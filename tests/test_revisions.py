import csv
import json
import io
from contextlib import redirect_stdout
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import house
from room_by_room import house_backup as backups
from room_by_room import house_revisions as rev
from PIL import Image


class HouseRevisions(unittest.TestCase):
    def test_verified_directory_publication_retries_a_transient_lock_only(self):
        with tempfile.TemporaryDirectory() as folder:
            staged, final = Path(folder, "stage"), Path(folder, "issue")
            staged.mkdir()
            rename = Path.rename
            locked = PermissionError("Temporary lock")
            locked.winerror = 32
            def transient(source, destination):
                if install.call_count == 1:
                    raise locked
                return rename(source, destination)
            with patch.object(Path, "rename", autospec=True, side_effect=transient) as install:
                with patch.object(rev.time, "sleep") as wait:
                    rev.publish_directory(staged, final)
                    self.assertEqual(install.call_count, 2)
                    wait.assert_called_once()
            self.assertTrue(final.is_dir())
            with self.assertRaises(FileExistsError):
                rev.publish_directory(staged, final)

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

    def test_working_dimensions_are_available_at_intake_and_frozen_per_revision(self):
        register = self.home / "cad-assumptions.csv"
        header = register.read_text(encoding="utf8")
        self.assertIn("working_value", header)
        original = header + "A1,Door,Clear width,mm,850,800,900,assumed,Room plan,S01,Access route\n"
        register.write_text(original, encoding="utf8")
        first = rev.begin(self.home, "BEFORE")
        register.write_text(original.replace("850,800,900,assumed", "812,,,measured"), encoding="utf8")
        second = rev.begin(self.home, "AFTER")
        self.assertEqual((first.parent / "inputs/cad-assumptions.csv").read_text(encoding="utf8"), original)
        self.assertEqual((second.parent / "inputs/cad-assumptions.csv").read_bytes(), register.read_bytes())

    def first_revision(self):
        source = self.home / "source/survey.txt"
        source.write_bytes(b"measured")
        out = rev.begin(self.home, "pier-r1", inputs=["source/survey.txt"])
        (out / "design").mkdir()
        (out / "design/plan.pdf").write_bytes(b"first plan")
        rev.save(self.home, "PIER-R1", **self.reason)
        return source

    def test_furnished_checkpoint_continues_without_a_second_homeowner_instruction(self):
        room = self.home / "rooms/kitchen"
        out = rev.begin(self.home, "R1")
        (out / "camera.txt").write_text("Camera review")
        with (room / "review.csv").open(newline="") as f:
            rows = list(csv.reader(f))
        for row in rows[1:6]:
            row[1:4] = ["pass", "R1", "brief.md"]
        with (room / "review.csv").open("w", newline="") as f:
            csv.writer(f).writerows(rows)
        with self.assertRaisesRegex(ValueError, "make and compare the final photo"):
            rev.save(self.home, "R1", **self.reason, question="Which room next?", question_kind="scope")
        with self.assertRaisesRegex(ValueError, "final photo"):
            rev.ask(self.home, "R1", "Which room next?", kind="scope")
        rev.save(self.home, "R1", **self.reason)
        self.assertIn("final photo", rev.next_choice(self.home, rev.records(self.home)))
        rev.begin(self.home, "R2", parent="R1")
        with self.assertRaisesRegex(ValueError, "Continue the agreed"):
            rev.save(self.home, "R2", **self.reason, question="Where next?", question_kind="scope")
        with (room / "README.md").open("a") as f:
            f.write("\nFurnished deliverable: views only\nHomeowner explicitly requested the cameras only.\n")
        rev.save(self.home, "R2", **self.reason, question="Which room next?", question_kind="scope")
        self.assertIn("Which room next?", rev.next_choice(self.home, rev.records(self.home)))

    def test_first_furnished_export_cannot_offer_the_next_room_before_register_update(self):
        out = rev.begin(self.home, "FIRST")
        (out / "openings").mkdir()
        (out / "openings/kitchen.camera.json").write_text("{}")
        (out / "scene.blend").write_bytes(b"model")
        Image.new("RGB", (6, 8), "teal").save(out / "view.png")
        with self.assertRaisesRegex(ValueError, "review the furnished camera"):
            rev.save(self.home, "FIRST", **self.reason, question="Which room next?", question_kind="scope")
        rev.save(self.home, "FIRST", **self.reason)
        self.assertIn("review the furnished camera", rev.next_choice(self.home, rev.records(self.home)))

    def test_full_pack_must_include_the_compared_photo_and_not_just_the_camera(self):
        room = self.home / "rooms/kitchen"
        out = rev.begin(self.home, "R3")
        for name, colour in [("camera.png", "grey"), ("final.png", "green")]:
            Image.new("RGB", (15, 10), colour).save(out / name)
        prefix = "revisions/R3/outputs/"
        with (room / "finish-checks.csv").open("a", newline="") as f:
            csv.writer(f).writerow(["R3", "ai-colour", "seat", prefix+"camera.png", prefix+"final.png", "Compared", "pass"])
        stages = {key: {"evidence": prefix+name} for key, name in (("final-ai", "final.png"), ("handover", "pack.zip"))}
        with ZipFile(out / "pack.zip", "w") as z:
            z.write(out / "camera.png", "final.png")
            z.writestr("index.html", "<img src='final.png'>")
        with self.assertRaisesRegex(ValueError, "downloadable room pack"):
            rev.verify_room_pack(out, room, "R3", stages)
        with ZipFile(out / "pack.zip", "w") as z:
            z.write(out / "final.png", "pictures/reading.png")
            z.write(out / "camera.png", "pictures/camera.png")
            z.writestr("index.html", "<img src='pictures/reading.png'>")
        rev.verify_room_pack(out, room, "R3", stages)
        (out / "final.png").write_bytes((out / "camera.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicates"):
            rev.verify_room_pack(out, room, "R3", stages)

    def test_homeowner_choice_survives_internal_saves_and_resumes_without_reasking(self):
        def cli(*args):
            output = io.StringIO()
            with patch.object(house, "HOUSES", self.home.parent), patch.object(sys, "argv", ["house.py", *args]), redirect_stdout(output):
                house.main()
            return output.getvalue()

        self.assertIn("Which space", cli("next", "Example home"))
        self.first_revision()
        self.assertIn("Reprice the units", cli("next", "Example home", "PIER-R1"))
        self.assertNotIn("?", cli("next", "Example home", "PIER-R1"))
        out = rev.begin(self.home, "R2", "PIER-R1")
        Image.new("RGB", (20, 20)).save(out / "checked plan.png")
        question = "Would you like a different hob position or the side cupboard?"
        text = cli("save-revision", "Example home", "R2", "--change", "Studied both positions",
                   "--why", "Serving crosses cooking", "--affects", "Dining", "--by", "Reviewer",
                   "--next", "Choose a serving routine", "--ask", question, "--ask-image", "checked plan.png",
                   "--image-description", "A shows the cupboard, B shows the shifted hob.")
        self.assertIn("![A shows", text)
        self.assertLess(text.index("![A shows"), text.index(question))
        self.assertIn(question, text)
        self.assertIn(question, cli("status", "Example home"))
        rev.begin(self.home, "R3", "R2")
        rev.save(self.home, "R3", **self.reason)
        self.assertIn(question, cli("next", "Example home"))
        reply = "Pause the kitchen and take the bathroom next."
        cli("answer", "Example home", "R2", reply)
        cli("answer", "Example home", "R2", reply)
        self.assertIn(reply, cli("next", "Example home"))
        with self.assertRaisesRegex(ValueError, "already has a reply"):
            cli("answer", "Example home", "R2", "Proceed")
        rev.begin(self.home, "R4", "R3")
        self.assertIn(reply, cli("status", "Example home"))
        self.assertNotIn(question, cli("next", "Example home", "R2"))
        final = rev.save(self.home, "R4", **self.reason)
        rec = rev.verify_revision(self.home, "R4")
        self.assertIn("handover-answers/R2.json", rec["inputs"])
        self.assertEqual(rev.stored_json(final / "inputs/handover-answers/R2.json")["answer"], reply)
        restored = self.folder / "restored"
        backups.restore("example-home", backups.backup_directory() / rec["backup"], restored)
        self.assertIn(reply, rev.next_choice(restored, rev.records(restored)))

    def test_visual_decision_gate_checks_drafts_saves_and_recovery(self):
        out = rev.begin(self.home, "R1")
        (out / "plan.png").write_bytes(b"not an image")
        question = "Which side would you serve from?"
        caption = "A is the kitchen side. B is the radiator side."
        for caller in (lambda **kw: rev.ask(self.home, "R1", question, image=kw.get("question_image"),
                                            description=kw.get("image_description")),
                       lambda **kw: rev.save(self.home, "R1", **self.reason, question=question, **kw)):
            for image, desc in ((None, None), ("plan.png", None), ("plan.png", caption),
                                ("missing.png", caption), ("../other.png", caption)):
                with self.subTest(image=image, caption=desc), self.assertRaises(ValueError):
                    caller(question_image=image, image_description=desc)
        Image.new("RGB", (24, 12), "green").save(out / "plan.png")
        original = (out / "plan.png").read_bytes()
        rev.ask(self.home, "R1", question, image="plan.png", description=caption)
        rev.ask(self.home, "R1", question, image="plan.png", description=caption)
        prompt = rev.next_choice(self.home, [])
        self.assertIn("![A is the kitchen side.", prompt)
        self.assertIn((out / "plan.png").as_posix(), prompt)
        self.assertIn(question, prompt)
        with self.assertRaisesRegex(ValueError, "differs"):
            rev.save(self.home, "R1", **self.reason, question="When?", question_kind="timing")
        (out / "plan.png").write_bytes(b"replaced")
        with self.assertRaisesRegex(ValueError, "changed"):
            rev.next_choice(self.home, [], "R1")
        with self.assertRaisesRegex(ValueError, "changed"):
            rev.save(self.home, "R1", **self.reason)
        (out / "plan.png").write_bytes(original)
        saved = rev.save(self.home, "R1", **self.reason)
        record = rev.verify_revision(self.home, "R1")
        self.assertEqual(record["question_image"]["sha256"], record["outputs"]["plan.png"])
        restored = self.folder / "fresh"
        backups.restore("example-home", backups.backup_directory() / record["backup"], restored)
        self.assertIn(restored.as_posix(), rev.next_choice(restored, rev.records(restored)))
        (saved / "outputs/plan.png").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            rev.next_choice(self.home, [record])

    def test_text_decision_and_reply_during_study(self):
        out = rev.begin(self.home, "R1")
        (out / "scope.txt").write_text("Budget priorities")
        rev.ask(self.home, "R1", "What is the ceiling?", kind="budget")
        self.assertNotIn("![", rev.next_choice(self.home, []))
        rev.record_answer(self.home, "R1", "Ten thousand pounds.")
        self.assertIn("Ten thousand", rev.next_choice(self.home, []))
        rev.save(self.home, "R1", **self.reason)
        self.assertNotIn("What is the ceiling?", rev.next_choice(self.home, rev.records(self.home)))

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

    def test_rolling_backup_keeps_all_saved_revisions_and_survives_failed_replacement(self):
        self.first_revision()
        first = rev.verify_revision(self.home, "PIER-R1")
        archive = backups.backup_directory() / first["backup"]
        previous = archive.read_bytes()
        (self.home / "views/new.png").write_bytes(b"later view")
        out = rev.begin(self.home, "pier-r2", "pier-r1")
        (out / "design/plan.pdf").write_bytes(b"revised")
        with patch.object(backups, "read_payload", side_effect=ValueError("Verification failed")):
            with self.assertRaisesRegex(ValueError, "Verification failed"):
                rev.save(self.home, "pier-r2", **self.reason)
        self.assertEqual(archive.read_bytes(), previous)
        rev.save(self.home, "pier-r2", **self.reason)
        self.assertEqual(list(backups.backup_directory().rglob("*.zip")), [archive])
        with ZipFile(archive) as recovered:
            self.assertEqual(backups.manifest(recovered, "example-home")["format"], 1)
        for number in (1, 2):
            revision = f"PIER-R{number}"
            record = rev.verify_revision(self.home, revision)
            target = self.folder / f"recovered-{number}"
            archive = backups.backup_directory() / record["backup"]
            backups.restore("example-home", archive, target)
            self.assertEqual(rev.verify_revision(target, revision), record)
            self.assertEqual(len(rev.records(target)), 2)
            self.assertTrue((target / "views/new.png").is_file())

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
