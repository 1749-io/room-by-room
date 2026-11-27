import ast
import glob
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/blender-interiors/scripts"
PACKAGE = SCRIPTS / "room_assets"
GUIDE = ROOT / "skills/blender-interiors/references/room-assets.md"
sys.path.insert(0, str(SCRIPTS))

import room_assets  # noqa: E402


def blender():
    """Locate Blender from BLENDER, PATH or a standard installation."""
    found = os.environ.get("BLENDER") or shutil.which("blender")
    if found:
        return found
    for pattern in (r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
                    "/Applications/Blender.app/Contents/MacOS/Blender"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def functions(module):
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


class Catalogue(unittest.TestCase):
    def test_every_entry_has_a_builder_taking_its_options(self):
        for kind, entry in room_assets.ASSETS.items():
            with self.subTest(asset=kind):
                builder = functions(entry["module"]).get(kind)
                self.assertIsNotNone(builder, f"{entry['module']}.py needs a function named {kind}")
                self.assertTrue(ast.get_docstring(builder))
                self.assertEqual([arg.arg for arg in builder.args.args],
                                 ["root", "size", "finishes", *entry["options"]])

    def test_every_builder_is_catalogued(self):
        modules = {entry["module"] for entry in room_assets.ASSETS.values()}
        built = {name for module in modules for name in functions(module)}
        self.assertEqual(built, set(room_assets.ASSETS))

    def test_sizes_and_finishes_are_usable(self):
        source = ast.parse((PACKAGE / "parts.py").read_text(encoding="utf-8"))
        palette, = [ast.literal_eval(node.value) for node in source.body
                    if isinstance(node, ast.Assign) and node.targets[0].id == "PALETTE"]
        for kind, entry in room_assets.ASSETS.items():
            with self.subTest(asset=kind):
                size = entry["size"]
                for low, default, high in zip(size["min"], size["default"], size["max"]):
                    self.assertLessEqual(low, default)
                    self.assertLessEqual(default, high)
                self.assertLessEqual(set(entry["finishes"].values()), set(palette))
                for field in ("summary", "size_means", "origin"):
                    self.assertTrue(entry[field])

    def test_guide_lists_exactly_the_catalogue(self):
        rows = re.findall(r"^\| `(\w+)` \|", GUIDE.read_text(encoding="utf-8"), flags=re.M)
        self.assertEqual(rows, list(room_assets.ASSETS))

    def test_builders_take_nothing_from_chance_files_or_the_network(self):
        banned = {"random", "secrets", "time", "datetime", "urllib", "requests", "os", "pathlib", "uuid"}
        for module in sorted({entry["module"] for entry in room_assets.ASSETS.values()} | {"parts"}):
            tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
            used = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            used |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
            self.assertFalse(used & banned, f"{module}.py imports {sorted(used & banned)}")


class Requests(unittest.TestCase):
    def test_defaults_are_filled_from_the_catalogue(self):
        size, finishes, options = room_assets.resolve("rattan_armchair")
        self.assertEqual(size, [740, 790, 820])
        self.assertEqual(finishes, {"frame": "rattan", "weave": "cane", "cushions": "oatmeal"})
        self.assertEqual(options, {"seat_height_mm": 475, "arm_height_mm": 617})
        size, finishes, options = room_assets.resolve("dining_chair", (460, 520, 880), {"pad": "rust"}, {"seat_height_mm": 470})
        self.assertEqual((size, finishes["pad"], finishes["frame"], options), ([460, 520, 880], "rust", "oak", {"seat_height_mm": 470}))

    def test_requests_outside_the_catalogue_are_refused_with_the_limits(self):
        cases = {
            "No asset named": ("chaise_longue", None, None, None),
            "outside 600 to 900 mm": ("rattan_armchair", (1200, 790, 820), None, None),
            "three sizes": ("hedge", (3000, 700), None, None),
            "no option castors": ("sideboard", None, None, {"castors": True}),
            "no finish for canopy": ("hedge", None, {"canopy": "leaf"}, None),
        }
        for message, request in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                room_assets.resolve(*request)


    def test_a_one_off_request_is_checked_before_blender_is_needed(self):
        cases = [("builder function itself", ("hall_bench", "bench", (1200, 380, 450))),
                 ("three positive sizes", (print, "bench", (1200, 380))),
                 ("three positive sizes", (print, "bench", (1200, 0, 450)))]
        for message, request in cases:
            with self.subTest(request=request[2]), self.assertRaisesRegex(ValueError, message):
                room_assets.build_custom(*request)


class Guide(unittest.TestCase):
    def test_starting_examples_cover_every_builder_and_name_real_helpers(self):
        guide = GUIDE.read_text(encoding="utf-8")
        table = guide.split("## Choose an example to start from")[1].split("## Build a one-off piece")[0]
        linked = re.findall(r"\[([^\]]+)\]\(\.\./scripts/room_assets/(\w+)\.py\)", table)
        named = {}
        for label, module in linked:
            for name in re.findall(r"[a-z]+_[a-z]+|tree|hedge|pendant|sideboard", label):
                named[name] = module
        self.assertEqual(named, {kind: entry["module"] for kind, entry in room_assets.ASSETS.items()})
        helpers = set(functions("parts"))
        used = set(re.findall(r"`(\w+)`", table))
        self.assertTrue(used)
        self.assertLessEqual(used, helpers)

    def test_one_off_example_is_valid_python_using_the_public_names(self):
        guide = GUIDE.read_text(encoding="utf-8")
        section = guide.split("## Build a one-off piece for one house")[1]
        code = re.search(r"```python\n(.*?)```", section, flags=re.S)[1]
        tree = ast.parse(code)
        imported = {alias.name for node in tree.body if isinstance(node, ast.ImportFrom) for alias in node.names}
        public = set(functions("__init__")) | {"parts"}
        self.assertLessEqual(imported, public)
        builder, = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual([arg.arg for arg in builder.args.args][:3], ["root", "size", "finishes"])


@unittest.skipUnless(blender(), "Blender is not installed. Set BLENDER to its executable to run the geometry check")
class BuiltGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "report.json"
            run = subprocess.run([blender(), "--background", "--factory-startup", "--python-exit-code", "1",
                                  "--python", str(SCRIPTS / "check_room_assets.py"), "--", str(target)],
                                 capture_output=True, text=True, timeout=600)
            if not target.exists():
                raise AssertionError(f"Blender did not write a report:\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}")
            cls.report = json.loads(target.read_text(encoding="utf-8"))

    def test_every_asset_reads_back_at_each_requested_size(self):
        self.assertEqual(set(self.report["assets"]), set(room_assets.ASSETS))
        for kind, result in self.report["assets"].items():
            for case in result["cases"]:
                with self.subTest(asset=kind, size=case["case"]):
                    self.assertEqual(case["requested_size_mm"], room_assets.ASSETS[kind]["size"][case["case"]])
                    self.assertLessEqual(case["worst_difference_mm"], room_assets.TOLERANCE_MM)
                    self.assertLessEqual(case["worst_difference_when_turned_mm"], room_assets.TOLERANCE_MM)

    def test_floor_standing_assets_fill_exactly_the_stated_box(self):
        for kind in ("rattan_armchair", "block_armchair", "dining_chair", "dining_table", "sideboard", "side_table", "glazed_leaf", "hedge"):
            for case in self.report["assets"][kind]["cases"]:
                with self.subTest(asset=kind, size=case["case"]):
                    width, depth, height = case["requested_size_mm"]
                    self.assertEqual(case["requested_extent_mm"], [-width / 2, -depth / 2, 0, width / 2, depth / 2, height])
                    for measured, wanted in zip(case["measured_size_mm"], case["requested_size_mm"]):
                        self.assertAlmostEqual(measured, wanted, delta=room_assets.TOLERANCE_MM)

    def test_a_tree_stands_at_its_surveyed_height_on_its_trunk(self):
        for case in self.report["assets"]["tree"]["cases"]:
            low, high = case["measured_extent_mm"][:3], case["measured_extent_mm"][3:]
            self.assertAlmostEqual(low[2], 0, delta=1)
            self.assertAlmostEqual(high[2], case["requested_size_mm"][2], delta=1)
            self.assertLess(low[0], 0)
            self.assertGreater(high[0], 0)

    def test_a_one_off_builder_gets_the_same_record_and_refusal(self):
        custom = self.report["custom"]
        self.assertEqual(custom["asset"], "custom:bench")
        self.assertEqual(custom["requested_size_mm"], [1200, 380, 450])
        self.assertLessEqual(custom["worst_difference_mm"], room_assets.TOLERANCE_MM)
        self.assertEqual(json.loads(custom["options"]), {"slats": 4})
        self.assertTrue(custom["tags_kept"])
        self.assertTrue(custom["oversize_refused"])

    def test_the_same_request_repeats_and_removal_leaves_nothing(self):
        for kind, result in self.report["assets"].items():
            self.assertTrue(result["repeats"], f"{kind} differed between two builds")
        self.assertEqual(self.report["objects_left_behind"], [])


if __name__ == "__main__":
    unittest.main()
