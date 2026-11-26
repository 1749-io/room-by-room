"""Draw the two fictional readers and check their journey in the reopened CAD layout."""
import json
from pathlib import Path

import fitz
from shapely.geometry import LineString, box


def build(folder):
    folder = Path(folder)
    boxes = json.loads((folder / "Layout checks.json").read_text(encoding="utf-8"))["bounds_mm"]

    def footprint(name):
        x, y, _, right, back, _ = boxes[name]
        return box(x, y, right, back)

    chair, case = footprint("Chair"), footprint("Bookcase")
    # Allow 400 mm for the seated reader's knees and feet, projecting west.
    left, near, right, far = chair.bounds
    occupied = box(left - 400, near, right, far)
    approach = LineString([(0, 820), (1380, 820), (1510, 1640), (1510, 2400)])
    width = 550
    passage = approach.buffer(width / 2, cap_style=2)
    browser = box(1235, 2140, 1785, 2660)
    walls = box(*footprint("Floor").bounds)
    if not walls.covers(passage) or not walls.covers(browser):
        raise ValueError("The reader's route leaves the room")
    for shape in (occupied, case, footprint("Lamp"), footprint("OpenDoor")):
        if passage.intersects(shape) or browser.intersects(shape):
            raise ValueError("The bookcase visit conflicts with the parked door, furniture or seated reader")
    if occupied.intersects(case) or browser.distance(case) > 100:
        raise ValueError("Check the occupied chair and the reader's reach to the bookcase")

    with fitz.open() as doc:
        page = doc.new_page(width=720, height=440)
        ink, sage, grey, tan = (0.15, 0.21, 0.18), (0.65, 0.75, 0.57), (0.85, 0.86, 0.81), (0.84, 0.71, 0.53)
        def point(x, y):
            return (40 + x / 10, 370 - y / 10)

        def area(shape, fill, dashed=False):
            x0, y0, x1, y1 = shape.bounds
            r = fitz.Rect(point(x0, y1), point(x1, y0))
            page.draw_rect(r, color=ink, fill=fill, width=0.8, dashes="[3 2] 0" if dashed else None)

        def label(x, y, value, size=10):
            page.insert_text((x, y), value, fontsize=size, color=ink)

        label(40, 32, "Library | reading and reaching the shelves", 19)
        label(40, 50, "Alder Cottage    /    occupied layout    /    north at the top")
        area(walls, (1, 1, 1))
        path = page.new_shape()
        path.draw_polyline([point(x, y) for x, y in passage.exterior.coords])
        path.finish(color=None, fill=(0.90, 0.94, 0.92))
        path.commit()
        page.draw_line(point(0, 360), point(0, 1260), color=(1, 1, 1), width=2)
        area(footprint("OpenDoor"), tan)
        area(occupied, None, True)
        area(chair, sage)
        area(case, grey)
        area(browser, None, True)
        area(footprint("Lamp"), tan)
        page.draw_polyline([point(x, y) for x, y in approach.coords], color=ink, dashes="[3 2] 0", width=1)
        start, _, _, end, _, _ = boxes["WindowSill"]
        page.draw_line(point(start, 0), point(end, 0), color=(0.25, 0.50, 0.62), width=3)
        label(145, 88, "Fixed bookcase")
        label(167, 134, "Standing")
        label(171, 148, "reader")
        label(311, 285, "Chair")
        label(43, 352, "Parked door")
        label(211, 391, "South window")
        label(455, 89, "Drawing key", 14)
        label(455, 121, "Green fill      Retained reading chair")
        label(455, 146, "Grey fill         Existing bookcase")
        label(455, 171, "Ochre fill       Door leaf and floor lamp")
        label(455, 196, "Dashed box   Occupied space")
        label(455, 221, "Pale band     550 mm route for a second reader")
        label(455, 246, "Dashed line   Hall door to bookcase")
        label(455, 271, "Blue line       South window")
        label(455, 310, "Chair faces west. The dashed extension")
        label(455, 326, "allows 400 mm beyond the front edge.")
        label(455, 353, "Door parked before the reader enters.")
        page.draw_line((40, 398), (140, 398), color=ink, width=1)
        label(40, 415, "0")
        label(125, 415, "1 m")
        doc.save(folder / "Occupied library.pdf", garbage=4, deflate=True, no_new_id=True)
    return {"route_width_mm": width, "route_to_occupied_chair_mm": round(passage.distance(occupied), 1),
            "standing_reader_to_shelf_mm": browser.distance(case)}
