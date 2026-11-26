"""Turn reopened Alder model measurements (mm, world coordinates) into a room gate."""
from hashlib import sha256
import json
import math
from pathlib import Path


def rectangle(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def write_report(folder, model, readback, revision, cad_revision):
    folder = Path(folder)
    digest = sha256(model.read_bytes()).hexdigest()
    if readback["model_sha256"] != digest:
        raise ValueError("The model has changed since its native measurements were recorded")
    bounds = readback["bounds_mm"]
    design = folder / "library.json"
    spec = json.loads(design.read_text(encoding="utf-8"))
    door = spec["shell"]["west_door"]
    width, height = door["width"], spec["shell"]["height"] - door["height"]
    x0, y0, _, x1, y1, leaf_top = bounds["OpenDoor"]
    _, head_start, head_base, _, head_end, head_top = bounds["DoorHead"]
    if (x0, y0, x1, y1) != (0, door["hinge_y"], width, door["hinge_y"] + door["leaf_thickness"]):
        raise ValueError("The open leaf must match the hinge, parked position and thickness")
    if (head_start, head_end, leaf_top, head_top) != (y0, y0 + width, door["height"], spec["shell"]["height"]):
        raise ValueError("The reopened head span or elevation does not match the design")

    def elevation(reveal):
        return [
            {"id": "Working head clearance", "role": "open", "xz": rectangle(0, 0, width, reveal)},
            {"id": "Solid partition", "role": "opaque", "xz": rectangle(0, reveal, width, height)},
        ]

    def solid(b):
        return {"xy": rectangle(b[0], b[1], b[3], b[4]), "z": [b[2], b[5]]}

    obstacles = ["Chair", "Lamp", "Bookcase", "DoorHead"]
    geometry = {name: solid(bounds[name]) for name in ["OpenDoor", *obstacles]}
    # Circumscribing the sweep protects the whole travel, including the hinge-side thickness.
    radius = math.hypot(x1 - x0, y1 - y0)
    geometry["DoorTravel"] = solid([x0 - (y1 - y0), y0, 0, x0 + radius, y0 + radius, leaf_top])
    data = {
        "revision": revision, "cad_revision": cad_revision, "room": "library", "units": "mm",
        "basis": "Fictional model dimensions measured after reopening. Conservative full-travel bounds, with a 5 mm design allowance and no survey uncertainty in this synthetic example.",
        "model": "outputs/" + model.name, "model_sha256": digest,
        "door_heads": {"west-hall": {
            "basis": "A solid west partition above the 6 mm head reveal in the accepted example design.",
            "design_reference": "outputs/library.json", "design_sha256": sha256(design.read_bytes()).hexdigest(),
            "field_mm": [width, height], "expected": elevation(door["head_reveal"]),
            "observed": elevation(head_base - leaf_top),
        }},
        "geometry": geometry,
        "zones": [{"name": "Hall door beside the reading area", "travel": "Shut to 90 degrees",
                   "installed": ["OpenDoor"], "sweeps": ["DoorTravel"], "obstacles": obstacles,
                   "required_mm": 5, "uncertainty_mm": 0}],
    }
    out = folder / "openings"
    out.mkdir(exist_ok=True)
    target = out / ("library.camera.json" if model.suffix == ".blend" else "library.json")
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return target
