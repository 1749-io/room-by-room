"""Run in live Blender after reopening the saved, fully dressed room."""
import bpy
from mathutils import Vector
from mathutils.geometry import convex_hull_2d


def occupied_footprints(collection, excluded, metres_per_unit):
    """Project evaluated object bounds, including instances, into world-plan mm.

    excluded maps original object names to reviewed reasons (floor, high-level
    lighting, etc.). Limit the collection to the complete room and its contents.
    """
    if metres_per_unit <= 0 or any(not reason.strip() for reason in excluded.values()):
        raise ValueError("Supply the model scale and a reason for each exclusion")
    members = set(collection.all_objects)
    outlines = {}
    scene_objects = []
    exemptions = {}
    for instance in bpy.context.evaluated_depsgraph_get().object_instances:
        obj = instance.object
        owner = instance.parent if instance.is_instance else obj
        if owner.original not in members:
            continue
        if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME", "POINTCLOUD", "CURVES"}:
            continue
        key = obj.original.name
        if instance.is_instance:
            key += f"@{owner.original.name}:{tuple(instance.persistent_id)}"
        if key in scene_objects:
            raise ValueError(f"Duplicate walkthrough object: {key}")
        scene_objects.append(key)
        if obj.original.name in excluded:
            exemptions[key] = excluded[obj.original.name]
            continue
        corners = [instance.matrix_world @ Vector(corner) for corner in obj.bound_box]
        points = [Vector((p.x, p.y)) * (1000 * metres_per_unit) for p in corners]
        outlines[key] = [list(points[i]) for i in convex_hull_2d(points)]
    return {"scene_objects": scene_objects, "obstacles": outlines, "exclusions": exemptions}
