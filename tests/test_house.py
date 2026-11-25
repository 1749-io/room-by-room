import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import house

class HomeownerWorkflow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        settings = patch.object(house.house_backup, "backup_directory", return_value=self.root / "backups")
        settings.start()
        self.addCleanup(settings.stop)
        bound = patch.object(house,"HOUSES",self.root/"houses")
        bound.start()
        self.addCleanup(bound.stop)

    def test_two_houses_keep_their_briefs_and_rooms_separate(self):
        brief=self.root/"original.pdf"
        brief.write_bytes(b"original bytes")
        first=house.initialise("First home",brief,["Office"])
        second=house.initialise("Second home",None,["Kitchen"])
        self.assertEqual((first/"source/original-brief/original.pdf").read_bytes(),brief.read_bytes())
        with (first / "sources.csv").open(encoding="utf-8", newline="") as stream:
            source, = csv.DictReader(stream)
        self.assertEqual((first / source["relative_path"]).read_bytes(), brief.read_bytes())
        self.assertEqual(source["source_id"], "E01")
        self.assertFalse((second/"rooms/office").exists())
        self.assertEqual(house.read_status(first),["office: brief / pending"])
        with self.assertRaises(ValueError):
            house.initialise("First home",None,[])
        with self.assertRaises(ValueError):
            house.add_room(first,"Office")
        self.assertTrue((first/"rooms/office/README.md").is_file())

    def test_failed_setup_leaves_no_partial_house(self):
        with self.assertRaises(ValueError):
            house.initialise("Retreat",None,["Hall","Hall"])
        self.assertFalse((house.HOUSES/"retreat").exists())

    def test_review_requires_evidence_from_this_house_and_current_revision(self):
        place=house.initialise("Terrace",None,["Kitchen"])
        file=place/"rooms/kitchen/review.csv"
        with file.open(newline="") as f:
            rows=list(csv.reader(f))
        rows[1][1:]=["pass","03","../other.pdf","Reviewer","Compared to survey"]
        def save():
            with file.open("w",newline="") as f:
                csv.writer(f).writerows(rows)
        save()
        self.assertIn("evidence or review details missing",house.read_status(place)[0])
        rows[1][3]="brief.md"
        rows[2][1:]=["pass","02","brief.md","Reviewer","Compared walls"]
        save()
        self.assertIn("revision differs",house.read_status(place)[0])
        rows[2][2]="03"
        save()
        self.assertIn("save a revision", house.read_status(place)[0])
        draft = house.revisions.begin(place, "survey")
        (draft / "plan.txt").write_text("Checked against survey")
        house.revisions.save(place, "survey", change="Save plan", why="Measured baseline",
                             author="Reviewer", affects="Kitchen", next_step="Check the proposal")
        rows[2][3]="revisions/SURVEY/outputs/plan.txt"
        save()
        self.assertIn("proposed-cad / pending",house.read_status(place)[0])
        (place / rows[2][3]).write_text("Replaced outside the house workflow")
        self.assertIn("cannot verify saved evidence", house.read_status(place)[0])

    def test_legacy_cad_pass_cannot_skip_existing_condition_review(self):
        place=house.initialise("Legacy",None,["Lounge"])
        review=place/"rooms/lounge/review.csv"
        with review.open(newline="") as f:
            rows=list(csv.reader(f))
        del rows[2]
        rows[2][0]="cad"
        for row in rows[1:3]:
            row[1:]=["pass","01","brief.md","Reviewer","Previous issue"]
        with review.open("w",newline="") as f:
            csv.writer(f).writerows(rows)
        self.assertIn("existing-cad / pending",house.read_status(place)[0])

    def test_layout_gate_requires_current_intent_activity_and_journey_evidence(self):
        place = house.initialise("Cottage", None, ["Lounge"])
        room = place / "rooms/lounge"
        register = room / "layout-checks.csv"
        header = register.read_text().strip()
        intent = "03,intent,brief,chair beside window,position checked,brief.md,pass"
        use = "03,use,brief,reach the table while seated,reach checked,brief.md,pass"
        journey = "03,journey,brief,walk from hall to dining,both door hands checked,brief.md,pass"
        whole = "03,whole-room,brief,combine occupied activities,overlay checked,rooms/lounge/plan.svg,pass"
        (room / "plan.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
        for rows, expected in [
            ([intent, use], "journey"),
            ([intent, journey, use.replace("03,", "02,")], "missing current layout checks: use"),
            ([intent, journey, use.replace("pass", "hold")], "unresolved"),
            ([intent, journey, use.replace("brief.md", "missing.png")], "missing"),
            ([intent, journey, use.replace("reach checked", "")], "observation"),
            ([intent, journey, use.replace("brief.md", "../elsewhere.md")], "missing"),
            ([intent, journey, use, use.replace(",use,", ",other,")], "unknown layout check kind"),
        ]:
            register.write_text("\n".join([header, whole, *rows]))
            self.assertIn(expected, house.check_layout_evidence(place, room, "03"))
        old_hold = use.replace("03,", "02,").replace("pass", "hold")
        register.write_text("\n".join([header, old_hold, intent, use, journey, whole]))
        self.assertIsNone(house.check_layout_evidence(place, room, "03"))
        for row, expected in [
            (whole.replace("03,", "02,"), "whole-room"),
            (whole.replace("plan.svg", "absent.svg"), "missing"),
            (whole.replace("rooms/lounge/plan.svg", "brief.md"), "reviewed CAD plan"),
            (whole.replace(",pass", ",hold"), "unresolved"),
        ]:
            register.write_text("\n".join([header, intent, use, journey, row]))
            self.assertIn(expected, house.check_layout_evidence(place, room, "03"))

    def test_each_intended_position_needs_current_evidence_for_its_activity(self):
        place = house.initialise("Workshop", None, ["Studio"])
        room = place / "rooms/studio"
        (room / "activity-positions.csv").write_text(
            "check_id,activity,position\nmain,See demonstration,Main bench\nside,See demonstration,Side bench\n"
        )
        plan = room / "plan.svg"
        plan.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        evidence = "rooms/studio/plan.svg"
        checks = room / "layout-checks.csv"
        rows = [checks.read_text().strip()] + [
            f"02,{kind},brief,test,observed,{evidence},pass,{key}"
            for kind, key in [("intent",""),("journey",""),("whole-room",""),("use","main")]
        ]
        rows.append(f"01,use,brief,old placement,observed,{evidence},pass,side")
        checks.write_text("\n".join(rows))
        self.assertIn("Side bench", house.check_layout_evidence(place, room, "02"))
        rows.append(f"02,use,brief,current placement,observed,{evidence},hold,side")
        checks.write_text("\n".join(rows))
        self.assertIn("unresolved", house.check_layout_evidence(place, room, "02"))
        rows[-1] = rows[-1].replace(",hold,", ",pass,")
        checks.write_text("\n".join(rows))
        self.assertIsNone(house.check_layout_evidence(place, room, "02"))

    def test_cli_checks_new_and_upgraded_houses_without_releasing_held_renders(self):
        def cli(*args, passed=True):
            result = subprocess.run([sys.executable, str(house.ROOT / "house.py"), "--houses-dir",
                                     str(self.root / "houses"), *args], capture_output=True, text=True,
                                    env={**os.environ, "HOUSE_BACKUP_DIR": str(self.root / "backups")})
            self.assertEqual(result.returncode, 0 if passed else 1, result.stderr)
            return result.stdout + result.stderr

        cli("start", "Terrace", "--room", "Kitchen")
        working = Path(cli("begin-revision", "Terrace", "R1").strip())
        (working / "review.txt").write_text("Test evidence")
        cli("save-revision", "Terrace", "R1", "--change", "Save design", "--why", "Test handovers",
            "--by", "Reviewer", "--affects", "Kitchen", "--next", "Check the plan")
        evidence = "revisions/R1/outputs/review.txt"
        cli("add-room", "Terrace", "Dining")
        self.assertIn("brief / pending", cli("check-study", "Terrace", "Kitchen", passed=False))
        kitchen = self.root / "houses/terrace/rooms/kitchen"
        dining = kitchen.parent / "dining/layout-checks.csv"
        register = kitchen / "layout-checks.csv"
        header = register.read_text().strip()
        register.write_text(header + "\nR1,intent,brief,face the garden,compared,brief.md,pass\n")
        dining.unlink()
        self.assertIn("dining", cli("prepare-reviews", "Terrace"))
        self.assertEqual(cli("prepare-reviews", "Terrace"), "")
        self.assertEqual(dining.read_text().strip(), header)
        self.assertIn("face the garden", register.read_text())

        with (kitchen / "review.csv").open(newline="") as handle:
            reviews = list(csv.reader(handle))
        for row in reviews[1:4]:
            row[1:] = ["pass", "R1", evidence, "Reviewer", "Compared with plan"]
        reviews[4][1] = "hold"
        with (kitchen / "review.csv").open("w", newline="") as handle:
            csv.writer(handle).writerows(reviews)
        self.assertIn("missing current layout checks", cli("check-layout", "Terrace", "Kitchen", passed=False))
        self.assertIn("reviewed through existing-cad", cli("check-study", "Terrace", "Kitchen", "--input-revision", "R1"))
        self.assertIn("differs from reviewed", cli("check-study", "Terrace", "Kitchen", "--input-revision", "R0", passed=False))
        with register.open("a") as handle:
            handle.write("R1,use,brief,unload dishwasher,storage accessible,brief.md,pass\n")
            handle.write("R1,journey,brief,carry food to dining,occupied route checked,brief.md,pass\n")
        self.assertIn("whole-room", cli("check-layout", "Terrace", "Kitchen", passed=False))
        (kitchen / "plan.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L2 3"/></svg>')
        with register.open("a") as handle:
            handle.write("R1,whole-room,brief,serve while unloading,overlay checked,rooms/kitchen/plan.svg,pass\n")
        self.assertIn("reviewed through proposed-cad", cli("check-layout", "Terrace", "Kitchen"))
        self.assertIn("kitchen: blender / hold", cli("status", "Terrace"))
        self.assertIn("blender / hold", cli("check-render", "Terrace", "Kitchen", "blender", passed=False))
        reviews[4][1] = "pending"
        with (kitchen / "review.csv").open("w", newline="") as handle:
            csv.writer(handle).writerows(reviews)
        self.assertIn("blender may proceed", cli("check-render", "Terrace", "Kitchen", "blender"))
        self.assertIn("differs from reviewed", cli("check-render", "Terrace", "Kitchen", "blender", "--input-revision", "R0", passed=False))
        self.assertIn("differs from reviewed", cli("check-layout", "Terrace", "Kitchen", "--input-revision", "R0", passed=False))
        project = kitchen.parents[1]
        review = kitchen / "review.csv"
        self.assertTrue(house.render_status(project, review, "blender", input_revision="R1")[0])
        allowed, finding = house.render_status(project, review, "blender", input_revision="R0")
        self.assertFalse(allowed)
        self.assertIn("input revision R0 differs from reviewed R1", finding)
        self.assertIn("blender / pending", cli("check-render", "Terrace", "Kitchen", "final-ai", passed=False))
        for row in reviews[4:6]:
            row[1:] = ["pass", "R1", evidence, "Reviewer", "Checked camera and products"]
        reviews[6][1] = "hold"
        with (kitchen / "review.csv").open("w", newline="") as handle:
            csv.writer(handle).writerows(reviews)
        self.assertIn("record current lighting and finish", cli("check-render", "Terrace", "Kitchen", "final-ai", passed=False))
        finishes = kitchen / "finish-checks.csv"
        finish_header = finishes.read_text().strip()
        image = "rooms/kitchen/finish.jpg"
        (kitchen / "finish.jpg").write_bytes(b"fixture")
        lighting = f"R1,lighting,window,property photo,{image},window shadow checked,pass"
        product = f"R1,finish,cabinet,selected swatch,{image},grain and colour checked,pass"
        palette = f"R1,room-palette,Kitchen,brief.md,{image},cabinet stands out against flooring in daylight,pass"
        finishes.write_text("\n".join([finish_header, lighting, product]))
        self.assertIn("whole-room palette review", cli("check-render", "Terrace", "Kitchen", "final-ai", passed=False))
        for invalid, expected in [
            (product.replace("R1,", "R0,"), "current lighting and finish"),
            (product.replace(",pass", ",hold"), "resolve the lighting"),
            (product.replace(image, "../elsewhere.jpg"), "within this house"),
            (product.replace(image, "brief.md"), "comparison image"),
        ]:
            finishes.write_text("\n".join([finish_header, lighting, invalid, palette]))
            self.assertIn(expected, cli("check-render", "Terrace", "Kitchen", "final-ai", passed=False))
        finishes.write_text("\n".join([finish_header, lighting, product, palette]))
        self.assertIn("final-ai / hold", cli("check-render", "Terrace", "Kitchen", "final-ai", passed=False))
        reviews[6][1] = "pending"
        with review.open("w", newline="") as handle:
            csv.writer(handle).writerows(reviews)
        self.assertIn("final-ai may proceed", cli("check-render", "Terrace", "Kitchen", "final-ai", "--input-revision", "R1"))
        self.assertIn("differs from reviewed", cli("check-render", "Terrace", "Kitchen", "final-ai", "--input-revision", "R0", passed=False))
        for row in reviews[6:]:
            row[1:] = ["pass", "R1", evidence, "Reviewer", "Reviewed test issue"]
        with review.open("w", newline="") as handle:
            csv.writer(handle).writerows(reviews)
        self.assertIn("record the final image colour comparison", cli("status", "Terrace"))
        (kitchen / "final.jpg").write_bytes(b"final fixture")
        with finishes.open("a") as stream:
            stream.write(f"\nR1,ai-colour,hero,{image},rooms/kitchen/final.jpg,compared finished image,pass\n")
        self.assertIn("kitchen: reviewed through handover / R1", cli("status", "Terrace"))

    def test_colour_choices_and_image_drift_hold_the_affected_handover(self):
        place = house.initialise("Grove", None, ["Study"])
        room = place / "rooms/study"
        register = room / "finish-checks.csv"
        header = register.read_text().strip()
        camera = "rooms/study/blender.jpg"
        final = "rooms/study/ai.jpg"
        (place / camera).write_bytes(b"camera")
        (place / final).write_bytes(b"issued photo")
        regular = [f"R2,{kind},desk,supplier,{camera},compared,pass" for kind in ("lighting", "finish")]
        scheme = f"R2,room-palette,Study,brief.md,{camera},requested bold pink desk stands out against teal walls,pass"

        def write(*extra):
            register.write_text("\n".join([header, *regular, *extra]))

        def check(stage):
            return house.check_finish_evidence(place, room, "R2", stage)

        pending = "R2,palette,walls,brief,,Keep the tonal wall or try a lighter sample?,hold"
        selected = "R2,palette,walls,owner,decisions.md,owner selected the muted shade,pass"
        drift = f"R2,ai-colour,hero,{camera},{final},AI changed specified velvet,hold"
        passed = f"R2,ai-colour,hero,{camera},{final},velvet matched in corrected photo,pass"
        for invalid, expected in [
            (selected, "whole-room palette review"),
            (scheme.replace("R2,", "R1,"), "whole-room palette review"),
            (scheme.replace("brief.md", "missing.md"), "brief or recorded palette decision"),
            (scheme.replace(camera, "brief.md"), "reviewed furnished room view"),
            (scheme.replace(camera, "../external.jpg"), "reviewed furnished room view"),
            (scheme.replace(",pass", ",hold"), "whole-room palette finding for Study"),
        ]:
            with self.subTest(invalid=invalid):
                write(invalid)
                self.assertIn(expected, check("products"))
        regular.append(scheme)
        write(pending)
        finding = check("products")
        self.assertIn("open palette choice for walls", finding)
        self.assertIn("Keep the tonal wall or try a lighter sample?", finding)
        write(selected.replace("decisions.md", "absent.md"))
        self.assertIn("homeowner's choice", check("products"))
        write(selected, drift)
        self.assertIsNone(check("products"))
        self.assertIn("final image colour finding", check("final-ai"))
        write(selected, passed.replace(final, camera))
        self.assertIn("separate files", check("final-ai"))
        write(selected, passed.replace("R2,", "R1,"))
        self.assertIn("record the final image", check("final-ai"))
        write(selected, passed, drift.replace("hero,", "reverse,"))
        self.assertIn("reverse", check("final-ai"))
        write(passed)
        self.assertIsNone(check("products"))
        self.assertIsNone(check("final-ai"))

    def test_decorator_release_is_scoped_to_the_surface_revision_and_owner_decision(self):
        place = house.initialise("Orchard", None, ["Cinema"])
        room = place / "rooms/cinema"
        register = room / "decorator-finishes.csv"
        header = register.read_text().strip()
        walls = "R1,Walls,,Muted blue,,,sample required,brief.md"
        trim = "R1,Joinery,Example,Cloud,C1,Satin,approved,decisions.md"

        def write(*rows):
            register.write_text("\n".join([header, *rows]))

        def check(surface=None):
            return house.check_decorator(place, room, "R1", surface)

        write(walls, trim)
        self.assertIn("Walls: sample required", check())
        self.assertIsNone(check("joinery"))
        self.assertIn("no decorator finish", check("ceiling"))
        write(trim.replace("R1,", "R0,"))
        self.assertIn("no decorator finish", check())
        write(trim.replace(",Satin,", ",,"))
        self.assertIn("named colour and finish", check())
        write(trim.replace("decisions.md", "../elsewhere.md"))
        self.assertIn("recorded sample approval", check())
        write(trim, trim)
        self.assertIn("distinct entry", check())
        write(trim)
        self.assertIsNone(check())
