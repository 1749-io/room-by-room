import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import house_openings


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
