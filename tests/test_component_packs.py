import csv
import importlib.util
import io
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz
from openpyxl import load_workbook

from room_by_room import house_delivery as packs
from room_by_room import house_revisions as rev
from tools import render_pack

ROOT = Path(__file__).resolve().parents[1]
fixture = importlib.util.spec_from_file_location("pack_example", ROOT / "examples/component-pack/replay.py")
example = importlib.util.module_from_spec(fixture)
fixture.loader.exec_module(example)


class ComponentDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        cls.path = Path(cls.work.name)
        cls.home = example.prepare(cls.path)
        cls.editions = {k: example.build_issue(cls.path, cls.home, k, parts)
                        for k, parts in example.EDITIONS.items()}

    def test_four_portable_editions_and_their_forwarded_files(self):
        for issue, folder in self.editions.items():
            with self.subTest(issue=issue), zipfile.ZipFile(next(folder.glob("*.zip"))) as archive:
                names = archive.namelist()
                self.assertEqual("Issue.pdf" in names, issue == "COMPLETE")
                self.assertEqual(any(n.startswith("Rooms/") for n in names), issue in ("ROOM", "COMPLETE"))
                self.assertEqual(any(n.startswith("Drawings/") for n in names), issue in ("DRAWING", "COMPLETE"))
                self.assertEqual(any(n.startswith("Schedules/") for n in names), issue in ("SHOP", "COMPLETE"))
                for name in names:
                    data = archive.read(name)
                    self.assertEqual(data, (folder / "delivery" / name).read_bytes())
                    if name.endswith(".pdf"):
                        with fitz.open(stream=data, filetype="pdf") as doc:
                            for page in doc:
                                self.assertIn("Alder Cottage", page.get_text())
                                self.assertIn(issue, page.get_text())
                                self.assertGreater(len(page.get_pixmap().samples), 1000)
                            if name.startswith("Drawings/"):
                                self.assertIn("Drawing key", doc[0].get_text())
                    if name.endswith("-shopping.csv"):
                        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
                        self.assertEqual([r["Item ID"] for r in rows], ["L01", "L02"])
                        self.assertEqual(rows[1]["Quantity x unit GBP"], "169.00")
                        self.assertIn("held", rows[1]["Fit / purchase hold"])
                    if name.endswith(".xlsx"):
                        book = load_workbook(io.BytesIO(data))
                        try:
                            table = next(iter(book.active.tables.values()))
                            self.assertEqual(table.autoFilter.ref, table.ref)
                            self.assertIn(169, list(book.active.values)[2])
                        finally:
                            book.close()
                    if name.endswith("review.html"):
                        self.assertIn(b'data:image/png;base64,', data)
                        self.assertNotIn(b'../', data)
                self.assertFalse(any(".revision-work" in n or "Kitchen" in n for n in names))

    def test_two_clean_builds_match_archive_bytes(self):
        draft = self.editions["COMPLETE"].parents[1]
        base = rev.stored_json(draft / "draft.json")
        spec, assets = packs.resolve(self.home, base, draft)
        with tempfile.TemporaryDirectory() as other:
            stage = Path(other) / "pack"
            render_pack.build(stage, spec, assets, packs.fingerprint(spec))
            self.assertEqual(next(stage.glob("*.zip")).read_bytes(),
                             next(self.editions["COMPLETE"].glob("*.zip")).read_bytes())

    def test_room_reader_pages_reproduce_the_signed_visual(self):
        folder = self.editions["COMPLETE"]
        draft = folder.parents[1]
        spec, assets = packs.resolve(self.home, rev.stored_json(draft / "draft.json"), draft)
        with tempfile.TemporaryDirectory() as other:
            copied = Path(other) / "delivery"
            shutil.copytree(folder / "delivery", copied)
            render_pack.check_visual_files(copied, spec, assets)
            sheet, = (copied / "Drawings").glob("*.pdf")
            with fitz.open() as doc:
                doc.new_page().insert_text((40, 40), "Different layout")
                sheet.write_bytes(render_pack.pdf_bytes(doc))
            with self.assertRaisesRegex(ValueError, "differs from the signed visual placement"):
                render_pack.check_visual_files(copied, spec, assets)

    def test_whole_house_reuses_each_standalone_and_checks_room_coverage(self):
        for edition in ["ROOM", "DRAWING", "SHOP"]:
            example.save_example(self.path, edition, "Checked the standalone files against fixture expectations.")
        full = example.build_house(self.path, self.home)
        with zipfile.ZipFile(next(full.glob("*.zip"))) as combined:
            for edition in ("ROOM", "DRAWING", "SHOP"):
                with zipfile.ZipFile(next(self.editions[edition].glob("*.zip"))) as single:
                    files = [n for n in single.namelist() if "/" in n]
                    for name in files:
                        self.assertEqual(combined.read(name), single.read(name))
        example.save_example(self.path, "HOUSE", "Reopened the full house issue and matched standalone files.")
        self.assertIn("HOUSE", (self.home / "CHECKLIST.md").read_text(encoding="utf-8"))
        from tools.house_pack import resolve_house
        request = rev.stored_json(self.home / "house-request.json")
        example.save_example(self.path, "COMPLETE", "Reopened the room, drawing and schedule.")
        drawing_only = dict(request, components=["drawing"], rooms={"library": {"drawing": "COMPLETE"}})
        schedule = self.home / "shopping.csv"
        original = schedule.read_bytes()
        try:
            schedule.write_bytes(original.replace(b"84.50", b"90.50"))
            resolve_house(self.home, drawing_only, "DRAWINGS")
            with self.assertRaisesRegex(ValueError, "shopping selections changed"):
                resolve_house(self.home, request, "NEXT")
        finally:
            schedule.write_bytes(original)
        # A standalone schedule can identify the registered room by its slug.
        alias_request = rev.stored_json(self.home / "request-SHOP.json")
        alias_request["room"] = "library"
        rev.write_json(self.home / "alias-shop.json", alias_request)
        example.run(self.path, "begin-revision", "Alder Cottage", "ALIAS-SHOP", "--pack-request", "alias-shop.json")
        example.run(self.path, "build-pack", "Alder Cottage", "ALIAS-SHOP")
        example.save_example(self.path, "ALIAS-SHOP", "Checked the shopping files issued under the library slug.")
        mixed = dict(request, rooms={"library": dict(request["rooms"]["library"], shopping="ALIAS-SHOP")})
        rev.write_json(self.home / "mixed.json", mixed)
        example.run(self.path, "begin-revision", "Alder Cottage", "MIXED", "--pack-request", "mixed.json")
        entry = Path(example.run(self.path, "build-pack", "Alder Cottage", "MIXED"))
        self.assertIn("ALIAS-SHOP-shopping.xlsx", entry.read_text(encoding="utf-8"))
        with fitz.open(entry.parent / "Issue.pdf") as contents:
            self.assertEqual(len(contents), 1)
            for issue in ("ROOM", "DRAWING", "ALIAS-SHOP"):
                self.assertIn(issue, contents[0].get_text())
        example.run(self.path, "add-room", "Alder Cottage", "Utility")
        with self.assertRaisesRegex(ValueError, "Missing.*utility"):
            resolve_house(self.home, request, "NEXT")

    def test_source_change_blocks_only_the_affected_issue(self):
        schedule = self.home / "shopping.csv"
        orig = schedule.read_bytes()
        try:
            schedule.write_bytes(orig.replace(b"84.50", b"90.50"))
            with self.assertRaisesRegex(ValueError, "shopping selections changed"):
                packs.command(self.home, "COMPLETE", "check-pack")
            packs.command(self.home, "DRAWING", "check-pack")
        finally:
            schedule.write_bytes(orig)

    def test_shared_item_retains_the_house_quantity_and_an_explicit_allocation_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            schedule = Path(temp) / "shopping.csv"
            schedule.write_text("guide_ref,room,product_name,quantity,status,unit_price_gbp\n"
                                "S1,Library / Kitchen,Wall light in brass,3,Selected,90\n", encoding="utf-8")
            for room in ("Library", "Kitchen"):
                row, = packs.shopping_rows(schedule, room)
                self.assertEqual((row["Item ID"], row["Source quantity"], row["Quantity"]), ("S1", "3", ""))
                self.assertEqual(row["Quantity x unit GBP"], "")
                self.assertIn("allocation", row["Fit / purchase hold"])

    def test_hold_and_stale_revision(self):
        reg = self.home / "rooms/library/review.csv"
        original = reg.read_bytes()
        try:
            reg.write_bytes(original.replace(b"existing-cad,pass", b"existing-cad,hold"))
            with self.assertRaisesRegex(ValueError, "hold"):
                packs.command(self.home, "DRAWING", "check-pack")
            packs.command(self.home, "SHOP", "check-pack")
        finally:
            reg.write_bytes(original)

    def test_saving_requires_a_review_bound_to_built_files(self):
        folder = example.build_issue(self.path, self.home, "SAVE", ["shopping"])
        args = ("save-revision", "Alder Cottage", "SAVE", "--change", "Fictional schedule", "--why",
                "Check portability", "--by", "Test", "--affects", "Library", "--next", "Review holds")
        with self.assertRaisesRegex(ValueError, "reader review"):
            example.run(self.path, *args)
        packs.command(self.home, "SAVE", "check-pack", "Fixture reader", "Opened both schedule formats and checked holds.")
        register = folder / "delivery/Link-register.csv"
        register.rename(register.with_suffix(".absent"))
        with self.assertRaisesRegex(ValueError, "commissioned file list"):
            example.run(self.path, *args)
        register.with_suffix(".absent").rename(register)
        example.run(self.path, *args)
        self.assertIn("Verified issued pack", packs.command(self.home, "SAVE", "check-pack"))

    def test_portable_zip_must_include_the_commissioned_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "copy"
            shutil.copytree(self.editions["SHOP"], folder)
            manifest = rev.stored_json(folder / "issue-manifest.json")
            portal = folder / "delivery" / "Start here.html"
            portal.write_text("<h1>Shopping</h1>", encoding="utf-8")
            register = portal.parent / "Link-register.csv"
            rows = packs.read_rows(register)
            entry = next(row for row in rows if row["path"] == portal.name)
            entry["sha256"] = packs.digest(portal)
            register.write_bytes(render_pack.csv_bytes([entry]))
            archive = folder / manifest["archive"]
            with zipfile.ZipFile(archive, "w") as out:
                for path in (portal, register):
                    out.write(path, path.name)
            manifest["archive_sha256"] = packs.digest(archive)
            with self.assertRaisesRegex(ValueError, "commissioned file list"):
                render_pack.verify(folder, manifest["request"], manifest)

    def test_requested_shopping_rows_cannot_disappear_from_workbook(self):
        # Keep the ZIP, its loose files and their index internally consistent.
        # The independent frozen item set must still catch the removed purchase.
        from tools.check_delivery import verify_issue
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "copy"
            shutil.copytree(self.editions["SHOP"], folder)
            delivery = folder / "delivery"
            workbook = next(delivery.rglob("*.xlsx"))
            book = load_workbook(io.BytesIO(workbook.read_bytes()))
            book.active.delete_rows(3)
            book.save(workbook)
            book.close()
            register = delivery / "Link-register.csv"
            rows = list(csv.DictReader(io.StringIO(register.read_text(encoding="utf-8-sig"))))
            for row in rows:
                row["sha256"] = packs.digest(delivery / row["path"])
            register.write_bytes(render_pack.csv_bytes(rows))
            archive = next(folder.glob("*.zip"))
            with zipfile.ZipFile(archive, "w") as out:
                for path in delivery.rglob("*"):
                    if path.is_file():
                        out.write(path, path.relative_to(delivery).as_posix())
            manifest = rev.stored_json(folder / "issue-manifest.json")
            manifest["archive_sha256"] = packs.digest(archive)
            verify_issue(delivery, archive_folder=folder)
            with self.assertRaisesRegex(ValueError, "workbook has different rows"):
                render_pack.verify(folder, manifest["request"], manifest)
