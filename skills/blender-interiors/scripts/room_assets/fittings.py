"""Fitting stand-ins: a pendant light, a roller blind and a glazed door leaf.

The pendant and blind hang above the floor. Their root still sits on the floor directly below, so every
asset is placed from a plan position. Each returns the extent it occupies in the root's axes.
"""

import bpy

from . import parts


def pendant(root, size, finishes, underside_mm, ceiling_mm, light_watts):
    """A drum pendant on a flex: shade, glowing diffuser and an optional point light just below."""
    width, depth, height = size
    if abs(width - depth) > 1e-6:
        raise ValueError("A round pendant needs the same width and depth")
    radius, underside, ceiling = width / 2, underside_mm / 1000, ceiling_mm / 1000
    if not 0 < underside < underside + height < ceiling:
        raise ValueError("The shade needs to hang between the floor and the ceiling")
    parts.cylinder(root, "shade", 0, 0, underside + 0.005, underside + height, radius, finishes["shade"])
    parts.cylinder(root, "diffuser", 0, 0, underside, underside + 0.02, radius * 0.875, finishes["diffuser"])
    parts.cylinder(root, "flex", 0, 0, underside + height, ceiling, 0.006, finishes["flex"], segments=8)
    if light_watts:
        lamp = bpy.data.lights.new(f"{root.name} | light", "POINT")
        lamp.energy = light_watts
        lamp.color = (1.0, 0.86, 0.68)
        holder = bpy.data.objects.new(f"{root.name} | light", lamp)
        root.users_collection[0].objects.link(holder)
        holder.parent = root
        holder.location = (0, 0, underside - 0.04)
    return [-radius, -radius, underside, radius, radius, ceiling]


def roller_blind(root, size, finishes, head_mm, drop_mm):
    """A roller blind: a cassette at the head of the opening and the fabric lowered by the stated drop."""
    width, depth, height = size
    head, drop = head_mm / 1000, drop_mm / 1000
    if not 0 <= drop <= head - height:
        raise ValueError("The fabric cannot drop below the floor")
    half_w, half_d = width / 2, depth / 2
    parts.box(root, "cassette", -half_w, -half_d, head - height, half_w, half_d, head, finishes["cassette"], bevel=0.006)
    if drop:
        parts.box(root, "fabric", -half_w + 0.015, -0.001, head - height - drop, half_w - 0.015, 0.001, head - height, finishes["fabric"])
    return [-half_w, -half_d, head - height - drop, half_w, half_d, head]


def glazed_leaf(root, size, finishes, stile_mm, bottom_rail_mm):
    """One glazed door leaf, hinged or sliding: two stiles, a top and bottom rail and a single clear pane."""
    width, depth, height = size
    half_w, half_d = width / 2, depth / 2
    stile, rail = stile_mm / 1000, bottom_rail_mm / 1000
    if not (2 * stile < width - 0.1 and stile + rail < height - 0.1 and depth > 0.012):
        raise ValueError("The stiles and rails leave no room for a pane")
    frame = finishes["frame"]
    parts.box(root, "stile 1", -half_w, -half_d, 0, -half_w + stile, half_d, height, frame)
    parts.box(root, "stile 2", half_w - stile, -half_d, 0, half_w, half_d, height, frame)
    parts.box(root, "top rail", -half_w + stile, -half_d, height - stile, half_w - stile, half_d, height, frame)
    parts.box(root, "bottom rail", -half_w + stile, -half_d, 0, half_w - stile, half_d, rail, frame)
    parts.box(root, "pane", -half_w + stile, -0.006, rail, half_w - stile, 0.006, height - stile, finishes["pane"])
