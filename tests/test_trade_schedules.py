import csv
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz
import openpyxl

from room_by_room import house_delivery as delivery
from room_by_room import house_revisions as revisions
from tools.house_pack import build_house, resolve_house
from tools.schedule_data import cost_rows, programme_rows, resolve_schedule
from tools.schedule_pack import build_schedule, totals, verify_schedule

ROOT = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location("trade_example", ROOT / "examples/trade-schedules/replay.py")
example = importlib.util.module_from_spec(module)
module.loader.exec_module(example)
ISSUES = {"FINISH": "decorator-finishes", "COST": "cost-schedule", "PROG": "programme"}


class TradeSchedules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sandbox = tempfile.TemporaryDirectory(prefix="Alder trade issues ")
        cls.addClassCleanup(sandbox.cleanup)
        cls.home = example.replay(Path(sandbox.name) / "fixture")

    def folder(self, rev):
        return self.home / "revisions" / rev

    def archive(self, rev):
        return zipfile.ZipFile(next((self.folder(rev) / "outputs/pack").glob("*.zip")))

    def current(self, rev):
        folder = self.folder(rev)
        return delivery.resolve(self.home, revisions.verify_revision(self.home, rev), folder)[0]

    def test_each_standalone_and_house_contains_the_same_usable_files(self):
        with self.archive("HOUSE-TRADE") as full:
            for rev, kind in ISSUES.items():
                with self.subTest(rev=rev), self.archive(rev) as single:
                    prefix = "Schedules/" + kind + "/"
                    members = [n for n in single.namelist() if n.startswith(prefix)]
                    self.assertEqual({Path(n).suffix for n in members}, {".xlsx", ".csv", ".html"})
                    self.assertEqual(len(members), 3)
                    self.assertEqual(set(single.namelist())-set(members), {"Start here.html", "Link-register.csv"})
                    for n in members:
                        self.assertEqual(single.read(n), full.read(n))
                    self.assertIn(prefix+"Read%20me.html", full.read("Start here.html").decode())
                    file = next(n for n in members if n.endswith(".csv"))
                    rows = list(csv.DictReader(io.StringIO(single.read(file).decode("utf-8-sig"))))
                    self.assertEqual({r["Issue"] for r in rows}, {rev})
                    self.assertEqual({r["House"] for r in rows}, {"Alder Cottage"})
                    self.assertNotIn("Private acquisition figures", str(rows))
            with fitz.open(stream=full.read("Issue.pdf"), filetype="pdf") as pdf:
                self.assertEqual(len(pdf), 3)  # one room plus two contents pages for six publications
                for title in ("Cost schedule", "Decorator finishes", "Programme", "Architect pack", "Buyer brief", "Homeowner presentation"):
                    self.assertIn(title, "".join(p.get_text() for p in pdf))

    def test_workbooks_have_the_approved_rows_prices_dependencies_and_formula_caches(self):
        for rev in ISSUES:
            with self.archive(rev) as single:
                data = single.read(next(n for n in single.namelist() if n.endswith(".xlsx")))
            book = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            try:
                sheet = book.worksheets[-1]
                labels = [c.value for c in sheet[6]]
                rows = [dict(zip(labels, row)) for row in sheet.iter_rows(min_row=7, values_only=True)]
                self.assertTrue(sheet.tables)
                if rev == "FINISH":
                    self.assertEqual([(r["Surface"], r["Code"], r["Finish"]) for r in rows],
                                     [("Library walls", "AL-04", "Washable matt"),
                                      ("Library skirting and architrave", "AL-01", "Water-based eggshell")])
                    self.assertEqual({r["Status"] for r in rows}, {"approved"})
                if rev == "COST":
                    summary = list(book["Cost summary"].values)
                    self.assertEqual(summary[6], ("Base", 210, 300, 0, 210, 300))
                    self.assertEqual(summary[7], ("Add shelves", 379, 469, 1, None, None))
                    self.assertEqual([r["Low GBP"] for r in rows if r["Shopping IDs"] == "L02"], [169])
                if rev == "PROG":
                    fit = next(r for r in rows if r["Task ID"] == "FIT")
                    self.assertEqual([fit["After 1"], fit["After 2"]], ["PAINT", "LEAD"])
                    self.assertEqual(fit["Forecast finish"].date().isoformat(), "2027-01-18")
                    self.assertIn("Conditional", fit["Status"])
            finally:
                book.close()

    def test_clean_builds_match_all_four_archives(self):
        reference = ROOT / "examples/trade-schedules/reference/Alder-Cottage-trade-handover.zip"
        actual, = (self.folder("HOUSE-TRADE") / "outputs/pack").glob("*.zip")
        self.assertEqual(hashlib.sha256(actual.read_bytes()).digest(), hashlib.sha256(reference.read_bytes()).digest(),
                         "A clean build must reproduce the downloadable Alder Cottage issue on every tested platform")
        with self.archive("HOUSE-TRADE") as full, fitz.open(stream=full.read("Issue.pdf"), filetype="pdf") as contents:
            schedule_pages = [page.get_text() for page in contents if "Schedules/" in page.get_text()]
            self.assertTrue(schedule_pages)
            self.assertTrue(all("Included in this handover" in page for page in schedule_pages))
        for rev in [*ISSUES, "HOUSE-TRADE"]:
            folder = self.folder(rev)
            spec, assets = delivery.resolve(self.home, revisions.verify_revision(self.home, rev), folder)
            with self.subTest(rev=rev), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp)
                if rev == "HOUSE-TRADE":
                    build_house(dest, spec, assets, delivery.fingerprint(spec))
                else:
                    build_schedule(dest, spec, delivery.fingerprint(spec))
                    verify_schedule(dest, spec, revisions.stored_json(dest / "issue-manifest.json"))
                self.assertEqual(next(dest.glob("*.zip")).read_bytes(), next((folder / "outputs/pack").glob("*.zip")).read_bytes())

    def test_each_schedule_can_be_the_first_issue_in_its_own_house(self):
        requests = json.loads((example.HERE / "requests.json").read_text(encoding="utf-8"))
        sources = {"FINISH": ["rooms/library/decorator-finishes.csv", "source/library-sample-decision.md"],
                   "COST": ["budget.csv", "shopping.csv"], "PROG": ["programme.csv"]}
        for rev in ISSUES:
            with self.subTest(rev=rev), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                example.audience.room.run(work, "start", "Alder Cottage", "--room", "Library")
                home = work / "houses/alder-cottage"
                for name in sources[rev]:
                    (home / name).write_bytes((self.home / name).read_bytes())
                req = dict(requests[rev], version=1, profile="schedule", house="alder-cottage")
                example.audience.issue(work, home, rev, req)
                example.audience.room.save_example(work, rev, "Opened the independently issued schedule.")
                self.assertEqual({p.name for p in (home / "revisions").iterdir() if p.is_dir()}, {rev})
                issued = next((home / "revisions" / rev / "outputs/pack").glob("*.zip"))
                self.assertEqual(issued.read_bytes(), next((self.folder(rev) / "outputs/pack").glob("*.zip")).read_bytes())

    def test_missing_or_superseded_finish_and_changed_approval_block_only_affected_issues(self):
        full = revisions.stored_json(self.home / "request-HOUSE-TRADE.json")
        path = self.home / "source/library-sample-decision.md"
        before = path.read_bytes()
        try:
            path.write_bytes(before + b"\nSuperseding sample evidence\n")
            with self.assertRaisesRegex(ValueError, "approval evidence changed"):
                resolve_house(self.home, full, "CHECK")
            self.current("COST")
        finally:
            path.write_bytes(before)
        req = revisions.stored_json(self.home / "request-FINISH.json")
        for surface in ("Bookcase back panel", "Ceiling"):
            req["surfaces"]["Library"]["surfaces"] = [surface]
            with self.assertRaisesRegex(ValueError, "sample required|no decorator finish"):
                resolve_schedule(self.home, req, "CHECK", self.home)
        path = self.home / "rooms/library/decorator-finishes.csv"
        before = path.read_bytes()
        try:
            replacement = before.splitlines()[1].replace(b"FIN-01", b"FIN-02")
            path.write_bytes(before + b"\n" + replacement + b"\n")
            with self.assertRaisesRegex(ValueError, "latest recorded finish"):
                self.current("FINISH")
        finally:
            path.write_bytes(before)

    def test_stale_prices_and_programme_cycles_hold_release(self):
        for filename, old, new, rev, error in [
            ("shopping.csv", b"84.50", b"85.50", "COST", "shopping lines total"),
            ("programme.csv", b"PAINT LEAD", b"FIT LEAD", "PROG", "cycle"),
            ("programme.csv", b"PAINT LEAD", b"NO-TASK LEAD", "PROG", "missing or repeated")]:
            path = self.home / filename
            before = path.read_bytes()
            try:
                self.assertIn(old, before)
                path.write_bytes(before.replace(old, new))
                with self.assertRaisesRegex(ValueError, error):
                    self.current(rev)
            finally:
                path.write_bytes(before)

    def test_recipient_cannot_forward_private_costs(self):
        full = revisions.stored_json(self.home / "request-HOUSE-TRADE.json")
        full.update(audience="Architect", components=["drawing"], rooms={"library": {"drawing": "DRAWING"}},
                    editions={"cost-schedule": "COST"})
        with self.assertRaisesRegex(ValueError, "audience permission missing"):
            resolve_house(self.home, full, "CHECK")

    def test_partial_cost_bounds_and_missing_durations_remain_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "budget.csv").write_text("scope,low_gbp,high_gbp,basis,date,includes,exclusions,decision\n"
                                               "Site visit,40,,Fictional minimum,,,,Await quote\n", encoding="utf-8")
            rows, _ = cost_rows(folder, {"budget_lines": {"Site visit": "Base"}})
            self.assertEqual((rows[0]["Low GBP"], rows[0]["High GBP"], rows[0]["Pricing"]), ("40", "", "Check range"))
            self.assertEqual(totals(rows)[0][3:], [1, "", ""])
            path = folder / "programme.csv"
            path.write_bytes((example.HERE / "programme.csv").read_bytes().replace(b"Installer,,1,", b"Installer,,,"))
            rows, _ = programme_rows(folder, {"start_date": "2027-01-11", "tasks": "all"})
            tasks = {row["Task ID"]: row for row in rows}
            self.assertEqual(tasks["SUR"]["Forecast finish"], "")
            self.assertEqual(tasks["CHOOSE"]["Timing"], "Awaiting duration")
            self.assertEqual(tasks["FIT"]["Forecast start"], "")
            self.assertEqual(tasks["PAINT"]["Forecast finish"], "2027-01-14")
