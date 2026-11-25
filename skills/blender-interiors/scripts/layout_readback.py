"""Read measured centres and functional facing from evaluated meshes through Blender MCP."""

from math import atan2, degrees

import bpy
from mathutils import Vector


def mesh_centre(name, depsgraph):
    obj = bpy.context.scene.objects[name].evaluated_get(depsgraph)
    if obj.type != "MESH" or not len(obj.data.vertices):
        raise ValueError(f"{name} needs a measurable mesh in the active scene")
    local = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
    return obj.matrix_world @ local


def read_facing(seat, back, target):
    """Use separate seat, back and target meshes in the same scene. Return world metres."""
    graph = bpy.context.evaluated_depsgraph_get()
    centre, rear, aim = (mesh_centre(name, graph) for name in (seat, back, target))
    forward = (centre - rear).to_2d()
    sight = (aim - centre).to_2d()
    if min(forward.length, sight.length) < 1e-8:
        raise ValueError("The seat, back and target need distinct horizontal reference points")
    metres = bpy.context.scene.unit_settings.scale_length
    return {
        "seat": seat, "back": back, "target": target,
        "centre_m": list(centre * metres), "target_m": list(aim * metres),
        "front_yaw_deg": degrees(atan2(forward.y, forward.x)),
        "turn_deg": abs(degrees(atan2(forward.cross(sight), forward.dot(sight)))),
    }
