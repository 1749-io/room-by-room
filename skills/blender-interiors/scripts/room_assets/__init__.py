"""Deterministic stand-ins for furnishing a Blender scene at stated sizes.

Each asset is built from code alone: the same request always gives the same geometry, and nothing is
imported or downloaded. `catalogue.json` beside this file lists every asset with its sizes, options and
finishes. Add this file's parent directory to `sys.path` inside Blender, then:

    import room_assets
    chair = room_assets.build("rattan_armchair", "C01 armchair 1", size_mm=(740, 790, 820),
                              collection="Furniture | conservatory",
                              tags={"furnishing_room": "conservatory", "shopping_ref": "C01"})
    room_assets.place(chair, centre_m=(0.55, 9.40), yaw_deg=-12)
    report = room_assets.measure(chair)

Sizes are millimetres: width along the asset's X, depth along its Y, then height. The scene is metres.
For a piece the catalogue lacks, write a builder like the ones here and pass it to `build_custom`.
"""

import importlib
import json
import math
from pathlib import Path

CATALOGUE = json.loads(Path(__file__).with_name("catalogue.json").read_text(encoding="utf-8"))
ASSETS = CATALOGUE["assets"]
TOLERANCE_MM = CATALOGUE["tolerance_mm"]
RESERVED = ("asset", "asset_size_mm", "asset_extent_mm", "asset_options", "asset_finishes")


def resolve(kind, size_mm=None, finishes=None, options=None):
    """Check a request against the catalogue and fill in its defaults. Needs no Blender."""
    if kind not in ASSETS:
        raise ValueError(f"No asset named {kind!r}. The catalogue has: {', '.join(sorted(ASSETS))}")
    entry = ASSETS[kind]
    limits = entry["size"]
    size = [float(v) for v in (limits["default"] if size_mm is None else size_mm)]
    if len(size) != 3:
        raise ValueError(f"{kind} needs three sizes in millimetres: {entry['size_means']}")
    for value, low, high, axis in zip(size, limits["min"], limits["max"], ("first", "second", "third")):
        if not low <= value <= high:
            raise ValueError(f"{kind}: the {axis} size, {value:g} mm, is outside {low} to {high} mm ({entry['size_means']})")
    unknown = sorted(set(options or {}) - set(entry["options"]))
    if unknown:
        raise ValueError(f"{kind} has no option {', '.join(unknown)}. It accepts: {', '.join(entry['options']) or 'none'}")
    unknown = sorted(set(finishes or {}) - set(entry["finishes"]))
    if unknown:
        raise ValueError(f"{kind} has no finish for {', '.join(unknown)}. It accepts: {', '.join(entry['finishes'])}")
    return size, {**entry["finishes"], **(finishes or {})}, {**entry["options"], **(options or {})}


def build(kind, name, size_mm=None, collection="Furniture", finishes=None, tags=None, **options):
    """Build one catalogue asset at the origin and return its root empty.

    The root carries the tags, for example `furnishing_room` and `shopping_ref`, and the request that made
    it. A finish is a palette key from `parts.PALETTE` or the name of a material already in the file. The
    built size is read back before returning, and an asset outside the tolerance is removed and reported.
    """
    size, chosen, settings = resolve(kind, size_mm, finishes, options)
    builder = getattr(importlib.import_module(f".{ASSETS[kind]['module']}", __name__), kind)
    return _assemble(kind, builder, name, size, collection, chosen, tags, settings)


def build_custom(builder, name, size_mm, collection="Furniture", finishes=None, tags=None, **options):
    """Build a one-off piece from a builder written for one house, with the same record and read-back.

    The builder has the same form as a catalogue builder: it receives the root, the size in metres, the
    finishes and its options, adds parts with the helpers in `parts`, and returns the occupied extent only
    when that differs from a box centred on the root. There are no catalogue limits or default finishes.
    """
    if not callable(builder):
        raise ValueError("Pass the builder function itself, written like the ones in this library")
    size = [float(v) for v in size_mm]
    if len(size) != 3 or min(size) <= 0:
        raise ValueError("A one-off piece needs three positive sizes in millimetres: width, depth and height")
    return _assemble(f"custom:{builder.__name__}", builder, name, size, collection, dict(finishes or {}), tags, options)


def _assemble(kind, builder, name, size, collection, chosen, tags, settings):
    import bpy
    from . import parts

    clash = sorted(set(tags or {}) & set(RESERVED))
    if clash:
        raise ValueError(f"These tag names are kept for the asset record: {', '.join(clash)}")
    if abs(bpy.context.scene.unit_settings.scale_length - 1.0) > 1e-9:
        raise ValueError("Set the scene's unit scale to 1.0 so that one Blender unit is one metre")
    root = parts.new_root(name, collection)
    try:
        width, depth, height = (v / 1000 for v in size)
        extent = builder(root, (width, depth, height), chosen, **settings)
        extent = extent or [-width / 2, -depth / 2, 0.0, width / 2, depth / 2, height]
        root["asset"] = kind
        root["asset_size_mm"] = size
        root["asset_extent_mm"] = [round(v * 1000, 3) for v in extent]
        root["asset_options"] = json.dumps(settings, sort_keys=True)
        root["asset_finishes"] = json.dumps(chosen, sort_keys=True)
        for key, value in (tags or {}).items():
            root[key] = value
        report = measure(root)
        if not report["within_tolerance"]:
            raise RuntimeError(f"{kind} was built {report['worst_difference_mm']} mm away from the requested size: {report}")
    except Exception:
        remove(root)
        raise
    return root


def place(root, centre_m, yaw_deg=0.0, floor_m=0.0):
    """Put the asset's origin at a plan position. Yaw turns the front anticlockwise from +Y, seen from above."""
    root.location = (centre_m[0], centre_m[1], floor_m)
    root.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    return root


def measure(root, tolerance_mm=TOLERANCE_MM):
    """Read the built asset back from its evaluated meshes and compare it with the request."""
    from . import parts

    if "asset" not in root:
        raise ValueError(f"{root.name} was not built by this library")
    wanted = list(root["asset_extent_mm"])
    found = [v * 1000 for v in parts.bounds(root)]
    worst = max(abs(a - b) for a, b in zip(wanted, found))
    return {
        "name": root.name,
        "asset": root["asset"],
        "requested_size_mm": list(root["asset_size_mm"]),
        "measured_size_mm": [round(found[i + 3] - found[i], 2) for i in range(3)],
        "requested_extent_mm": wanted,
        "measured_extent_mm": [round(v, 2) for v in found],
        "worst_difference_mm": round(worst, 2),
        "within_tolerance": worst <= tolerance_mm,
        "yaw_deg": round(math.degrees(root.matrix_world.to_euler().z), 3),
        "world_bounds_m": [round(v, 4) for v in parts.bounds(root, world=True)],
    }


def remove(root):
    """Delete an asset: its root, its parts and the mesh or light data only they used."""
    import bpy

    for obj in list(root.children_recursive) + [root]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.batch_remove([data])
