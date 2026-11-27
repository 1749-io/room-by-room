"""Keep the published workflow diagrams tied to the review register and its return paths."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from tools.check_workflow_changes import coverage_problems
from house import GATES


DOCS = Path(__file__).resolve().parents[1] / "docs"
SVG = {"s": "http://www.w3.org/2000/svg"}
LINK = "{http://www.w3.org/1999/xlink}href"


class WorkflowDiagrams(unittest.TestCase):
    def test_changed_workflow_requires_its_own_published_map(self):
        room = {"skills/living-in-the-room/SKILL.md", "room_by_room/house_walkthrough.py"}
        pack = {"house.py", "skills/pack-delivery/SKILL.md"}
        map_changes = {"docs/workflow.dot", "docs/workflow.svg"}
        pack_changes = {"docs/pack-delivery.dot", "docs/pack-delivery.svg"}
        self.assertTrue(coverage_problems(room))
        self.assertTrue(coverage_problems(room | {"docs/workflow.dot"}))
        self.assertTrue(coverage_problems(room | {"docs/workflow.svg"}))
        self.assertTrue(coverage_problems(room | pack_changes))
        self.assertTrue(coverage_problems(pack | map_changes))
        self.assertFalse(coverage_problems(room | map_changes))
        self.assertFalse(coverage_problems(pack | pack_changes))
        self.assertFalse(coverage_problems({"README.md", "tests/test_house.py"}))
        film = {"skills/room-by-room-film/SKILL.md", "skills/room-by-room-film/references/brand.md"}
        self.assertFalse(coverage_problems(film))
        self.assertTrue(coverage_problems(film | room))

    def test_both_maps_keep_the_room_decisions_and_correction_loops(self):
        maps = [ET.parse(DOCS / name) for name in ("workflow.svg", "workflow-quick.svg", "workflow-preview.svg")]
        expected = {
            "intake->checklist", "checklist->survey", "survey->shell", "survey->options",
            "intake->shell", "intake->decor", "shell->fixed", "fixed->shell",
            "fixed->study", "study->options", "fixed->options", "options->living",
            "living->decide", "decide->options", "living->finish", "living->style",
            "style->finish", "finish->walkthrough", "walkthrough->finish", "walkthrough->options",
            "walkthrough->camera", "camera->fidelity", "fidelity->finish", "fidelity->style",
            "fidelity->ai", "ai->ai", "ai->release", "fixed->climate", "climate->options", "release->assembled", "assembled->finish",
        }
        for diagram in maps:
            with self.subTest(title=diagram.findtext("s:title", namespaces=SVG)):
                self.assertIn("Diagram key", [n.text for n in diagram.findall(".//s:text", SVG)])
                edges = diagram.findall(".//s:g[@class='edge']/s:title", SVG)
                paths = {re.sub(r":[nsew]+", "", edge.text) for edge in edges}
                self.assertTrue(expected.issubset(paths))
                self.assertNotIn("finish->camera", paths)
                self.assertNotIn("finish->fidelity", paths)
                for gate in ("fixed", "living", "walkthrough", "fidelity"):
                    node = next(g for g in diagram.findall(".//s:g[@class='node']", SVG)
                                if g.findtext("s:title", namespaces=SVG) == gate)
                    self.assertIsNotNone(node.find("s:polygon", SVG))

    def test_each_component_opens_a_review_and_can_return_to_the_map(self):
        for name in ("workflow.svg", "workflow-quick.svg"):
            root = ET.parse(DOCS / name)
            panels = {node.get("id"): node for node in root.iter() if node.get("id")}
            nodes = root.findall(".//s:g[@class='node']", SVG)
            links = root.findall(".//s:a[s:g]", SVG)
            self.assertEqual({link.find("s:g", SVG) for link in links}, set(nodes))
            for link in links:
                panel = panels[link.attrib[LINK][1:]]
                self.assertTrue(any(a.get(LINK) == "#room-map" for a in panel.findall("s:a", SVG)))
            for link in root.findall(".//s:a", SVG):
                self.check_destination(link.attrib[LINK], panels)
            beam = "".join(panels["study-structural-openings"].itertext())
            for solver in ("PyNite", "CalculiX"):
                self.assertIn(solver, beam)

    def test_every_room_gate_has_a_return_path_and_the_links_resolve(self):
        root = ET.parse(DOCS / "workflow.svg")
        ids = {node.get("id") for node in root.iter() if node.get("id")}
        self.assertTrue(set(GATES).issubset(ids))
        for gate in GATES:
            with self.subTest(gate=gate):
                panel = root.find(f".//s:g[@id='{gate}']", SVG)
                labels = {node.text for node in panel.findall("s:text", SVG)}
                self.assertTrue({"Proceed", "Hold, correct and return", "Who decides"}.issubset(labels))
        for link in root.findall(".//s:a", SVG):
            self.check_destination(link.get(LINK), ids)
        self.assertTrue({"specialist-study", "opening-enquiry", "orchard-house"}.issubset(ids))

    def check_destination(self, href, ids):
        if href.startswith("#"):
            self.assertIn(href[1:], ids)
        else:
            self.assertEqual(href, "pack-delivery.svg")
            self.assertTrue((DOCS / href).is_file())

    def test_pack_map_routes_and_commands(self):
        root = ET.parse(DOCS / "pack-delivery.svg")
        edges = {node.text for node in root.findall(".//s:g[@class='edge']/s:title", SVG)}
        self.assertTrue({"design->freeze", "single->freeze", "audience->freeze", "schedule->freeze", "house->freeze", "scope->fix", "check->fix",
                         "fix->freeze", "read->review", "review->release", "release->received"} <= edges)
        words = " ".join(root.getroot().itertext())
        for key in ("Diagram key", "Homeowner presentation", "architect pack", "buyer brief", "Decorator finishes", "cost schedule", "programme",
                    "plan-pack", "build-pack", "check-pack", "save-revision"):
            self.assertIn(key, words)
        for link in root.findall(".//s:a", SVG):
            self.assertTrue((DOCS / link.attrib[LINK]).is_file())
