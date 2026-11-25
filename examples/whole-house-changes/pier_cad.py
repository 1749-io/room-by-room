"""Run through live FreeCAD MCP. Uses a new, fictional document only."""
import json
from pathlib import Path

import FreeCAD as App


def build_example(folder):
    """Create a shareable teaching fixture, reopen it and export native bounds in mm."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    model = folder / "Example rear rooms.FCStd"
    evidence = folder / "rear-rooms.json"
    if model.exists() or evidence.exists():
        raise ValueError("Use a new output folder for the example")
    previous = App.ActiveDocument.Name if App.ActiveDocument else None
    doc = App.newDocument("ExampleRearRooms")
    doc.Label = "Fictional rear rooms | pier and occupied dining"

    def box(group, name, x0, y0, x1, y1, height, colour, base=0):
        obj = doc.addObject("Part::Box", group.Name + name)
        obj.Label = name
        obj.Length, obj.Width, obj.Height = x1 - x0, y1 - y0, height
        obj.Placement.Base = App.Vector(x0, y0, base)
        obj.ViewObject.ShapeColor = colour
        group.addObject(obj)
        return obj

    states = (("R0", False, 3000, 0), ("R1", True, 3000, 0),
              ("R1a", True, 2700, 0), ("R2", True, 2700, 180), ("R3", True, 2700, 180))
    for revision, pier, cabinet_end, move_table in states:
        group = doc.addObject("App::DocumentObjectGroup", revision)
        box(group, "Floor", 0, -700, 7410, 5000, 100, (0.89, 0.87, 0.82), -100)
        bench_shift = -300 if revision == "R3" else 0
        box(group, "SouthRun", 0, 700 + bench_shift, 3000, 2200 + bench_shift,
            900, (0.46, 0.60, 0.55))
        box(group, "EndRun", 0, 2600, cabinet_end, 3200, 900, (0.46, 0.60, 0.55))
        box(group, "Return", 3950, 2650, 7410, 2900, 2400, (0.72, 0.68, 0.64))
        if pier:
            box(group, "Pier", 3650, 2650, 3950, 2900, 2400, (0.77, 0.38, 0.25))
        for capacity, length, spacing in (("Four", 1500, (320, 1180)),
                                          ("Eight", 2100, (320, 1050, 1780))):
            dining = doc.addObject("App::DocumentObjectGroup", revision + capacity)
            group.addObject(dining)
            x = 3980 + move_table
            box(dining, "Table", x, 1100, x + length, 1950, 750, (0.72, 0.53, 0.38))
            for number, offset in enumerate(spacing, 1):
                for side, y0, y1 in (("S", 740, 1100), ("N", 1950, 2310)):
                    box(dining, side + str(number), x + offset - 210, y0,
                        x + offset + 210, y1, 850, (0.41, 0.52, 0.64))
            if capacity == "Eight":
                for name, left in (("W", x - 310), ("E", x + length)):
                    box(dining, name, left, 1320, left + 310, 1740, 850, (0.41, 0.52, 0.64))
            dining.ViewObject.Visibility = capacity == "Eight"
        group.ViewObject.Visibility = revision == "R3"
        if revision == "R3":
            doc.getObject("R3Four").ViewObject.Visibility = False
    doc.recompute()
    doc.saveAs(str(model))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(model))
    try:
        def bounds(obj):
            if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
                raise ValueError("Invalid fixture solid " + obj.Name)
            b = obj.Shape.BoundBox
            return [round(v, 3) for v in (b.XMin, b.YMin, b.XMax, b.YMax)]

        exported = {}
        for revision, *_ in states:
            items = {}
            for obj in reopened.getObject(revision).Group:
                if obj.TypeId == "App::DocumentObjectGroup":
                    items[obj.Name[len(revision):]] = {
                        part.Name[len(obj.Name):]: bounds(part) for part in obj.Group
                    }
                else:
                    items[obj.Name[len(revision):]] = bounds(obj)
            exported[revision] = items
        evidence.write_text(json.dumps(exported, indent=2) + "\n", encoding="utf-8")
    finally:
        App.closeDocument(reopened.Name)
        if previous and previous in App.listDocuments():
            App.setActiveDocument(previous)
    return {revision: len(parts["Eight"]) - 1 for revision, parts in exported.items()}
