"""Run with Blender in background mode, with a new scratch scene and saved user preferences."""
import csv
import math
from pathlib import Path

import bpy
from mathutils import Vector


def check():
    if bpy.data.filepath:
        raise ValueError("Use a fresh background Blender process without a project file.")
    if not any(a.module.rsplit(".", 1)[-1] == "sun_position" for a in bpy.context.preferences.addons):
        raise RuntimeError("Enable Sun Position in Blender and save preferences first.")
    scene = bpy.context.scene
    sun = bpy.data.objects.new("Test sun", bpy.data.lights.new("Test sun", "SUN"))
    scene.collection.objects.link(sun)
    props = scene.sun_pos_properties
    props.sun_object = sun
    props.latitude, props.longitude = 52, -1.5
    props.UTC_zone, props.use_daylight_savings = 0, True
    props.year, props.month, props.day, props.time = 2026, 9, 21, 17
    bpy.context.view_layer.update()
    angles = math.degrees(props["azimuth"]) % 360, math.degrees(props["elevation"])
    vector = sun.rotation_euler.to_matrix() @ Vector((0, 0, 1))
    aim = math.degrees(math.atan2(vector.x, vector.y)) % 360, math.degrees(math.asin(vector.z))
    samples = Path(__file__).resolve().parents[1] / "garden-sun" / "samples.csv"
    with samples.open(newline="", encoding="utf-8") as stream:
        row, = (r for r in csv.DictReader(stream) if r["local_time"] == "2026-09-21T17:00:00+01:00")
    reference = float(row["azimuth_deg"]), float(row["apparent_elevation_deg"])
    for angle, light, expected in zip(angles, aim, reference):
        if abs(angle - expected) > 0.2 or abs(angle - light) > 0.1:
            raise ValueError(f"Sun Position {angle}, lamp direction {light}, reference {expected}")
    print(f"Sun Position passed: bearing {aim[0]:.3f}, elevation {aim[1]:.3f} degrees.")


if __name__ == "__main__":
    check()
