import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "skills/renovation-pack/references/deliverables.md"


class PackGuidance(unittest.TestCase):
    def test_pack_guidance_is_reachable_at_start_and_release(self):
        for entry in ("README.md", "skills/renovation-pack/SKILL.md",
                      "skills/renovation-pack/references/handover-gates.md"):
            with self.subTest(entry=entry):
                page = ROOT / entry
                targets = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", page.read_text(encoding="utf-8"))
                self.assertTrue(any((page.parent / target).resolve() == GUIDE for target in targets))

    def test_pack_reader_can_follow_each_audience_link(self):
        guide = GUIDE.read_text(encoding="utf-8")
        headings = {line[3:].lower().replace(",", "").replace(" ", "-") for line in guide.splitlines()
                    if line.startswith("## ")}
        links = dict(re.findall(r"\[([^\]]+)\]\(#([^)]+)\)", guide))
        for audience in ("Homeowner", "Buyer", "Architect or engineer", "Decorator or purchaser"):
            with self.subTest(audience=audience):
                self.assertIn(links.get(audience), headings)
