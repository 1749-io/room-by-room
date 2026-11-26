import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

import house
import house_photos as photos
import house_revisions as revisions
import house_visuals as visuals


class PhotoRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / photos.EXTERIOR_REGISTER).write_text("revision,photo,opening,room\n")
        self.out = self.root / "revisions/R1/outputs"
        (self.out / "photo-reviews").mkdir(parents=True)
        for slug in ("sunroom", "dining"):
            room = self.root / "rooms" / slug
            room.mkdir(parents=True)
            refs = {"final-ai": slug+".png", "handover": slug+".zip"}
            with (room/"review.csv").open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["stage","revision","status","evidence"])
                for g in house.GATES:
                    w.writerow([g,"R1","pass","revisions/R1/outputs/"+refs.get(g,"source.png")])
            with (room/"finish-checks.csv").open("w",newline="") as f:
                w = csv.writer(f)
                w.writerow(["revision","kind","source","evidence","result"])
                w.writerow(["R1","ai-colour","revisions/R1/outputs/"+slug+"-camera.png","revisions/R1/outputs/"+slug+".png","pass"])
            Image.new("RGB",(64,40),"red").save(self.out/(slug+".png"))
            Image.new("RGB",(64,40),"grey").save(self.out/(slug+"-camera.png"))
            brief = {"windows":{}, "basis":"Glazed room brief","views":{"whole-room":"Show the whole layout","operation":"Show deployed shade"},"openings":{"partition":"dining"} if slug=="sunroom" else {}}
            brief["architectural_details"] = {"wall_mounts": [], "openings": list(brief["openings"])}
            self.put(slug+"-brief",brief)
            item = {k:"Inspected against the model" for k in ["reviewer","composition","products_and_operation","light_and_finish","architecture","opening_inspection"]}
            detail = dict(visibility="visible", finding="Two continuous fixed panels", result="pass",
                          camera=[0, 0, 1, 1], photo=[0, 0, 1, 1], model_leaves=["fixed", "fixed"],
                          photo_leaves=["fixed", "fixed"], continuous_frame_and_hardware=True,
                          head_review=dict(expected="closed above", camera_state="closed above", photo_state="closed above",
                                           camera=[0,0,1,.2], photo=[0,0,1,.2], finding="Wall continues across the head."))
            item["architectural_details"] = {"wall_mounts": {}, "openings": {k: detail for k in brief["openings"]}}
            item.update(window_treatments={}, photo=slug+".png", camera=slug+"-camera.png", shows=list(brief["views"]), result="pass",
                        openings={"partition":"visible"} if slug=="sunroom" else {},visible_rooms=[])
            for k in ("photo","camera"):
                item[k+"_sha256"] = photos.digest(self.out/item[k])
            if slug=="sunroom":
                item["visible_rooms"]=[{"room":"dining","through":"partition","comparison":"Matches table and wall","status":"matched","revision":"R1","reference":"dining.png","sha256":item["photo_sha256"]}]
            self.put(slug,{"room":slug,"revision":"R1","photos":[item]})
            with ZipFile(self.out/(slug+".zip"),"w") as z:
                for name in [slug+".png",slug+"-camera.png","photo-reviews/"+slug+".json","photo-reviews/"+slug+"-brief.json"]:
                    z.write(self.out/name,name)
                z.writestr("pack.html","Reviewed room")
        self.prepare_visual_reviews()

    def prepare_visual_reviews(self):
        (self.root/"project.json").write_text('{"id":"fixture"}')
        model = self.out/"room-geometry.json"
        model.write_text('{"unit":"mm","opening_width":900}')
        def ref(path):
            return {"path": path.relative_to(self.root).as_posix(), "sha256": photos.digest(path)}
        native = dict(ref(model), revision="R1")
        scopes = ["room/dining", "room/sunroom", "house"]
        state = {"phase": "proposed", "status": "accepted", "revision": "R1", "scopes": scopes,
                 "arrangement": "Retain the partition and its opening.", "exclusions": ["Construction design"],
                 "geometry": [native], "features": {}, "supersedes": []}
        quote = "I accept the fixture's retained partition and opening."
        decision = self.root/"decision.md"
        decision.write_text(quote)
        binding = self.root/"binding.json"
        binding.write_text(json.dumps({"house": "fixture", "state": "rooms", "kind": "design-acceptance",
                           "arrangement_sha256": visuals.arrangement_signature(state), "decision_sha256": photos.digest(decision),
                           "by": "Example homeowner", "date": "2026-11-24", "quote": quote}))
        state["homeowner_decision"] = dict(ref(decision), kind="design-acceptance", by="Example homeowner",
                                           date="2026-11-24", quote=quote, binding=ref(binding))
        records = {}
        for slug in ("dining", "sunroom"):
            for view, name in (("camera", slug+"-camera.png"), ("photo", slug+".png")):
                records[name] = {"state":"rooms", "state_sha256":visuals.signature(state), "status":"signed", "view":view,
                                 "source":dict(ref(self.out/name), revision="R1"), "reviewer":"Example reviewer",
                                 "supersedes":[], "dependencies":[native], "features":{}, "limitations":[],
                                 "placements":[{"purpose":"photo-pack.room", "scope":"room/"+slug},
                                               {"purpose":"photo-pack.exterior", "scope":"house"}]}
        for name, fields in [("design-states.json", {"states":{"rooms":state}}), ("visual-approvals.json", {"visuals":records})]:
            (self.root/name).write_text(json.dumps(dict(version=1, house="fixture", **fields)))
        (self.out.parent/"record.json").write_text(json.dumps({"house":"fixture","revision":"R1",
              "outputs":{p.relative_to(self.out).as_posix():photos.digest(p) for p in self.out.rglob("*") if p.is_file()}}))

    @patch("house.status_through", return_value=(True, "pass"))
    def test_photographic_release_checks_the_placement_and_extra_archive_images(self, _):
        with ZipFile(self.out/"sunroom.zip", "a") as pack:
            pack.writestr("historic-locator.png", b"Unapproved historical plan")
        with self.assertRaisesRegex(ValueError, "historic-locator.*missing purpose-specific"):
            photos.house_issue(self.root)

    def test_saved_camera_addendum_checks_both_manifests(self):
        room = self.root / "rooms/dining"
        folder = self.root / "revisions/R2"
        refs = {}
        for name in ("dining.json", "dining-brief.json"):
            rel = "photo-reviews/" + name
            path = folder / "outputs" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((self.out / rel).read_bytes())
            refs[rel] = photos.digest(path)
            (self.out / rel).unlink()
        (folder / "record.json").write_text(json.dumps({"outputs": refs}))
        (room / "photo-review-addendum.json").write_text(json.dumps({"revision": "R2", "source_revision": "R1"}))
        self.assertEqual(photos.review(self.out, room, "R1")["room"], "dining")
        (folder / "outputs/photo-reviews/dining-brief.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "changed after save"):
            photos.review(self.out, room, "R1")

    def test_corrected_pair_is_bound_to_the_saved_addendum_and_original(self):
        room = self.root / "rooms/dining"
        out = self.root / "revisions/R2/outputs"
        (out / "photo-reviews").mkdir(parents=True)
        manifest = Path("photo-reviews/dining.json")
        brief = Path("photo-reviews/dining-brief.json")
        (out / brief).write_bytes((self.out / brief).read_bytes())
        doc = json.loads((self.out / manifest).read_text())
        entry = doc["photos"][0]
        entry["replaces"] = {k: entry[k] for k in ("camera", "photo")}
        for key in ("camera", "photo"):
            name = "corrected-" + key + ".png"
            (out / name).write_bytes(name.encode())
            entry[key] = name
            entry[key + "_sha256"] = photos.digest(out / name)
        (out / manifest).write_text(json.dumps(doc))
        files = {p.relative_to(out).as_posix(): photos.digest(p) for p in out.rglob("*") if p.is_file()}
        (out.parent / "record.json").write_text(json.dumps({"outputs": files}))
        (room / "photo-review-addendum.json").write_text(json.dumps({"revision": "R2", "source_revision": "R1"}))
        self.assertEqual(photos.review(self.out, room, "R1")["photos"][0]["photo"], "corrected-photo.png")
        (out / "corrected-camera.png").write_bytes(b"another camera")
        with self.assertRaisesRegex(ValueError, "Changed camera"):
            photos.review(self.out, room, "R1")

    def test_wall_art_and_glazed_leaf_defects_block_release(self):
        room = self.root / "rooms/sunroom"
        brief = json.loads((self.out / "photo-reviews/sunroom-brief.json").read_text())
        brief["architectural_details"]["wall_mounts"] = ["framed print beside partition"]
        self.put("sunroom-brief", brief)
        doc = self.doc()
        details = doc["photos"][0]["architectural_details"]
        mount = dict(visibility="visible", finding="Frame remains on the wall beside the trim",
                     result="pass", model_clearance_mm=35, photo_clear_of_opening=True,
                     camera=[0.1, 0.2, 0.4, 0.8], photo=[0.1, 0.2, 0.4, 0.8])
        details["wall_mounts"]["framed print beside partition"] = mount
        self.put("sunroom", doc)
        photos.review(self.out, room, "R1")
        opening = details["openings"]["partition"]
        for target, field, value in [(mount, "model_clearance_mm", -2), (mount, "photo_clear_of_opening", False),
                                     (mount, "photo", [1, 0, 0, 1]), (opening, "photo_leaves", ["open"]),
                                     (opening["head_review"], "photo_state", "intentional opening"), (opening["head_review"], "camera_state", "occluded"),
                                     (opening, "continuous_frame_and_hardware", False), (opening, "visibility", "occluded")]:
            with self.subTest(field=field):
                good = target[field]
                target[field] = value
                self.put("sunroom", doc)
                with self.assertRaises(ValueError):
                    photos.review(self.out, room, "R1")
                target[field] = good
        self.put("sunroom", doc)
        (room / "photo-defects.csv").write_text("photo_sha256,finding\n" + doc["photos"][0]["photo_sha256"] + ",Broken jamb\n")
        with self.assertRaisesRegex(ValueError, "Broken jamb"):
            photos.review(self.out, room, "R1")

    def put(self,name,doc):
        (self.out/"photo-reviews"/(name+".json")).write_text(json.dumps(doc))

    def doc(self):
        return json.loads((self.out/"photo-reviews/sunroom.json").read_text())

    def test_room_coverage_is_bound_to_pixels_and_sightlines(self):
        room=self.root/"rooms/sunroom"
        baseline=self.doc()
        for change in ({"shows":["whole-room"]}, {"photo_sha256":"wrong"}, {"visible_rooms":[]}, {"openings":{}}, {"result":"hold"}, {"composition":""}):
            with self.subTest(change=change):
                doc=json.loads(json.dumps(baseline));doc["photos"][0].update(change);self.put("sunroom",doc)
                with self.assertRaises(ValueError):
                    photos.review(self.out,room,"R1")
        self.put("sunroom",baseline)
        with ZipFile(self.out/"sunroom.zip","w") as z:
            z.write(self.out/"sunroom.png","sunroom.png");z.write(self.out/"sunroom-camera.png","sunroom-camera.png");z.writestr("index.html","hello")
        stages={r["stage"]:r for r in house.review_rows(room/"review.csv")}
        with self.assertRaises(ValueError):
            revisions.verify_room_pack(self.out,room,"R1",stages,photo_quality=True)

    def test_uncommissioned_adjoining_room_must_be_entirely_outside_frame(self):
        room = self.root / "rooms/sunroom"
        brief = json.loads((self.out / "photo-reviews/sunroom-brief.json").read_text())
        entry = {"outside_commission": "hall", "reason": "The hall doorway is behind this camera.",
                 "reference": "sunroom-camera.png", "sha256": photos.digest(self.out / "sunroom-camera.png")}
        brief["openings"]["hall door"] = entry
        brief["architectural_details"]["openings"].append("hall door")
        self.put("sunroom-brief", brief)
        doc = self.doc()
        image = doc["photos"][0]
        image["openings"]["hall door"] = "outside-frame"
        image["architectural_details"]["openings"]["hall door"] = {
            "visibility": "outside-frame", "finding": entry["reason"]}
        self.put("sunroom", doc)
        photos.review(self.out, room, "R1")
        for state in ("visible", "occluded"):
            image["openings"]["hall door"] = state
            self.put("sunroom", doc)
            with self.assertRaisesRegex(ValueError, "register and review"):
                photos.review(self.out, room, "R1")
        image["openings"]["hall door"] = "outside-frame"
        self.put("sunroom", doc)
        for override, failure in [({"outside_commission": "dining"}, "registered"),
                                  ({"sha256": "old"}, "framing evidence"), ({"reason": ""}, "reason")]:
            brief["openings"]["hall door"] = dict(entry, **override)
            self.put("sunroom-brief", brief)
            with self.assertRaisesRegex(ValueError, failure):
                photos.review(self.out, room, "R1")

    def test_each_declared_window_needs_a_comparison_even_when_room_is_hidden(self):
        room = self.root / "rooms/sunroom"
        brief_file = self.out / "photo-reviews/sunroom-brief.json"
        brief = json.loads(brief_file.read_text())
        brief["windows"] = {"far glazing": "dining"}
        self.put("sunroom-brief", brief)
        doc = self.doc()
        with self.assertRaisesRegex(ValueError, "every window"):
            photos.review(self.out, room, "R1")
        seen = {"visibility": "visible", "status": "matched", "treatment": "lined curtains",
                "state": "closed", "outside_face": "ivory lining", "comparison": "Lining fills the far pane",
                "revision": "R1", "reference": "revisions/R1/outputs/dining.png",
                "sha256": photos.digest(self.out / "dining.png")}
        doc["photos"][0]["window_treatments"] = {"far glazing": seen}
        self.put("sunroom", doc)
        photos.review(self.out, room, "R1", final_windows=True)
        for change, error in [({"revision": "R0"}, "stale"), ({"sha256": "wrong"}, "changed"),
                              ({"outside_face": ""}, "outside_face")]:
            bad = dict(seen, **change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, error):
                photos.window_review(self.root, self.out, "R1", brief["windows"], {"far glazing": bad})
        seen.update(status="provisional", follow_up="Decorator to confirm lining from the outside")
        self.put("sunroom", doc)
        photos.review(self.out, room, "R1")
        with self.assertRaisesRegex(ValueError, "provisional window"):
            photos.review(self.out, room, "R1", final_windows=True)

    def test_provisional_source_still_needs_the_reviewed_bytes(self):
        observation = {"visibility": "visible", "status": "provisional", "treatment": "roller blind",
                       "state": "raised", "outside_face": "pale lining", "comparison": "Short drop visible",
                       "follow_up": "Decorator to verify backing", "reference": "revisions/R1/outputs/dining.png",
                       "sha256": "superseded"}
        with self.assertRaisesRegex(ValueError, "provisional source"):
            photos.window_review(self.root, self.out, "R1", {"side": "dining"}, {"side": observation})

    def test_standalone_exterior_requires_registered_windows_and_unchanged_files(self):
        (self.root / photos.EXTERIOR_REGISTER).write_text(
            "revision,photo,opening,room\nR1,sunroom.png,far reflection,dining\n")
        inventory = photos.exterior_register(self.root)["R1"]
        with self.assertRaisesRegex(ValueError, "reconcile"):
            photos.exterior_review(self.root, self.out, "R1", inventory)
        image = self.doc()["photos"][0]
        image["openings"] = inventory["sunroom.png"]
        image["window_treatments"] = {"far reflection": {"visibility": "occluded", "comparison": "Brick pier hides the far window"}}
        manifest = {"revision": "R1", "photos": {"sunroom.png": image}}
        path = self.out / photos.EXTERIOR_REVIEW
        path.write_text(json.dumps(manifest))
        staged = photos.exterior_review(self.root, self.out, "R1", inventory, final=True)
        self.assertIn("exterior/R1/sunroom.png", staged)
        with patch("house.status_through", return_value=(True, "pass")), patch("house_revisions.verify_revision") as verify:
            self.assertIn("exterior/R1/sunroom.png", photos.house_issue(self.root))
            verify.assert_called_once_with(self.root, "R1")
        (self.out / image["camera"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed exterior camera"):
            photos.exterior_review(self.root, self.out, "R1", inventory)

    def test_whole_house_requires_an_explicit_exterior_inventory(self):
        (self.root / photos.EXTERIOR_REGISTER).unlink()
        with patch("house.status_through", return_value=(True, "pass")), self.assertRaisesRegex(ValueError, "Declare current exterior"):
            photos.house_issue(self.root)

    def test_duplicate_pixels_cannot_cover_a_second_photo(self):
        room = self.root / "rooms/sunroom"
        (self.out / "duplicate.png").write_bytes((self.out / "sunroom.png").read_bytes())
        with (room / "finish-checks.csv").open("a", newline="") as stream:
            csv.writer(stream).writerow(["R1", "ai-colour", "revisions/R1/outputs/sunroom-camera.png",
                                         "revisions/R1/outputs/duplicate.png", "pass"])
        doc = self.doc()
        doc["photos"].append(dict(doc["photos"][0], photo="duplicate.png"))
        self.put("sunroom", doc)
        with self.assertRaisesRegex(ValueError, "Repeated final photograph"):
            photos.review(self.out, room, "R1")

    @patch("house.status_through",return_value=(True,"review passed"))
    def test_assembly_rechecks_neighbour_revision_camera_and_room_pack(self,_):
        draft=self.root/"new";draft.mkdir()
        target=photos.package(self.root,draft)
        photos.verify_assembly(self.root,target)
        with self.assertRaises(ValueError):
            photos.package(self.root,draft)
        doc=self.doc()
        for fields in ({"status":"provisional"},{"revision":"R0"},{"reference":"sunroom.png"},{"sha256":"old"}):
            with self.subTest(fields=fields):
                item=json.loads(json.dumps(doc));item["photos"][0]["visible_rooms"][0].update(fields);self.put("sunroom",item)
                with self.assertRaisesRegex(ValueError,"adjoining|view into"):
                    photos.house_issue(self.root)
        self.put("sunroom",doc)
        with ZipFile(target,"a") as z:
            z.writestr("extra.txt","an unreviewed change")
        with self.assertRaisesRegex(ValueError,"inventory"):
            photos.verify_assembly(self.root,target)

    def test_unfinished_neighbour_blocks_even_when_provisional_is_disclosed(self):
        doc=self.doc();doc["photos"][0]["visible_rooms"][0]["status"]="provisional";self.put("sunroom",doc)
        photos.review(self.out,self.root/"rooms/sunroom","R1")
        def readiness(root,register,rows,stage):
            return (False,"CAD on hold") if register.parent.name=="dining" else (True,"pass")
        with patch("house.status_through",side_effect=readiness):
            with self.assertRaisesRegex(ValueError,"(?s)dining: CAD on hold.*unfinished"):
                photos.house_issue(self.root)
