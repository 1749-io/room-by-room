import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import house
from room_by_room.house_routes import analyse
from shapely.geometry import LineString, Polygon


def rect(x, y, right, top):
    return [[x, y], [right, y], [right, top], [x, top]]


def dining():
    # Two rooms linked by a 1,400 mm throat. An inherited table stays put.
    return {
        "revision": "R2", "units": "mm", "basis": "Measured synthetic test plan",
        "source": "brief.md", "authority": "decisions.md",
        "floor": [[0, 0], [2500, 0], [2500, 1000], [4500, 1000], [4500, 0],
                  [7000, 0], [7000, 4000], [4500, 4000], [4500, 2400],
                  [2500, 2400], [2500, 4000], [0, 4000]],
        "obstacles": {"Sideboard": rect(3000, 1000, 4000, 1850), "Family table": rect(500, 3000, 2200, 3800)},
        "journeys": {"carry-shopping": {"start": [1100, 1700], "end": [5900, 1700],
                                       "width_mm": 850, "uncertainty_mm": 0}},
    }


class HouseholdRoutes(unittest.TestCase):
    def test_walkthrough_cli_requires_the_recording_even_if_the_planner_fits(self):
        with tempfile.TemporaryDirectory() as library:
            home = Path(library) / "cottage"
            home.mkdir()
            (home / "project.json").write_text("{}")
            (home / "brief.md").touch()
            (home / "decisions.md").touch()
            study = dining()
            study["floor"] = rect(0, 0, 8000, 4000)
            study["obstacles"] = {"Door": rect(3200, 1400, 3300, 2000)}
            leg = study["journeys"]["carry-shopping"]
            cmd = [sys.executable, house.__file__, "--houses-dir", library, "check-routes",
                   "cottage", "film.routes.json", "--input-revision", "R2", "--require-walked-path", "--json"]
            for samples, expected in [(None, 1), ([leg["start"], leg["end"]], 1),
                                      ([leg["start"], [2400, 2700], [4500, 2700], leg["end"]], 0)]:
                with self.subTest(samples=samples):
                    if samples is not None:
                        leg["walked_path_mm"] = samples
                    (home / "film.routes.json").write_text(json.dumps(study))
                    run = subprocess.run(cmd, capture_output=True, text=True)
                    self.assertIn("journeys", json.loads(run.stdout))
                    self.assertEqual(run.returncode, expected, run.stderr)

    def test_recorded_walk_checks_the_film_even_when_a_detour_exists(self):
        study = dining()
        study["floor"] = rect(0, 0, 6000, 4000)
        study["obstacles"] = {"Door leaf": rect(2950, 1500, 3050, 2500)}
        leg = dict(start=[1000, 2000], end=[5000, 2000], width_mm=600, uncertainty_mm=0)
        study["journeys"] = {"walk": leg}
        planned = analyse(study, "baseline")["walk"]
        self.assertEqual(planned["status"], "fits")
        for y, expected in [(2000, "restricted"), (1400, "restricted"), (1100, "fits")]:
            leg["walked_path_mm"] = [leg["start"], [1500, y], [4500, y], leg["end"]]
            actual = analyse(study, "baseline")["walk"]
            self.assertEqual(actual["status"], expected)
            self.assertEqual(actual["beside"], "Door leaf")
        leg["walked_path_mm"] = [[900, 2000], leg["end"]]
        with self.assertRaisesRegex(ValueError, "match the journey endpoints"):
            analyse(study, "baseline")
        leg["end"] = leg["start"]
        leg["walked_path_mm"] = [leg["start"], [1200, 1600], leg["end"]]
        self.assertEqual(analyse(study, "baseline")["walk"]["status"], "fits")
        leg["walked_path_mm"] = [leg["start"], leg["end"]]
        with self.assertRaisesRegex(ValueError, "contain movement"):
            analyse(study, "baseline")

    def test_buyer_can_review_a_thin_route_without_proposing_work(self):
        study = dining()
        original = json.dumps(study)
        result = analyse(study, "baseline")["carry-shopping"]
        self.assertEqual(result["status"], "restricted")
        self.assertAlmostEqual(result["tested_mm"], 550, delta=5)
        self.assertEqual(json.dumps(study), original)
        study["options"] = {"remove table": {"Family table": None}}
        with self.assertRaisesRegex(ValueError, "outside the recorded scope"):
            analyse(study, "remove table")

    def test_rearrange_only_the_sideboard_and_its_operating_space(self):
        study = dining()
        study["allowed_changes"] = {"Sideboard": "reposition"}
        study["options"] = {"move": {"Sideboard": {"translate_mm": [-2500, -800]}}}
        study["journeys"]["carry-shopping"]["in_use"] = {
            "Sideboard in use": {"attached_to": "Sideboard", "outline": rect(3000, 1000, 4000, 2250)}}
        self.assertLess(analyse(study, "baseline")["carry-shopping"]["tested_mm"], 151)
        # This first move clears the doorway but blocks the shopping pick-up point.
        self.assertEqual(analyse(study, "move")["carry-shopping"]["status"], "restricted")
        study["options"]["move"]["Sideboard"] = {"translate_mm": [2900, -1000]}
        self.assertEqual(analyse(study, "move")["carry-shopping"]["status"], "fits")
        for edit, message in [(None, "rigid"), (rect(0, 0, 10, 10), "rigid"),
                              ({"translate_mm": [-4500, 0]}, "leave the modelled"),
                              ({"translate_mm": [-2400, 2100]}, "overlap Family table")]:
            with self.subTest(edit=edit), self.assertRaisesRegex(ValueError, message):
                study["options"]["move"]["Sideboard"] = edit
                analyse(study, "move")

    def test_laundry_can_use_an_alternative_around_occupied_breakfast(self):
        study = dining()
        study["floor"] = rect(0, 0, 9000, 6000)
        study["obstacles"] = {"Partition": rect(3500, 2000, 5500, 3800)}
        task = {"start": [1200, 1800], "end": [7800, 1800], "width_mm": 900, "uncertainty_mm": 0}
        busy = rect(3000, 0, 6000, 2000)
        study["journeys"] = {"breakfast empty": task, "breakfast occupied": dict(task, in_use={"Breakfast in use": busy})}
        quiet, occupied = analyse(study, "baseline").values()
        self.assertEqual(occupied["status"], "fits")
        self.assertGreater(occupied["length_mm"], quiet["length_mm"])
        self.assertGreaterEqual(LineString(occupied["path_mm"]).distance(Polygon(busy)), 450)
        self.assertGreater(max(y for _, y in occupied["path_mm"]), 3800)

    def test_walker_needs_the_turn_and_threshold_checked(self):
        study = dining()
        task = study["journeys"]["carry-shopping"]
        task.update(width_mm=500, uncertainty_mm=0, measurements=["Measure the bathroom turn and threshold"])
        finding = analyse(study, "baseline")["carry-shopping"]
        self.assertEqual(finding["status"], "measure")
        self.assertEqual(finding["measurements"], task["measurements"])
        task.update(width_mm=540, uncertainty_mm=30, measurements=[])
        self.assertEqual(analyse(study, "baseline")["carry-shopping"]["status"], "measure")

    def test_moving_a_lounge_chair_can_keep_dining_clear_and_block_a_valve(self):
        study = dining()
        study.update(floor=rect(0, 0, 6500, 4500), obstacles={"Armchair": rect(1500, 3000, 2300, 3800)},
                     allowed_changes={"Armchair": "reposition"},
                     options={"near radiator": {"Armchair": {"translate_mm": [3200, 0], "rotate_deg": 90}}})
        route = {"start": [800, 1000], "end": [5600, 1000], "width_mm": 700, "uncertainty_mm": 0}
        study["journeys"] = {"to dining": route, "reach valve": dict(route, end=[5100, 3500])}
        self.assertTrue(all(r["status"] == "fits" for r in analyse(study, "baseline").values()))
        option = analyse(study, "near radiator")
        self.assertEqual(option["to dining"]["status"], "fits")
        self.assertEqual(option["reach valve"]["status"], "restricted")
        self.assertEqual(option["reach valve"]["path_mm"], [])

    def test_assessment_and_proposed_layout_use_different_release_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            room = home / "rooms/dining"
            room.mkdir(parents=True)
            (home / "brief.md").touch()
            (room / "plan.svg").touch()
            recipe = "rooms/dining/occupied.routes.json"
            spec = dining()
            (home / recipe).write_text(json.dumps(spec))
            rows = ["revision,kind,source,expectation,observed,evidence,result,check_id",
                    "R2,intent,brief,keep table,retained,brief.md,pass,",
                    "R2,use,brief,serve,observed,brief.md,pass,",
                    "R2,whole-room,brief,dine and pass,checked,rooms/dining/plan.svg,pass,",
                    f"R2,journey,brief,carry shopping,checked,{recipe},pass,route:carry-shopping"]
            (room / "route-journeys.csv").write_text("journey_id,routine\ncarry-shopping,Carry groceries\n")
            (room / "layout-checks.csv").write_text("\n".join(rows[:-1] + ["R2,journey,brief,carry,looked,brief.md,pass,"]))
            self.assertIn("one current route study", house.check_layout_evidence(home, room, "R2"))
            (room / "layout-checks.csv").write_text("\n".join(rows))
            def gate():
                return house.check_layout_evidence(home, room, "R2")
            self.assertIn("restricted", gate())
            spec.update(review_option="move", allowed_changes={"Sideboard": "reposition"},
                        options={"move": {"Sideboard": {"translate_mm": [-2500, -800]}}})
            (home / recipe).write_text(json.dumps(spec))
            self.assertIn("authorising", gate())
            (home / "decisions.md").touch()
            self.assertIn("homeowner selection", gate())
            self.assertEqual(house.route_report(home, recipe, "R2", "move")["journeys"]["carry-shopping"]["status"], "fits")
            spec["selection"] = "decisions.md"
            (home / recipe).write_text(json.dumps(spec))
            self.assertIsNone(gate())
            spec["source_sha256"] = hashlib.sha256((home / "brief.md").read_bytes()).hexdigest()
            (home / recipe).write_text(json.dumps(spec))
            (home / "brief.md").write_text("Updated dimensions")
            self.assertIn("Source changed", gate())
            spec["revision"] = "R1"
            (home / recipe).write_text(json.dumps(spec))
            self.assertIn("revision", gate())

    def test_homeowner_can_keep_a_known_constraint_without_accepting_a_new_one(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "brief.md").touch()
            (home / "decisions.md").touch()
            spec = dining()
            task = spec["journeys"]["carry-shopping"]
            spec.update(allowed_changes={"Sideboard": "reposition"},
                        options={"shift": {"Sideboard": {"translate_mm": [0, 150]}}})
            kept = {"option": "baseline", "reason": "Keep the known narrow approach in the concept",
                    "decision": "decisions.md"}
            task["retained_constraint"] = kept
            def review(option):
                (home / "option.routes.json").write_text(json.dumps(spec))
                return house.route_report(home, "option.routes.json", "R2", option)["journeys"]["carry-shopping"]
            existing = review("baseline")
            self.assertEqual(existing["status"], "restricted")
            self.assertIn("retained_constraint", existing)
            kept["option"] = "shift"
            self.assertNotIn("retained_constraint", review("shift"))
            kept["option"] = "baseline"
            task["measurements"] = ["Measure the gap"]
            self.assertNotIn("retained_constraint", review("baseline"))

    def test_proposal_can_meet_minimum_but_worsen_a_protected_route(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "brief.md").touch()
            (home / "decisions.md").touch()
            spec = dining()
            spec["obstacles"]["Sideboard"] = rect(500, 200, 1500, 1050)
            spec.update(allowed_changes={"Sideboard": "reposition"},
                        options={"move": {"Sideboard": {"translate_mm": [2500, 800]}}})
            spec["journeys"]["carry-shopping"].update(width_mm=450, max_loss_mm=100)
            (home / "proposal.routes.json").write_text(json.dumps(spec))
            result = house.route_report(home, "proposal.routes.json", "R2", "move")["journeys"]["carry-shopping"]
            self.assertGreater(result["tested_mm"], 450)
            self.assertEqual(result["status"], "review")
            self.assertEqual(result["baseline_status"], "fits")
