import csv
import importlib.util
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
GARDEN = ROOT / "examples" / "garden-sun"


class WorkedExamples(unittest.TestCase):
    def test_solar_ray_and_hedge_sensitivity(self):
        spec = importlib.util.spec_from_file_location("garden_sun", GARDEN / "replay.py")
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        sunlight = replay.sunlight
        self.assertEqual(sunlight(1, 0, 0.75, 2, 270, 45), "shade")
        self.assertEqual(sunlight(4, 0, 0.75, 2, 270, 45), "sun")
        self.assertEqual(sunlight(1, 0, 0.75, 2, 90, 45), "sun")
        self.assertEqual(sunlight(1, 7, 0.75, 2, 270, 45), "sun")
        self.assertEqual(sunlight(1, 0, 0.75, 2, 270, -1), "below horizon")
        with (GARDEN / "samples.csv").open(newline="") as stream:
            sample, = (row for row in csv.DictReader(stream) if "09-21" in row["local_time"])
        angles = float(sample["azimuth_deg"]), float(sample["apparent_elevation_deg"])
        self.assertEqual(sunlight(4, 0, 0.75, 2, *angles), "sun")
        self.assertEqual(sunlight(4, 0, 0.75, 3, *angles), "shade")

    def test_example_index_opens_each_worked_case(self):
        index = ROOT / "examples/README.md"
        for target in re.findall(r"\]\(([^)]+)\)", index.read_text(encoding="utf-8")):
            url = urlsplit(target)
            if url.scheme:
                continue
            page = (index.parent / unquote(url.path)).resolve() if url.path else index
            with self.subTest(target=target):
                self.assertTrue(page.is_file())
                if url.fragment:
                    headings = re.findall(r"^#+ (.+)$", page.read_text(encoding="utf-8"), re.M)
                    anchors = [re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings]
                    self.assertIn(url.fragment, anchors)

class WholeHouseChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "examples/whole-house-changes/replay.py"
        spec = importlib.util.spec_from_file_location("whole_house_changes", path)
        cls.replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.replay)

    def test_a_straight_pier_gap_can_pass_while_the_continuous_route_fails(self):
        states = self.replay.read_json("reference/rear-rooms.json")
        result = self.replay.pier_results(states)
        self.assertEqual(result["R0", "Four"]["status"], "fits")
        self.assertEqual(result["R0", "Eight"]["status"], "restricted")
        self.assertEqual(result["R1", "Four"]["pier_gap"], 650)
        self.assertEqual(result["R2", "Eight"]["pier_gap"], 950)
        self.assertLess(result["R2", "Eight"]["tested_mm"], 825)
        for setting, count in (("Four", 4), ("Eight", 8)):
            self.assertEqual(result["R3", setting]["seats"], count)
            self.assertEqual(result["R3", setting]["status"], "fits")
        self.assertEqual(result["R3", "Eight"]["east_gap"], 840)

    def test_quote_exclusions_and_occupation_reverse_the_house_budget_decision(self):
        with (self.replay.FOLDER / "quotes.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        budget = self.replay.read_json("house-budget.json")
        result = self.replay.quote_results(rows, budget)
        self.assertEqual(result["a"], (53400, 209400, 211000, -1000))
        self.assertEqual(result["b"], (52000, 208000, 209600, 400))
        rows.append({"builder_a_gbp": 0, "builder_b_gbp": 600})
        self.assertEqual(self.replay.quote_results(rows, budget)["b"][-1], -200)

    def test_each_night_depends_on_service_access_and_the_actual_first_handover(self):
        data = self.replay.read_json("programme.json")
        plans = data["plans"]
        def failed(plan):
            availability = self.replay.bathroom_nights(plan, data["nights"])
            return [night for night, rooms in enumerate(availability, 1) if not rooms]
        self.assertEqual(failed(plans["simultaneous demolition"]), [1, 2, 3, 4])
        self.assertEqual(failed(plans["staggered but uncoordinated"]), [2, 3])
        coordinated = plans["occupied programme"]
        self.assertEqual(failed(coordinated), [])
        self.assertEqual(failed(self.replay.delayed_handover(coordinated, 7, False)), [6])
        delayed = self.replay.delayed_handover(coordinated, 7, True)
        self.assertEqual(delayed["downstairs_shower"], [[8, 11]])
        self.assertEqual(failed(delayed), [])
