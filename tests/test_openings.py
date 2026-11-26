import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from room_by_room import house_openings
from room_by_room import house_revisions as revisions


def box(x, y, z, width, depth, height):
    return {"xy": [[x,y], [x+width,y], [x+width,y+depth], [x,y+depth]], "z": [z,z+height]}


class OperatingClearances(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / "outputs"
        (self.out / "openings").mkdir(parents=True)
        self.spec = dict(revision="R2", room="study", units="mm", basis="Measured native model",
                         model="outputs/Plan.FCStd", model_sha256=hashlib.sha256(b"fixture").hexdigest(),
                         geometry={"case": box(-20,0,0,15,100,100), "leaf travel": box(0,0,15,100,100,60),
                                   "lip": box(50,40,40,10,8,8)},
                         door_heads={}, no_doors_reason="Isolated cabinet test",
                        zones=[dict(name="Opening", travel="Entire movement including the handle",
                                     installed=["case"], sweeps=["leaf travel"], obstacles=["lip"],
                                     required_mm=3, uncertainty_mm=2)])
        (self.out / "Plan.FCStd").write_bytes(b"fixture")

    def check(self, camera=False):
        suffix = ".camera" if camera else ""
        (self.out / "openings" / ("study"+suffix+".json")).write_text(json.dumps(self.spec))
        return house_openings.review(self.root,"study","R2",camera=camera)

    def test_intermediate_contact_vertical_clearance_and_uncertainty(self):
        self.assertIn("leaf travel / lip",self.check())
        self.spec["geometry"]["lip"]["z"] = [75,83]
        self.assertIn("0.0 mm",self.check())
        self.spec["geometry"]["lip"]["z"] = [79,87]
        self.assertIn("4.0 mm",self.check())
        self.spec["geometry"]["lip"]["z"] = [80,88]
        self.assertIsNone(self.check())
        self.spec["zones"][0]["uncertainty_mm"] = None
        self.assertIn("still to measure",self.check())

    def test_installed_carcass_and_separate_hardware(self):
        self.spec["geometry"]["lip"] = box(-10,40,40,2,8,8)
        self.assertIn("case / lip",self.check())
        self.spec["geometry"]["lip"] = box(104,40,40,2,8,8)
        self.spec["geometry"]["handle"] = box(92,40,40,16,5,4)
        self.spec["zones"][0]["sweeps"].append("handle")
        self.assertIn("handle / lip",self.check())

    def test_report_evidence_fails_closed(self):
        self.assertIn("missing CAD",house_openings.review(self.root,"study","R2"))
        self.spec["revision"]="R1"
        self.assertIn("revision",self.check())
        self.spec["revision"]="R2"
        del self.spec["geometry"]["lip"]
        self.assertIn("Missing geometry",self.check())
        self.spec["zones"]=[]
        self.assertIn("explain why",self.check())
        self.spec["no_interfaces_reason"]="Review of the empty room shell only"
        self.assertIn("unassessed",self.check())
        self.spec["geometry"] = {}
        self.assertIsNone(self.check())
        (self.out/"Plan.FCStd").write_bytes(b"changed")
        self.assertIn("model changed",self.check())

    def test_camera_adds_projection_and_cannot_clear_a_failed_cad_study(self):
        self.assertIn("leaf travel",self.check())
        self.spec.update(model="outputs/Scene.blend",cad_revision="R2")
        (self.out/"Scene.blend").write_bytes(b"fixture")
        self.spec["geometry"]["lip"]["z"]=[81,89]
        self.assertIn("leaf travel / lip",self.check(camera=True))
        self.spec["zones"][0]["obstacles"].append("shelf")
        self.assertIn("different opening interfaces",self.check(camera=True))
        self.spec["cad_revision"]="R1"
        self.assertIn("CAD revision",self.check(camera=True))

    def test_missing_head_above_2040_leaf_in_2400_partition(self):
        def band(role, bottom, top):
            return {"id": role, "role": role, "xz": [[0,bottom],[916,bottom],[916,top],[0,top]]}
        (self.out / "door.txt").write_bytes(b"Design elevation")
        intended = [band("open", 0, 4), band("opaque", 4, 360)]
        door = {"basis":"Closed head with operating reveal", "design_reference":"outputs/door.txt",
                "design_sha256":hashlib.sha256(b"Design elevation").hexdigest(),
                "field_mm":[916,360], "expected":intended, "observed":intended}
        self.spec.update(door_heads={"utility":door}, zones=[], geometry={}, no_interfaces_reason="Elevation only")
        self.assertIsNone(self.check())
        self.spec.update(cad_revision="R2", model="outputs/Scene.blend")
        (self.out/"Scene.blend").write_bytes(b"fixture")
        door["observed"] = [band("open", 0, 360)]
        self.assertIn("differs from the design", self.check(camera=True))
        door["observed"] = [band("opaque", 4, 350), band("open",0,4)]
        self.assertIn("unexplained gap", self.check(camera=True))
        door["observed"] = intended
        self.assertIsNone(self.check(camera=True))
        self.spec["door_heads"] = {}
        self.assertIn("inventory",self.check(camera=True))

    def test_designed_overlight_and_open_head(self):
        for role in ["glazing", "open"]:
            piece = {"id":"fanlight or open detail", "role":role, "xz":[[0,0],[920,0],[920,300],[0,300]]}
            self.spec.update(door_heads={"partition":dict(basis="Selected elevation",design_reference="outputs/Plan.FCStd",
                             design_sha256=self.spec["model_sha256"],field_mm=[920,300],expected=[piece],observed=[piece])},
                             zones=[],geometry={},no_interfaces_reason="Head only")
            self.assertIsNone(self.check())
        del self.spec["door_heads"]
        self.assertIn("door_heads",self.check())


class SavedOpeningCorrection(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "cottage"
        self.room = self.root / "rooms/study"
        self.room.mkdir(parents=True)
        revisions.write_json(self.root / "project.json", {"id": "fictional"})
        self.file_hash = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

    def issue(self, *, changed=False, travel=False, clash=False, room="study", stale=False):
        snapshots = self.root / "revisions"
        binding_inputs = {}
        for rev in ("BASE", "FIX"):
            folder = snapshots / rev
            (folder / "outputs/openings").mkdir(parents=True)
            (folder / "inputs").mkdir()
            for model, suffix in (("Room.FCStd", ".json"), ("Room.blend", ".camera.json")):
                native = folder / "outputs" / model
                native.write_text("changed" if changed and rev == "FIX" else "baseline")
                spec = dict(room="study", revision=rev, units="mm", basis="Fictional native read-back",
                            model="outputs/" + model, model_sha256=self.file_hash(native), cad_revision=rev)
                if rev == "BASE" or travel:
                    spec.update(zones=[dict(name="Door", travel="Full travel", required_mm=1, uncertainty_mm=1,
                                            installed=["leaf"], sweeps=["arc"], obstacles=["bench"])],
                                geometry={"leaf": box(1,1,0,1,1,10), "arc": box(2,1,0,2,2,10),
                                          "bench": box(3 if clash else 10,1,0,1,1,10)})
                if rev == "FIX":
                    band = {"id": "Lintel", "role": "opaque", "xz": [[0,0],[910,0],[910,300],[0,300]]}
                    spec["door_heads"] = {"door": dict(basis="Solid partition", field_mm=[910,300],
                        design_reference="outputs/Room.FCStd", design_sha256=self.file_hash(folder/"outputs/Room.FCStd"),
                        expected=[band], observed=[band])}
                path = folder / "outputs/openings" / ("study"+suffix)
                revisions.write_json(path, spec)
                binding_inputs[path.relative_to(self.root).as_posix()] = path.read_bytes()
            self.seal(folder)
        binder = snapshots / "CHECK"
        (binder / "outputs/opening-addenda").mkdir(parents=True)
        for key, raw in binding_inputs.items():
            p = binder / "inputs" / key
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"stale report" if stale else raw)
        revisions.write_json(binder / "outputs/opening-addenda/study.json",
                             dict(source_revision="BASE", study_revision="FIX", room=room, reviewer="Fixture reviewer"))
        self.seal(binder)
        revisions.write_json(self.room / "opening-review-addendum.json", dict(source_revision="BASE", revision="CHECK"))

    def seal(self, folder):
        record = dict(house="fictional", revision=folder.name)
        for kind in ("inputs", "outputs"):
            root = folder / kind
            record[kind] = {p.relative_to(root).as_posix(): self.file_hash(p) for p in root.rglob("*") if p.is_file()}
        revisions.write_json(folder / "record.json", record)

    def current(self, **options):
        return house_openings.registered_review(self.root, "study", "BASE", **options)

    def test_identical_native_model_reuses_verified_movement(self):
        self.issue()
        self.assertIsNone(self.current())
        self.assertIsNone(self.current(camera=True))
        (self.root / "revisions/FIX/outputs/Room.blend").write_bytes(b"later edit")
        self.assertIn("Checksum differs", self.current(camera=True))

    def test_changed_native_model_requires_fresh_movement(self):
        self.issue(changed=True)
        for camera in (False, True):
            self.assertIsNone(self.current(camera=camera, heads_only=True))
            self.assertIn("Remeasure full travel", self.current(camera=camera))

    def test_complete_remeasurement_on_changed_models(self):
        self.issue(changed=True, travel=True)
        self.assertIsNone(self.current(camera=True))

    def test_head_correction_preserves_real_clash(self):
        self.issue(clash=True)
        self.assertIsNone(self.current(heads_only=True))
        self.assertIn("arc / bench", self.current(camera=True))

    def test_binding_cannot_be_reassigned_to_another_room(self):
        self.issue(room="kitchen")
        self.assertIn("match the source revision, room and reviewer", self.current())

    def test_binding_rejects_stale_source_report(self):
        self.issue(stale=True)
        self.assertIn("stale opening study binding", self.current())

    def test_current_command_uses_the_requested_stage_register(self):
        self.issue()
        stages = ("brief", "existing-cad", "proposed-cad", "blender", "products", "final-ai", "handover")
        rows = [f"{stage},pass,{'BASE' if stage == 'proposed-cad' else 'FIX'},fixture,Reviewer,Checked"
                for stage in stages]
        (self.room / "review.csv").write_text(
            "stage,status,revision,evidence,reviewer,finding\n" + "\n".join(rows), encoding="utf-8")
        cli = [sys.executable, str(Path(__file__).resolve().parents[1] / "house.py"),
               "--houses-dir", str(self.root.parent), "check-openings", "Cottage", "Study",
               "--input-revision", "BASE", "--current", "--door-heads-only"]
        cad = subprocess.run(cli, capture_output=True, text=True)
        self.assertEqual(cad.returncode, 0, cad.stderr)
        camera = subprocess.run([*cli, "--camera"], capture_output=True, text=True)
        self.assertNotEqual(camera.returncode, 0)
        self.assertIn("currently registered FIX", camera.stderr)
