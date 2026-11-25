import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import house
import house_backup as backups
import house_revisions as rev


class HouseRevisions(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        settings = patch.object(backups, "backup_directory", return_value=self.folder / "automatic")
        settings.start()
        self.addCleanup(settings.stop)
        with patch.object(house, "HOUSES", self.folder / "library"):
            self.home = house.initialise("Example home", None, ["Kitchen"])
        self.reason = dict(change="Pier returned", why="Survey received", author="Surveyor",
                           affects="Kitchen and dining", next_step="Reprice the units")
        self.archive = self.folder / "recovery.zip"

    def first_revision(self):
        source = self.home / "source/survey.txt"
        source.write_bytes(b"measured")
        out = rev.begin(self.home, "pier-r1", inputs=["source/survey.txt"])
        (out / "design").mkdir()
        (out / "design/plan.pdf").write_bytes(b"first plan")
        rev.save(self.home, "PIER-R1", **self.reason)
        return source

    def test_copied_inputs_parent_and_draft_are_independent(self):
        source = self.first_revision()
        (self.home / "decisions.md").write_text("Owner now requires dining for eight")
        source.write_bytes(b"new measurement")
        second = rev.begin(self.home, "pier-r2", "pier-r1", ["source/survey.txt"])
        (second / "design/plan.pdf").write_bytes(b"second plan")
        rev.save(self.home, "pier-r2", **self.reason)
        (second / "design/plan.pdf").write_bytes(b"later draft edit")
        first, later = rev.records(self.home)
        self.assertEqual(later["parent"], first["revision"])
        self.assertNotEqual(later["inputs"], first["inputs"])
        self.assertNotEqual(later["inputs"]["decisions.md"], first["inputs"]["decisions.md"])
        for key, contents in [("pier-r1", b"first plan"), ("pier-r2", b"second plan")]:
            rev.verify_revision(self.home, key)
            self.assertEqual((rev.record_dir(self.home, key) / "outputs/design/plan.pdf").read_bytes(), contents)
            with self.assertRaisesRegex(ValueError, "already"):
                rev.begin(self.home, key)
            with self.assertRaisesRegex(ValueError, "already"):
                rev.save(self.home, key, **self.reason)
        altered = rev.record_dir(self.home, "pier-r1") / "outputs/design/plan.pdf"
        altered.write_bytes(b"modified externally")
        with self.assertRaisesRegex(ValueError, "Checksum"):
            rev.verify_revision(self.home, "pier-r1")
        with self.assertRaisesRegex(ValueError, "Checksum"):
            backups.backup(self.home, self.archive, house.ROOT)
        self.assertFalse(self.archive.exists())

    def test_failed_and_competing_saves_publish_only_one_complete_revision(self):
        out = rev.begin(self.home, "r1")
        with self.assertRaisesRegex(ValueError, "at least one"):
            rev.save(self.home, "r1", **self.reason)
        self.assertFalse(rev.record_dir(self.home, "r1").exists())
        (out / "plan.txt").write_text("plan")
        def try_save(_):
            try:
                rev.save(self.home, "r1", **self.reason)
                return True
            except (ValueError, OSError):
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(pool.map(try_save, range(2)), [True, False])
        self.assertEqual(len(rev.verify_revision(self.home, "r1")["outputs"]), 1)
        self.assertEqual(len(list(backups.backup_directory().rglob("*.zip"))), 1)

    def test_each_automatic_archive_restores_its_own_house_state(self):
        self.first_revision()
        (self.home / "views/new.png").write_bytes(b"later view")
        out = rev.begin(self.home, "pier-r2", "pier-r1")
        (out / "design/plan.pdf").write_bytes(b"revised")
        rev.save(self.home, "pier-r2", **self.reason)
        for number in (1, 2):
            revision = f"PIER-R{number}"
            record = rev.verify_revision(self.home, revision)
            target = self.folder / f"recovered-{number}"
            archive = backups.backup_directory() / record["backup"]
            backups.restore("example-home", archive, target)
            self.assertEqual(rev.verify_revision(target, revision), record)
            self.assertEqual(len(rev.records(target)), number)
            self.assertEqual((target / "views/new.png").exists(), number == 2)

    def test_failed_backup_keeps_draft_and_retries_without_publishing(self):
        out = rev.begin(self.home, "r1")
        (out / "model").write_bytes(b"model")
        with patch.object(backups, "read_payload", side_effect=ValueError("Verification failed")):
            with self.assertRaisesRegex(ValueError, "Verification failed"):
                rev.save(self.home, "r1", **self.reason)
        self.assertEqual(rev.records(self.home), [])
        self.assertFalse(list(backups.backup_directory().rglob("*.zip")))
        self.assertEqual((out / "model").read_bytes(), b"model")
        with patch.object(backups, "backup_directory", return_value=self.home / "unsafe"):
            with self.assertRaisesRegex(ValueError, "outside"):
                rev.save(self.home, "r1", **self.reason)
        rev.save(self.home, "r1", **self.reason)
        self.assertEqual(len(list(backups.backup_directory().rglob("*.zip"))), 1)

    def test_conflicting_restore_recovers_separately_and_never_overwrites(self):
        self.first_revision()
        (self.home / "views/image.png").write_bytes(b"original view")
        backups.backup(self.home, self.archive, house.ROOT)
        with self.assertRaises(FileExistsError):
            backups.backup(self.home, self.archive, house.ROOT)
        with self.assertRaisesRegex(ValueError, "different house"):
            backups.restore("another-house", self.archive, self.folder / "wrong")
        source = self.home / "source/survey.txt"
        source.unlink()
        (self.home / "views/image.png").write_bytes(b"current edit")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            backups.restore("example-home", self.archive, self.home)
        self.assertFalse(source.exists())
        self.assertEqual((self.home / "views/image.png").read_bytes(), b"current edit")
        recovered = self.folder / "other" / "example-home"
        backups.restore("example-home", self.archive, recovered)
        self.assertEqual((recovered / "views/image.png").read_bytes(), b"original view")
        brief = recovered / "brief.md"
        lf = brief.read_bytes().replace(b"\r\n", b"\n")
        brief.write_bytes(lf)
        self.assertEqual(backups.restore("example-home", self.archive, recovered), 0)
        self.assertEqual(brief.read_bytes(), lf)

    def test_interrupted_restore_can_be_retried(self):
        self.first_revision()
        backups.backup(self.home, self.archive, house.ROOT)
        target = self.folder / "partial"
        target.mkdir()
        (target / "project.json").write_bytes((self.home / "project.json").read_bytes())
        publish = backups.publish_file
        saved = []
        def interrupt(source, destination):
            if saved:
                raise OSError("Test interruption")
            publish(source, destination)
            saved.append(destination)
        with patch.object(backups, "publish_file", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "interruption"):
                backups.restore("example-home", self.archive, target)
        contents = saved[0].read_bytes()
        self.assertGreater(backups.restore("example-home", self.archive, target), 0)
        self.assertEqual(saved[0].read_bytes(), contents)
        rev.verify_revision(target, "PIER-R1")

    def test_damaged_and_misdirected_archives_leave_no_restored_house(self):
        self.first_revision()
        backups.backup(self.home, self.archive, house.ROOT)
        for case in ("damaged", "outside"):
            broken, target = self.folder / (case + ".zip"), self.folder / ("restore-" + case)
            with ZipFile(self.archive) as original, ZipFile(broken, "w") as edited:
                for name in original.namelist():
                    data = original.read(name)
                    if case == "damaged" and name == "house/source/survey.txt":
                        data = b"damaged"
                    if case == "outside" and name == "backup.json":
                        header = json.loads(data)
                        header["directories"].append("../escape")
                        data = json.dumps(header)
                    edited.writestr(name, data)
            with self.assertRaises(ValueError):
                backups.restore("example-home", broken, target)
            self.assertFalse(target.exists())
        for unsafe in ("../another", "models/file.txt:other", "X:/drive"):
            with self.assertRaises(ValueError):
                rev.begin(self.home, "r2", inputs=[unsafe])
        self.assertFalse((self.home / rev.WORK / "R2").exists())

    def test_pier_round_trip_using_public_commands_and_git_privacy_rules(self):
        script = house.ROOT / "examples/whole-house-changes/revision_replay.py"
        result = subprocess.run([sys.executable, str(script), "--output", str(self.folder / "drill")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("based on PIER-R1", result.stdout)
        self.assertIn("PIER-R3 verified", result.stdout)
