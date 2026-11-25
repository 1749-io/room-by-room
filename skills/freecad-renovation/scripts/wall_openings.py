"""Build an editable straight wall in a live FreeCAD document and inspect its actual sections.

Lengths are millimetres. Origin is the start of the wall on its near face at floor level.
Openings are (offset from start, clear width, sill above floor, clear height).
"""

from math import isfinite
import re

import FreeCAD as App
import Part


def build_wall(doc, name, origin, yaw, length, thickness, height, openings=()):
    """Add one standalone wall. The caller selects the option document and saves it."""
    openings = list(openings)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise ValueError("Use a stable FreeCAD object name for the wall")
    if len(origin) != 3 or not all(isfinite(v) for v in (*origin, yaw, length, thickness, height)):
        raise ValueError("Supply finite wall dimensions, origin and yaw")
    if min(length, thickness, height) <= 0:
        raise ValueError("Wall dimensions must be positive")
    for offset, width, sill, rise in openings:
        if (not all(isfinite(v) for v in (offset, width, sill, rise))
                or min(offset, sill) < 0 or min(width, rise) <= 0
                or offset + width > length or sill + rise > height):
            raise ValueError("Opening lies outside the wall or has invalid dimensions")
    names = [f"{name}Blank"] if openings else []
    names += [f"{name}Opening{i}" for i in range(1, len(openings) + 1)]
    names += [f"{name}Cut{i}" for i in range(1, len(openings))]
    if any(doc.getObject(key) is not None for key in [name, *names]):
        raise ValueError(f"Wall object name already in use: {name}. Inspect the existing feature.")
    frame = App.Placement(App.Vector(*origin), App.Rotation(App.Vector(0, 0, 1), yaw))
    doc.openTransaction(f"Build {name}")
    try:
        wall = doc.addObject("Part::Box", names[0] if openings else name)
        wall.Length, wall.Width, wall.Height = length, thickness, height
        wall.Placement = frame
        for i, (offset, width, sill, rise) in enumerate(openings, 1):
            tool = doc.addObject("Part::Box", f"{name}Opening{i}")
            tool.Length, tool.Width, tool.Height = width, thickness + 2, rise
            tool.Placement = frame.multiply(App.Placement(App.Vector(offset, -1, sill), App.Rotation()))
            cut = doc.addObject("Part::Cut", name if i == len(openings) else f"{name}Cut{i}")
            cut.Base, cut.Tool = wall, tool
            wall.ViewObject.Visibility = tool.ViewObject.Visibility = False
            wall = cut
        doc.recompute()
        if wall.Shape.isNull() or not wall.Shape.isValid() or wall.Shape.Volume <= 0:
            raise ValueError(f"Invalid wall solid: {name}")
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    return wall


def solid_spans(wall, origin, yaw, length, thickness, level):
    """Measure solid intervals along the wall at a given height in the reopened model.

    Supply the expected reference frame from the brief. Use heights inside each band,
    away from coincident faces at sills and heads. Works on a standalone wall feature.
    """
    frame = App.Placement(App.Vector(*origin), App.Rotation(App.Vector(0, 0, 1), yaw))
    start = frame.multVec(App.Vector(-1, thickness / 2, level))
    end = frame.multVec(App.Vector(length + 1, thickness / 2, level))
    section = wall.Shape.common(Part.makeLine(start, end))
    inverse = frame.inverse()
    return sorted(sorted(inverse.multVec(v.Point).x for v in edge.Vertexes) for edge in section.Edges)
