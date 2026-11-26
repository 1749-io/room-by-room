"""Build and reopen the fictional library in FreeCAD. Dimensions are in mm."""
import json
from hashlib import sha256
from pathlib import Path


def build(output_folder):
    import FreeCAD as App
    import Part

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "Alder library.FCStd"
    report = folder / "Layout checks.json"
    if target.exists() or report.exists():
        raise FileExistsError("Choose an empty output directory for this replay")
    spec = json.loads(Path(__file__).with_name("library.json").read_text(encoding="utf-8"))
    shell, furniture = spec["shell"], spec["furniture"]
    w, d, h, t = (shell[k] for k in ("width", "depth", "height", "wall"))
    door, window = shell["west_door"], shell["south_window"]
    hinge, leaf, top = door["hinge_y"], door["width"], door["height"]
    start, end = window["west_edge"], window["west_edge"]+window["width"]
    doc = App.newDocument("AlderLibrary")
    try:
        def block(name, label, x, y, z, length, width, height, colour):
            obj = doc.addObject("Part::Box", name)
            obj.Label = label
            obj.Length, obj.Width, obj.Height = length, width, height
            obj.Placement.Base = App.Vector(x, y, z)
            obj.ViewObject.ShapeColor = colour
            return obj

        wall = (0.87, 0.84, 0.75)
        oak = (0.62, 0.43, 0.25)
        sage = (0.44, 0.53, 0.40)
        block("Floor", "Oak floor", 0, 0, -25, w, d, 25, oak)
        block("North", "North wall", 0, d, 0, w, t, h, wall)
        block("East", "East wall", w, 0, 0, t, d, h, wall)
        block("WestSouth", "West wall before door", -t, 0, 0, t, hinge, h, wall)
        block("WestNorth", "West wall beyond door", -t, hinge+leaf, 0, t, d-hinge-leaf, h, wall)
        head = top+door["head_reveal"]
        block("DoorHead", "Wall above the door", -t, hinge, head, t, leaf, h-head, wall)
        block("SouthWest", "South wall before window", 0, -t, 0, start, t, h, wall)
        block("SouthEast", "South wall beyond window", end, -t, 0, w-end, t, h, wall)
        block("WindowSill", "Wall below sill", start, -t, 0, end-start, t, window["sill"], wall)
        block("WindowHead", "Wall above window", start,-t,window["head"],end-start,t,h-window["head"],wall)
        block("OpenDoor", "Hall door at 90 degrees", 0,hinge,0,leaf,door["leaf_thickness"],top,oak)
        x,y,z,a,b,c = furniture["chair"]["box"]
        block("Chair", "L01 | retained reading chair envelope", x,y,z,a,b,c,sage)
        x,y,z,a,b,c = furniture["bookcase"]["box"]
        case = block("Bookcase", "Fixed bookcase envelope", x,y,z,a,b,c,wall)
        case.ViewObject.DisplayMode = "Wireframe"
        shelf = furniture["shelves"]
        for i in range(shelf["quantity"]):
            block("Shelf"+str(i+1), "L02 | oiled oak shelf "+str(i+1),
                  x+i*shelf["length"], y, shelf["shelf_top"]-22, shelf["length"], b, 22, oak)
        lamp = doc.addObject("Part::Cylinder", "Lamp")
        lamp.Label = "Retained lamp envelope"
        lamp.Radius, lamp.Height = furniture["lamp"]["radius"], furniture["lamp"]["height"]
        lamp.Placement.Base = App.Vector(*furniture["lamp"]["centre"], 0)
        # The quadrant includes the complete swing of the leaf's outer corner.
        sweep = doc.addObject("PartDesign::Feature", "DoorSwing")
        radius = (leaf**2+door["leaf_thickness"]**2)**0.5
        quadrant = Part.makeCylinder(radius, top, App.Vector(0,hinge,0),App.Vector(0,0,1),90)
        thickness = door["leaf_thickness"]
        hinge_side = Part.makeBox(thickness, radius, top, App.Vector(-thickness,hinge,0))
        sweep.Shape = quadrant.fuse(hinge_side)
        sweep.Label = "Conservative hall door swing"
        sweep.ViewObject.Visibility = False
        doc.recompute()
        doc.saveAs(str(target.resolve()))
    finally:
        App.closeDocument(doc.Name)
    doc = App.openDocument(str(target.resolve()), True)
    try:
        def clearance(first, second):
            return round(doc.getObject(first).Shape.distToShape(doc.getObject(second).Shape)[0], 3)
        result = {
            "design_revision": spec["revision"],
            "door_swing_to_chair_mm": clearance("DoorSwing", "Chair"),
            "door_swing_to_bookcase_mm": clearance("DoorSwing", "Bookcase"),
            "door_swing_to_lamp_mm": clearance("DoorSwing", "Lamp"),
            "leaf_to_head_mm": clearance("OpenDoor", "DoorHead"),
            "shelf_lengths_mm": [doc.getObject("Shelf"+str(i+1)).Length.Value for i in range(shelf["quantity"])]
        }
        if min(result[k] for k in result if k.endswith("_mm") and k!="shelf_lengths_mm") <= 0:
            raise ValueError("A modelled opening or furniture clearance failed")
        if result["shelf_lengths_mm"] != [875, 875] or result["leaf_to_head_mm"] != door["head_reveal"]:
            raise ValueError("The saved model differs from the selected shelves or door detail")
        def bounds(name):
            box = doc.getObject(name).Shape.BoundBox
            return [round(val, 3) for val in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)]

        result["bounds_mm"] = {name: bounds(name) for name in (
            "Floor", "OpenDoor", "DoorHead", "WindowSill", "WindowHead", "Chair", "Bookcase", "Lamp")}
        result["model_sha256"] = sha256(target.read_bytes()).hexdigest()
        head_shape = doc.getObject("DoorHead").Shape
        head_box = head_shape.BoundBox
        if (len(head_shape.Solids) != 1 or not head_shape.isValid()
                or abs(head_shape.Volume - head_box.XLength * head_box.YLength * head_box.ZLength) > 0.01):
            raise ValueError("The head must fill its opaque rectangular partition")
        report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        return result
    finally:
        App.closeDocument(doc.Name)
