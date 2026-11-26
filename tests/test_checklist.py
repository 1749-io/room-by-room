"""Check the homeowner checklist through the normal house entry points."""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import house
from room_by_room import house_checklist as checklist
from room_by_room import house_revisions as revisions


class RenovationChecklist(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.library = Path(directory.name) / "houses"
        with patch.object(house, "HOUSES", self.library):
            self.home = house.initialise("Test cottage", None, [])
        self.page = self.home / "CHECKLIST.md"

    def cli(self, *args, check=True):
        return subprocess.run([sys.executable, str(house.ROOT / "house.py"), "--houses-dir",
                               str(self.library), *args], text=True, capture_output=True, check=check)

    def write_return(self, status, *, source="", check=""):
        with (self.home / "survey-returns.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, checklist.FIELDS)
            writer.writeheader()
            writer.writerow(dict(ref="S1",room="study",question="Measure the opened sash",
                                 owner="Surveyor",affects="Desk and window",status=status,
                                 return_evidence=source,recheck_evidence=check))

    def test_start_add_resume_and_repeated_refresh_preserve_homeowner_edits(self):
        self.assertIn("Add the rooms", self.page.read_text(encoding="utf-8"))
        self.cli("add-room", "Test cottage", "Study")
        first = self.page.read_text(encoding="utf-8")
        self.assertIn("| [Study](rooms/study/review.csv) | Pending", first)
        self.assertIn("| Assess |", first)
        tick = "- [x] Study. R1 accepted with the window outstanding."
        edited = first.replace("- [ ] Study. Record revision, decision, date and exclusions.", tick)
        self.page.write_text(edited + "\nCheck the sill on site.\n", encoding="utf-8")
        self.cli("add-room", "Test cottage", "Hall")
        self.write_return("requested")
        for action in ("next", "status", "checklist"):
            self.cli(action, "Test cottage")
        current = self.page.read_text(encoding="utf-8")
        for expected in (tick, "Check the sill on site.", "S1 · study · Requested", "acceptance hall"):
            self.assertIn(expected, current)
        self.assertEqual(current.count("acceptance study"), 1)
        timestamp = self.page.stat().st_mtime_ns
        checklist.refresh(self.home)
        self.assertEqual(self.page.stat().st_mtime_ns, timestamp)

    def test_survey_needs_both_retained_return_and_design_recheck(self):
        house.add_room(self.home, "Study")
        self.write_return("required")
        checklist.refresh(self.home)
        previous = self.page.read_bytes()
        for status, source, recheck in (("returned", "", ""), ("rechecked", "brief.md", ""),
                                        ("rechecked", "../bad.txt", "brief.md"), ("complete", "", "")):
            with self.subTest(status=status, source=source):
                self.write_return(status, source=source, check=recheck)
                result = self.cli("checklist", "Test cottage", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(previous, self.page.read_bytes())
        self.write_return("returned", source="brief.md")
        checklist.refresh(self.home)
        self.assertIn("- [ ] **S1 · study · Recheck due**", self.page.read_text(encoding="utf-8"))
        self.write_return("rechecked", source="brief.md", check="rooms/study/README.md")
        checklist.refresh(self.home)
        done = self.page.read_text(encoding="utf-8")
        self.assertIn("- [x] **S1 · study · Rechecked**", done)
        self.assertIn("[Recheck](rooms/study/README.md)", done)
        self.assertIn("| Pending | Waiting |", done)
        self.assertIn("- [ ] Study.", done)

    def test_evidence_drives_pass_and_revision_captures_working_state(self):
        house.add_room(self.home, "Study")
        register = self.home / "rooms/study/review.csv"
        with register.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        rows[1][1:6] = ["pass", "R1", "source/observed.txt", "Designer", "Brief reviewed"]
        with register.open("w", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerows(rows)
        checklist.refresh(self.home)
        self.assertIn("evidence or review details missing", self.page.read_text(encoding="utf-8"))
        (self.home / "source/observed.txt").write_text("Homeowner instructions", encoding="utf-8")
        self.cli("checklist", "Test cottage")
        self.assertIn("[Pass](source/observed.txt) | Pending", self.page.read_text(encoding="utf-8"))
        out = revisions.begin(self.home, "R1")
        for name in ("CHECKLIST.md", "survey-returns.csv"):
            self.assertEqual((out.parent / "inputs" / name).read_bytes(), (self.home / name).read_bytes())
        self.write_return("required")
        (out / "study.txt").write_text("CAD inputs", encoding="utf-8")
        with patch.object(house.house_backup, "backup_directory", return_value=self.library.parent / "backups"):
            revisions.save(self.home, "R1", change="Document brief", why="First issue",
                           author="Designer", affects="Study", next_step="Check sash")
        self.assertIn("S1 · study · Required", self.page.read_text(encoding="utf-8"))

    def test_a_missing_or_damaged_review_stays_on_the_checklist(self):
        for name in ("Study", "Lounge"):
            house.add_room(self.home, name)
        (self.home / "rooms/study/review.csv").unlink()
        (self.home / "rooms/lounge/review.csv").write_text("wrong header\n", encoding="utf-8")
        self.cli("checklist", "Test cottage")
        report = self.page.read_text(encoding="utf-8")
        self.assertIn("0 of 2 rooms", report)
        self.assertIn("[Study](rooms/study/README.md) | **Check register**", report)
        self.assertIn("Restore or create the room review register", report)
        self.assertIn("[Lounge](rooms/lounge/review.csv) | **Check register**", report)

    def test_existing_house_is_upgraded_without_losing_its_checklist(self):
        self.page.write_text("# Keep my list\n\n- [x] Original agreement\n", encoding="utf-8")
        (self.home / "survey-returns.csv").unlink()
        self.cli("checklist", "Test cottage")
        text = self.page.read_text(encoding="utf-8")
        self.assertIn("- [x] Original agreement", text)
        self.assertIn("## Room checks", text)
        self.assertIn("## Household and project decisions", text)
        self.assertTrue((self.home / "survey-returns.csv").exists())
