"""Build every catalogue asset in Blender and read its size back.

    blender --background --factory-startup --python check_room_assets.py -- report.json [--views DIRECTORY]

Each asset is built at its default, smallest and largest sizes, turned on the floor and measured again, and
built twice to confirm the geometry repeats. A one-off builder goes through `build_custom`, and a faulty one must be refused. `--views` also saves one picture per asset for a visual review.
"""

import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import room_assets  # noqa: E402


def fingerprint(root):
    """Digest of every part's evaluated vertices in the root's axes, to 0.001 mm. Take it before the asset is turned."""
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    to_root = root.matrix_world.inverted()
    digest = hashlib.sha256()
    for obj in sorted(root.children_recursive, key=lambda item: item.name.split(" | ", 1)[-1]):
        if obj.type != "MESH":
            continue
        shown = obj.evaluated_get(graph)
        mesh = shown.to_mesh()
        placed = to_root @ shown.matrix_world
        digest.update(obj.name.split(" | ", 1)[-1].encode())
        for vertex in mesh.vertices:
            digest.update(("%d,%d,%d;" % tuple(round(v * 1e6) for v in placed @ vertex.co)).encode())
        shown.to_mesh_clear()
    return digest.hexdigest()


def check(kind, entry):
    cases = []
    for label in ("default", "min", "max"):
        root = room_assets.build(kind, f"{kind} {label}", size_mm=entry["size"][label])
        flat = room_assets.measure(root)
        mark = fingerprint(root)
        room_assets.place(root, (3.0, -2.0), yaw_deg=30.0)
        turned = room_assets.measure(root)
        cases.append({"case": label, **flat, "worst_difference_when_turned_mm": turned["worst_difference_mm"],
                      "passes": flat["within_tolerance"] and turned["within_tolerance"], "fingerprint": mark})
        room_assets.remove(root)
    again = room_assets.build(kind, f"{kind} repeat")
    repeats = fingerprint(again) == cases[0]["fingerprint"]
    room_assets.remove(again)
    return {"cases": cases, "repeats": repeats, "passes": repeats and all(case["passes"] for case in cases)}


def bench(root, size, finishes, slats):
    """A one-off builder of the kind a house writes for itself: a slatted bench on two plank ends."""
    width, depth, height = size
    gap = 0.012
    slat = (depth - gap * (slats - 1)) / slats
    for index in range(slats):
        y = -depth / 2 + index * (slat + gap)
        room_assets.parts.box(root, f"slat {index + 1}", -width / 2, y, height - 0.03, width / 2, y + slat, height, finishes["timber"], bevel=0.003)
    for index, x in enumerate((-width / 2 + 0.08, width / 2 - 0.12)):
        room_assets.parts.box(root, f"end {index + 1}", x, -depth / 2, 0, x + 0.04, depth / 2, height - 0.03, finishes["timber"])


def oversize(root, size, finishes):
    """A faulty one-off builder: 20 mm wider than it was asked to be."""
    width, depth, height = size
    room_assets.parts.box(root, "block", -width / 2 - 0.02, -depth / 2, 0, width / 2, depth / 2, height, "oak")


def check_custom():
    root = room_assets.build_custom(bench, "one-off bench", (1200, 380, 450), finishes={"timber": "oak"},
                                    tags={"furnishing_room": "hall", "shopping_ref": "H01"}, slats=4)
    result = {**room_assets.measure(root), "tags_kept": root["shopping_ref"] == "H01", "options": root["asset_options"]}
    room_assets.remove(root)
    try:
        room_assets.build_custom(oversize, "one-off oversize", (600, 400, 400))
        result["oversize_refused"] = False
    except RuntimeError as error:
        result["oversize_refused"] = "20.0 mm away" in str(error)
    result["passes"] = result["within_tolerance"] and result["tags_kept"] and result["oversize_refused"]
    return result


def picture(kind, folder):
    """One three-quarter view of the default asset on a plain ground."""
    scene = bpy.context.scene
    root = room_assets.build(kind, f"{kind} view")
    x0, y0, z0, x1, y1, z1 = room_assets.measure(root)["world_bounds_m"]
    centre = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    reach = max(x1 - x0, y1 - y0, z1 - z0)
    camera = bpy.data.objects.new("view", bpy.data.cameras.new("view"))
    scene.collection.objects.link(camera)
    camera.data.lens = 50
    camera.data.clip_end = 1000
    camera.location = centre + Vector((0.95, 1.5, 0.75)).normalized() * reach * 2.6
    camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = str(folder / f"{kind}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    room_assets.remove(root)


def studio():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(140))
    scene.collection.objects.link(sun)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.88, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.render.resolution_x, scene.render.resolution_y = 640, 640
    scene.render.film_transparent = False


def main(arguments):
    target = Path(arguments[0]).resolve()
    views = Path(arguments[arguments.index("--views") + 1]).resolve() if "--views" in arguments else None
    studio()
    report = {"blender": bpy.app.version_string, "tolerance_mm": room_assets.TOLERANCE_MM,
              "assets": {kind: check(kind, entry) for kind, entry in room_assets.ASSETS.items()}}
    report["custom"] = check_custom()
    report["passes"] = report["custom"]["passes"] and all(result["passes"] for result in report["assets"].values())
    report["objects_left_behind"] = sorted(obj.name for obj in bpy.data.objects if obj.name != "sun")
    target.write_text(json.dumps(report, indent=1), encoding="utf-8")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        for kind in room_assets.ASSETS:
            picture(kind, views)
    print("Room assets:", "all sizes read back within tolerance" if report["passes"] else "FAILED, see " + str(target))
    return report["passes"]


if __name__ == "__main__":
    passed = main(sys.argv[sys.argv.index("--") + 1:])
    sys.exit(0 if passed else 1)
