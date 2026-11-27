import unittest

from room_by_room.house_openings import review
import test_openings
from test_routes import rect
from room_by_room.house_walkthrough import check


def scene():
    stops = {
        "hall": {"kind": "access", "point": [500, 1500]},
        "garden": {"kind": "access", "point": [5500, 1500]},
        "chair": {"kind": "seat", "object": "Chair", "point": [1500, 1100],
                  "use_space": rect(1000, 600, 2000, 1500)},
        "cupboard": {"kind": "operating", "object": "Cupboard", "point": [4500, 2000],
                    "use_space": rect(4000, 1600, 5000, 2500)},
    }
    study = {"floor": rect(0, 0, 6000, 3000), "obstacles": {
        "Chair": rect(1000, 200, 2000, 600), "Cupboard": rect(4000, 2500, 5000, 3000),
        "Plant": rect(3000, 2500, 3200, 2700)}, "stops": stops, "journeys": {
            name: {"from": "hall", "to": name, "width_mm": 650, "uncertainty_mm": 10}
            for name in ("garden", "chair", "cupboard")}}
    study["scene_objects"] = list(study["obstacles"])
    return ({"walkthrough": study, "revision": "R2", "units": "mm", "basis": "synthetic room"},
            {"walkthrough_stops": {name: stop["kind"] for name, stop in stops.items()}})


class FullyDressedWalkthrough(unittest.TestCase):
    def test_final_placement(self):
        for plant, expected in [
            (rect(1350, 650, 1450, 750), "chair: Plant"),
            (rect(4600, 2200, 4800, 2400), "cupboard: Plant"),
            (rect(2900, 0, 3300, 2600), "garden: restricted"),
            (rect(2900, 900, 3300, 1800), None),
        ]:
            camera, cad = scene()
            camera["walkthrough"]["obstacles"]["Plant"] = plant
            with self.subTest(expected=expected):
                result = check(camera, cad)
                if expected:
                    self.assertIn(expected, result)
                else:
                    self.assertIsNone(result)

    def test_late_native_plant_needs_a_footprint(self):
        camera, cad = scene()
        del camera["walkthrough"]["obstacles"]["Plant"]
        self.assertIn("Plant", check(camera, cad))

    def test_incomplete_inventory_or_route_holds(self):
        camera, cad = scene()
        del camera["walkthrough"]["journeys"]["cupboard"]
        self.assertIn("connect every", check(camera, cad))
        del camera["walkthrough"]["stops"]["cupboard"]
        self.assertIn("omits", check(camera, cad))

    def test_pre_dressing_opening_pass_is_insufficient(self):
        fixture = test_openings.OperatingClearances()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.spec["geometry"]["lip"]["z"] = [81,83]
        self.assertIsNone(fixture.check())
        fixture.spec.update(model="outputs/Scene.blend", cad_revision="R2")
        (fixture.out/"Scene.blend").write_bytes(b"fixture")
        self.assertIsNone(fixture.check(camera=True))
        self.assertIn("fully dressed", review(fixture.root, "study", "R2", camera=True, walkthrough=True))
