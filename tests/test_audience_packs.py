import csv
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz
from pptx import Presentation

from room_by_room import house_delivery as delivery
from room_by_room import house_revisions as revisions
from tools.audience_packs import build_edition
from tools.house_pack import resolve_house

ROOT = Path(__file__).resolve().parents[1]
fixture = importlib.util.spec_from_file_location("audience_fixture", ROOT / "examples/audience-packs/replay.py")
example = importlib.util.module_from_spec(fixture)
fixture.loader.exec_module(example)


class AudiencePacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory(prefix="House editions ")
        cls.addClassCleanup(temp.cleanup)
        cls.home = example.replay(Path(temp.name) / "private")

    def folder(self, issue):
        return self.home / "revisions" / issue / "outputs/pack"

    def archive(self, issue):
        return zipfile.ZipFile(next(self.folder(issue).glob("*.zip")))

    def resolve(self, issue):
        folder = self.folder(issue).parents[1]
        return delivery.resolve(self.home, revisions.stored_json(folder / "record.json"), folder)

    def test_each_edition_extracts_and_matches_house_bytes(self):
        with self.archive("HOUSE-ALL") as house:
            html = house.read("Start here.html").decode()
            for issue, (kind, *_) in example.EDITIONS.items():
                with self.subTest(issue=issue), self.archive(issue) as single:
                    prefix = f"Briefs/{kind}/"
                    self.assertIn(prefix + "Read%20me.html", html)
                    standalone = {n for n in single.namelist() if n.startswith(prefix)}
                    self.assertEqual(standalone, {n for n in house.namelist() if n.startswith(prefix)})
                    self.assertTrue(standalone)
                    self.assertEqual(set(single.namelist()) - standalone, {"Start here.html", "Link-register.csv"})
                    for n in standalone:
                        self.assertEqual(single.read(n), house.read(n), n)
                    for n in standalone:
                        if n.endswith(".pdf"):
                            with fitz.open(stream=single.read(n), filetype="pdf") as doc:
                                for page in doc:
                                    self.assertIn("Alder Cottage", page.get_text())
                                    self.assertNotIn("Kitchen-only", page.get_text())
                                    self.assertGreater(len(set(page.get_pixmap().samples[::97])), 3)

    def test_editable_slides_and_print_share_the_decision_figures_and_price(self):
        with self.archive("OWNER") as archive:
            deck = Presentation(io.BytesIO(archive.read(next(n for n in archive.namelist() if n.endswith(".pptx")))))
            with fitz.open(stream=archive.read(next(n for n in archive.namelist() if n.endswith(".pdf")))) as pdf:
                self.assertEqual(len(deck.slides), len(pdf))
                text = "\n".join(shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)
                for expected in ("Keep the library in use", "£169.00", "wall", "Order", "Homeowner"):
                    self.assertIn(expected.casefold(), text.casefold())
                self.assertTrue(any(s.shape_type == 13 for s in deck.slides[0].shapes))
                self.assertIn("Drawing key", pdf[0].get_text())
                self.assertEqual(pdf[0].rect.width/pdf[0].rect.height, 16/9)
                self.assertEqual(deck.core_properties.last_modified_by, "Alder Cottage")
                with zipfile.ZipFile(io.BytesIO(archive.read(next(n for n in archive.namelist() if n.endswith(".pptx"))))) as pptx:
                    preview = pdf[0].get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
                    self.assertEqual(pptx.read("docProps/thumbnail.jpeg"), preview.tobytes("jpeg"))
                for page in pdf:
                    self.assertTrue(all(not pdf.extract_font(font[0])[-1] for font in page.get_fonts()))

    def test_architect_register_forwards_the_original_and_prints_the_same_sheet(self):
        with self.archive("ARCH") as arch, self.archive("DRAWING") as source:
            register = next(n for n in arch.namelist() if n.endswith("Drawing-register.csv"))
            rows = list(csv.DictReader(io.StringIO(arch.read(register).decode("utf-8-sig"))))
            row, = rows
            self.assertEqual((row["Sheet"], row["Design revision"], row["Review stage"]), ("L-01", "LIB-01", "existing-cad"))
            sheet = arch.read(str(Path(register).parent.as_posix()) + "/" + row["File"])
            self.assertEqual(sheet, source.read(next(n for n in source.namelist() if n.startswith("Drawings/"))))
            brief = arch.read(next(n for n in arch.namelist() if n.endswith(".pdf") and "/Drawings/" not in n))
            with fitz.open(stream=brief) as doc, fitz.open(stream=sheet) as original:
                self.assertEqual(doc[-1].get_pixmap().digest, original[0].get_pixmap().digest)
                self.assertIn("Installer", doc[0].get_text())
                self.assertNotIn("£169", "".join(p.get_text() for p in doc))

    def test_buyer_extract_has_a_viewing_decision_cost_basis_and_questions(self):
        with self.archive("BUYER") as archive:
            self.assertFalse(any(n.endswith((".csv", ".xlsx", ".pptx")) and n != "Link-register.csv"
                                 for n in archive.namelist()))
            with fitz.open(stream=archive.read(next(n for n in archive.namelist() if n.endswith(".pdf")))) as doc:
                self.assertEqual(len(doc), 3)
                text = " ".join(" ".join(p.get_text().split()) for p in doc)
                for expected in ("£169.00", "2026-11-01", "quotation", "Moving in", "During the viewing", "conveyancer"):
                    self.assertIn(expected, text)

    def test_each_clean_rebuild_is_byte_identical(self):
        for issue in example.EDITIONS:
            spec, assets = self.resolve(issue)
            with self.subTest(issue=issue), tempfile.TemporaryDirectory() as other:
                target = Path(other)
                build_edition(target, spec, assets, delivery.fingerprint(spec))
                archive = next(target.glob("*.zip"))
                self.assertEqual(archive.read_bytes(), (self.folder(issue) / archive.name).read_bytes())
                manifest = json.loads((target / "issue-manifest.json").read_text(encoding="utf-8"))
                for asset in manifest["asset_uses"].values():
                    self.assertTrue(all(use.get("pages", [1]) for use in asset["uses"]))

    def test_reader_gate_rejects_a_substituted_plan(self):
        from tools import audience_pages
        spec, assets = self.resolve("OWNER")
        key = next(page["visual"]["key"] for page in spec["pages"] if page["visual"])
        with tempfile.TemporaryDirectory() as temp:
            substitute = Path(temp) / "different.pdf"
            with fitz.open() as doc:
                doc.new_page().insert_text((30, 40), "A different room")
                doc.save(substitute)
            with self.assertRaisesRegex(ValueError, "illustration differs"):
                audience_pages.verify(self.folder("OWNER") / "delivery", spec, {**assets, key: substitute})

    def test_drawing_approved_for_room_pages_cannot_open_the_homeowner_presentation(self):
        from room_by_room.house_visuals import Catalogue
        spec, _ = self.resolve("OWNER")
        self.assertEqual([p["visual"]["purpose"] for p in spec["pages"] if p["visual"]],
                         ["homeowner-presentation.opening", "homeowner-presentation.room"])
        path = self.home / "visual-approvals.json"
        self.addCleanup(path.write_bytes, path.read_bytes())
        catalogue = revisions.stored_json(path)
        grants = catalogue["visuals"]["LIB-PLAN-01"]["placements"]
        grants.remove({"purpose": "homeowner-presentation.opening", "scope": "room/library"})
        path.write_text(json.dumps(catalogue), encoding="utf-8")
        live = Catalogue(self.home)
        placement = dict(visual_id="LIB-PLAN-01", phase="existing", scope="room/library", view="plan")
        live.approve(purpose="homeowner-presentation.room", **placement)
        with self.assertRaisesRegex(ValueError, "not approved for homeowner-presentation.opening"):
            live.approve(purpose="homeowner-presentation.opening", **placement)
        with self.assertRaisesRegex(ValueError, "placement approval changed"):
            self.resolve("OWNER")

    def test_current_sources_and_named_audience_gate_full_assembly(self):
        req = revisions.stored_json(self.home / "request-HOUSE-ALL.json")
        with self.assertRaisesRegex(ValueError, "audience permission"):
            resolve_house(self.home, dict(req, share_with=["Selling agent"]), "REVIEW")
        with self.assertRaisesRegex(ValueError, "select an issued"):
            resolve_house(self.home, dict(req, editions={"buyer-brief": "ARCH"}), "REVIEW")
        for name in ("buyer.json", "shopping.csv"):
            path = self.home / name
            data = path.read_bytes()
            try:
                path.write_bytes(data + b" " if name.endswith(".json") else data.replace(b"84.50", b"86.50"))
                with self.assertRaisesRegex(ValueError, "changed"):
                    resolve_house(self.home, req, "REVIEW")
                self.resolve("ARCH")
            finally:
                path.write_bytes(data)

    def test_edition_grant_is_separate_from_room_source_grants(self):
        req = revisions.stored_json(self.home / "request-HOUSE-ALL.json")
        limited = dict(req, audience="Buyer", components=["drawing"], rooms={"library": {"drawing": "DRAWING"}},
                       editions={"architect-pack": "ARCH"})
        with self.assertRaisesRegex(ValueError, "ARCH: audience permission missing for Buyer"):
            resolve_house(self.home, limited, "REVIEW")

    def test_changed_cited_document_blocks_issue_and_private_path_stays_out_of_reader_files(self):
        path = self.home / "rooms/library/README.md"
        before = path.read_bytes()
        try:
            path.write_bytes(before + b"\nNew evidence for the library.\n")
            with self.assertRaisesRegex(ValueError, "cited evidence changed"):
                self.resolve("OWNER")
        finally:
            path.write_bytes(before)
        with self.archive("OWNER") as bundle:
            self.assertFalse(any(n.endswith(".md") for n in bundle.namelist()))
            with fitz.open(stream=bundle.read(next(n for n in bundle.namelist() if n.endswith(".pdf")))) as doc:
                self.assertNotIn("rooms/library/README.md", "".join(page.get_text() for page in doc))

    def test_explicit_scope_omission_is_printed_and_missing_chapter_is_held(self):
        folder = self.folder("BUYER").parents[1]
        from tools.audience_packs import resolve_edition
        request = revisions.stored_json(self.home / "request-BUYER.json")
        request["rooms"] = {"library": {"drawing": ["DRAWING"]}}
        with self.assertRaisesRegex(ValueError, "each commissioned component"):
            resolve_edition(self.home, request, "REVIEW", folder / "inputs")
        request["omissions"] = {"library": {"shopping": "Purchasing scope is open. Buyer to obtain estimates."}}
        spec, _ = resolve_edition(self.home, request, "REVIEW", folder / "inputs")
        self.assertIn("Purchasing scope is open", str(spec["pages"]))
        self.assertNotIn("£169.00", str(spec))
        with tempfile.TemporaryDirectory() as temp:
            path = self.home / "incomplete-buyer.json"
            data = revisions.stored_json(self.home / "buyer.json")
            del data["chapters"]["viewing"]
            path.write_text(json.dumps(data), encoding="utf-8")
            try:
                (Path(temp) / path.name).write_bytes(path.read_bytes())
                with self.assertRaisesRegex(ValueError, "expected chapters.*viewing"):
                    resolve_edition(self.home, dict(request, editorial=path.name), "REVIEW", Path(temp))
            finally:
                path.unlink()
