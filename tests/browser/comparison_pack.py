"""Exercise the comparison builder's public CLI and offline walkthrough in Chromium."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

import fitz
from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parents[2] / "skills" / "property-comparison-pack"
module = importlib.util.spec_from_file_location("visual_example", SKILL.parents[1]/"examples/visual-release/replay.py")
fixture = importlib.util.module_from_spec(module)
module.loader.exec_module(fixture)


def page_signatures(path):
    with fitz.open(path) as pdf:
        return [(page.get_text(), hashlib.sha256(page.get_pixmap().samples).digest()) for page in pdf]


class ComparisonPack(unittest.TestCase):
    channel = None

    def test_rebuild_and_walk(self):
        with tempfile.TemporaryDirectory(prefix="Comparison pack ") as folder:
            root = Path(folder)
            house, source, assets = fixture.prepare(root / "fictional")
            manifest = json.loads(source.read_text(encoding="utf-8"))
            new_room = {"id": "library", "title": "Library", "text": "The proposed second room."}
            manifest["proposed"]["rooms"].append(new_room)
            manifest["proposed"]["expected_rooms"].append("library")
            manifest["proposed"]["studies"].append({"id": "route", "title": "Access route", "text": "Walk from the living room to the library."})
            source.write_text(json.dumps(manifest), encoding="utf-8")
            first, replay = root / "First build", root / "Replay"
            replay.mkdir()
            for out in (first, replay):
                command = [sys.executable, str(SKILL / "scripts/build.py"), str(source), str(assets), str(out)]
                if self.channel:
                    command.extend(["--channel", self.channel])
                subprocess.run(command, check=True)
            from tools.comparison_visuals import REPORT, verify_saved
            receipt = first / REPORT
            original = receipt.read_bytes()
            altered = json.loads(original)
            altered["placements"].pop()
            receipt.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "actual page placements"):
                verify_saved(house, first)
            receipt.write_bytes(original)
            combined = first / "Comparison.pdf"
            combined.rename(first / "held.pdf")
            with self.assertRaisesRegex(ValueError, "missing reader files"):
                verify_saved(house, first)
            combined.write_bytes((first / "proposed.pdf").read_bytes())
            altered = json.loads(original)
            altered["files"]["Comparison.pdf"] = hashlib.sha256(combined.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "printed page images differ"):
                verify_saved(house, first)
            receipt.write_bytes(original)
            (first / "held.pdf").replace(combined)
            room = house / "rooms" / "living-room"
            rejected = hashlib.sha256((assets / "proposed-living.jpg").read_bytes()).hexdigest()
            (room / "photo-defects.csv").write_text("photo_sha256,finding\n" + rejected + ",Frame over doorway\n")
            rejected_build = subprocess.run(
                [sys.executable, str(SKILL / "scripts/build.py"), str(source), str(assets),
                 str(root / "rejected"), "--house", str(house)], capture_output=True, text=True)
            self.assertNotEqual(rejected_build.returncode, 0)
            self.assertIn("Frame over doorway", rejected_build.stderr)
            self.assertFalse((root / "rejected" / "Comparison.pdf").exists())
            joined = []
            with sync_playwright() as api:
                browser = api.chromium.launch(channel=self.channel)
                page = browser.new_page()
                for kind in ("existing", "proposed"):
                    doc = manifest[kind]
                    stops = [doc["cover"], {"id": "contents", "title": "Room directory"},
                             *doc["layouts"], *doc["rooms"], *doc["studies"], *doc["particulars"]]
                    html = kind + ".html"
                    self.assertEqual((first / html).read_bytes(), (replay / html).read_bytes())
                    signatures = page_signatures(first / (kind + ".pdf"))
                    self.assertEqual(signatures, page_signatures(replay / (kind + ".pdf")))
                    self.assertEqual(len(signatures), len(stops))
                    for stop, (text, _) in zip(stops, signatures):
                        self.assertIn(stop["title"], text)
                    joined.extend(signatures)

                    page.goto((first / "Start here.html").as_uri())
                    page.get_by_role("link", name=f"{kind} · browser edition", exact=True).click()
                    self.assertEqual(page.url, (first / html).as_uri())
                    for i, stop in enumerate(stops):
                        section = page.locator("#" + stop["id"])
                        controls = section.locator("footer")
                        for label, target in (("Previous", stops[max(0, i - 1)]),
                                              ("Next", stops[min(i + 1, len(stops) - 1)]),
                                              ("Directory", stops[1])):
                            controls.get_by_role("link", name=label, exact=True).click()
                            self.assertEqual(urlsplit(page.url).fragment, target["id"])
                            self.assertEqual(page.locator(":target h1").inner_text(), target["title"])
                        if i >= 2:
                            page.locator("#contents").get_by_role("link", name=stop["title"], exact=True).click()
                            self.assertEqual(urlsplit(page.url).fragment, stop["id"])
                browser.close()
            for out in (first, replay):
                self.assertEqual(page_signatures(out / "Comparison.pdf"), joined)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel")
    ComparisonPack.channel = parser.parse_args().channel
    unittest.main(argv=[sys.argv[0]], verbosity=2)
