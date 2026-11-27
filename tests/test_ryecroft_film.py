import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/ryecroft-film"
FILM = EXAMPLE / "film"
SKILL = ROOT / "skills/room-by-room-film"
TEXT = {".md", ".json", ".html", ".mjs", ".py", ".sh", ".txt"}
REBUILT = ("node_modules", "frames", "stills", "renders", "music")


def published():
    """Files of the example, without outputs that a rebuild leaves beside them."""
    return [path for path in EXAMPLE.rglob("*")
            if path.is_file() and not set(path.relative_to(EXAMPLE).parts) & set(REBUILT)
            and path.name not in {"channel.js", "timing.json", "sfx-events.json"} and path.suffix != ".wav"]


class RyecroftFilm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (FILM / "channel.json").read_text(encoding="utf-8")
        cls.film = json.loads(cls.raw)

    def test_every_card_picture_is_present_and_every_picture_is_used(self):
        page = (FILM / "film.html").read_text(encoding="utf-8")
        named = set(re.findall(r"assets/([\w-]+\.jpg)", self.raw + page))
        named |= set(re.findall(r"[\"'>(]([\w-]+\.jpg)", self.raw))
        stills = {path.name for path in (FILM / "assets").glob("*.jpg")}
        self.assertEqual(stills, named)

    def test_frame_sequences_hold_exactly_the_frames_the_cards_play(self):
        declared = re.findall(r"data-seq='assets/(\w+)/(\w+)' data-first='(\d+)' data-count='(\d+)'", self.raw)
        self.assertEqual({folder for folder, *_ in declared}, {"walk", "build"})
        for folder, prefix, first, count in declared:
            wanted = {f"{prefix}{number:04d}.jpg" for number in range(int(first), int(first) + int(count))}
            self.assertEqual({path.name for path in (FILM / "assets" / folder).iterdir()}, wanted, folder)

    def test_no_listing_machine_or_working_note_reaches_the_public_copy(self):
        banned = re.compile(r"rightmove|zoopla|onthemarket|guide price|offers over|[A-Z]:[\\/]Users|/home/\w|\bdirector\b", re.I)
        for path in published():
            if path.suffix in TEXT and path.name != "package-lock.json":
                with self.subTest(file=path.relative_to(EXAMPLE).as_posix()):
                    self.assertIsNone(banned.search(path.read_text(encoding="utf-8")))

    def test_only_expected_file_types_are_published(self):
        kinds = {path.suffix for path in published()}
        self.assertLessEqual(kinds, TEXT | {".jpg"})
        self.assertFalse([path.name for path in published() if path.name.startswith("patch_") or path.name == "build_channel.py"])

    def test_every_non_text_film_file_is_in_the_asset_inventory(self):
        inventory = json.loads((ROOT / "examples/asset-inventory.json").read_text(encoding="utf-8"))
        plain = {".py", ".md", ".txt", ".json"}
        expected = {path.relative_to(ROOT).as_posix() for path in published() if path.suffix not in plain}
        listed = {name for name in inventory if name.startswith("examples/ryecroft-film/")}
        self.assertEqual(listed, expected)
        for name in listed:
            self.assertTrue(inventory[name]["origin"] and inventory[name]["rights"], name)

    def test_figures_on_the_cards_are_in_the_figure_record(self):
        record = (EXAMPLE / "RUN-FIGURES.md").read_text(encoding="utf-8")
        for figure in ("756 mm", "895 mm", "2.30 mm", "2.51 mm", "1,540 mm", "740 × 790 × 820 mm", "£329", "20 items placed"):
            with self.subTest(figure=figure):
                self.assertIn(figure, self.raw)
                self.assertIn(figure, record)
        for invented in ("hazelandthrush.example", "Ryecroft is an example house, not a real one"):
            self.assertIn(invented, self.raw)

    def test_the_film_names_the_repository_and_says_the_house_is_fictional(self):
        self.assertEqual(self.film["brand"]["url"], "github.com/1749-io/room-by-room")
        self.assertIn("example house, not a real one", self.film["music"]["credit"])
        self.assertEqual((len(self.film["chapters"]), sum(len(chapter["cards"]) for chapter in self.film["chapters"])), (17, 29))

    def test_skill_palette_matches_the_film(self):
        brand = (SKILL / "references/brand.md").read_text(encoding="utf-8")
        for role in ("ground", "deep", "ink", "accent", "accent2", "panel", "trial", "exp"):
            self.assertIn(self.film["brand"]["palette"][role], brand, role)
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: room-by-room-film\n"))


if __name__ == "__main__":
    unittest.main()
