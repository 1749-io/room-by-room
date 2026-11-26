import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from room_by_room import house_visuals as gate
from tools.comparison_visuals import preflight

ROOT = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location("visual_fixture", ROOT/"examples/visual-release/replay.py")
example = importlib.util.module_from_spec(module)
module.loader.exec_module(example)


class VisualRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.home, manifest, cls.assets = example.prepare(Path(tmp.name)/"fixture")
        cls.manifest = json.loads(manifest.read_text(encoding="utf-8"))

    def setUp(self):
        self.states, self.visuals = [json.loads((self.home/f).read_text(encoding="utf-8")) for f in gate.REGISTERS]
        for file in [*gate.REGISTERS, "source/layout-decision.md", "source/proposed-door-view.json"]:
            path = self.home/file
            self.addCleanup(path.write_bytes, path.read_bytes())

    def write(self):
        for name, data in zip(gate.REGISTERS, [self.states, self.visuals]):
            example.save_json(self.home/name, data)

    def preflight(self, manifest=None):
        return preflight(self.home, manifest or self.manifest, self.assets)

    def test_actual_pages_and_repeated_uses_have_independent_grants(self):
        receipt = self.preflight()
        self.assertEqual(len(receipt["placements"]), 5)
        section = next(x for x in receipt["placements"] if x["request"]["view"] == "section")
        self.assertEqual(section["uses"][0], {"file": "proposed.html", "anchor": "opening-section"})
        self.assertGreater(section["uses"][2]["page"], section["uses"][1]["page"])
        manifest = copy.deepcopy(self.manifest)
        image = copy.deepcopy(manifest["proposed"]["layouts"][0]["images"][0])
        manifest["proposed"]["cover"]["images"] = [image]
        image["view"] = "plan"
        with self.assertRaisesRegex(ValueError, "not approved for comparison.cover"):
            self.preflight(manifest)

    def test_historical_room_locator_cannot_be_presented_as_a_current_floor_plan(self):
        old = copy.deepcopy(self.visuals["visuals"]["existing-plan"])
        old.update(view="locator", placements=[{"purpose": "comparison.rooms", "scope": "room/living-room"}])
        self.visuals["visuals"]["historic-locator"] = old
        self.write()
        manifest = copy.deepcopy(self.manifest)
        manifest["proposed"]["layouts"][0]["images"][0].update(path="existing-plan.png", visual_id="historic-locator")
        with self.assertRaisesRegex(ValueError, "not approved for comparison.layouts"):
            self.preflight(manifest)

    def test_missing_register_missing_section_and_changed_staged_source_are_held(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["proposed"]["studies"] = []
        with self.assertRaisesRegex(ValueError, "missing reviewed section showing retained-opening"):
            self.preflight(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["proposed"]["layouts"][0]["images"][0]["path"] = "existing-plan.png"
        with self.assertRaisesRegex(ValueError, "staged pixels differ"):
            self.preflight(manifest)
        (self.home/gate.REGISTERS[1]).unlink()
        with self.assertRaisesRegex(ValueError, "Missing visual-approvals"):
            self.preflight()

    def test_reviewer_cannot_supply_homeowner_acceptance_or_replace_accepted_geometry(self):
        state = self.states["states"]["proposed-arrangement"]
        original = state.pop("homeowner_decision")
        self.write()
        with self.assertRaisesRegex(ValueError, "homeowner's explicit design acceptance"):
            self.preflight()
        state["homeowner_decision"] = original
        state["geometry"] = [self.visuals["visuals"]["proposed-plan"]["source"]]
        self.write()
        with self.assertRaisesRegex(ValueError, "editable native geometry"):
            self.preflight()
        state["status"] = "for-review"
        self.write()
        with self.assertRaisesRegex(ValueError, "design status"):
            self.preflight()

    def test_accepted_state_persists_independently_of_its_derivatives(self):
        state = self.states["states"]["proposed-arrangement"]
        original = copy.deepcopy(state)
        state["arrangement"] += " The reading position has moved."
        self.write()
        with self.assertRaisesRegex(ValueError, "differs from the accepted record"):
            self.preflight()
        self.states["states"]["proposed-arrangement"] = original
        self.visuals["visuals"].clear()
        self.write()
        (self.home/"visual-approvals.json").unlink()
        saved = gate.Catalogue(self.home, design_only=True).design("proposed-arrangement", "proposed", "floor/ground", accepted=True)
        self.assertEqual(saved, original)
        self.assertNotIn("engineering_approval", saved)

    def test_superseded_ids_and_changed_decision_evidence_are_held(self):
        old = self.visuals["visuals"]["proposed-plan"]
        self.visuals["visuals"]["replacement"] = dict(old, supersedes=["proposed-plan"])
        self.write()
        with self.assertRaisesRegex(ValueError, "superseded"):
            self.preflight()
        del self.visuals["visuals"]["replacement"]
        self.write()
        (self.home/"source/layout-decision.md").write_text("A different instruction.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Stale or changed design evidence"):
            self.preflight()

    def test_camera_cannot_hide_a_visible_feature_and_an_exception_needs_evidence(self):
        visual = self.visuals["visuals"]["proposed-living"]
        check = visual["features"]["retained-opening"]
        check.update(visibility="outside-frame", finding="The camera faces away from the south wall.")
        self.write()
        with self.assertRaisesRegex(ValueError, "differs from the reviewed camera"):
            self.preflight()
        frame_path = self.home/visual["framing"]["path"]
        frame = json.loads(frame_path.read_text())
        for exception in ("outside-frame", "obscured"):
            frame["features"]["retained-opening"] = exception
            example.save_json(frame_path, frame)
            visual["framing"]["sha256"] = gate.checksum(frame_path)
            check["visibility"] = exception
            self.write()
            self.preflight()
        check.pop("evidence")
        self.write()
        with self.assertRaisesRegex(ValueError, "requires path"):
            self.preflight()
