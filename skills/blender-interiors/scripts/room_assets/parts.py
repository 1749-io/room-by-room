"""Shared geometry for the room stand-ins. Runs inside Blender. Lengths are metres in the root's own axes."""

import math

import bmesh
import bpy

# Finish key: material name, sRGB colour, roughness, then optional metallic, emission strength and alpha.
PALETTE = {
    "oak": ("Oak", "#B8905F", 0.45),
    "linen": ("Seat pad | linen", "#D9CFBF", 0.9),
    "oatmeal": ("Linen | oatmeal", "#DDD3C0", 0.95),
    "rust": ("Upholstery | rust", "#B5532F", 0.85),
    "rattan": ("Rattan | natural honey", "#C99A5B", 0.45),
    "cane": ("Rattan | cane weave", "#D9B278", 0.55),
    "brass": ("Brass", "#B08D57", 0.3, 1.0),
    "black": ("Black", "#1B1B1B", 0.4),
    "white": ("White paint", "#F3F1EC", 0.5),
    "frame": ("Window frame | white", "#F5F5F2", 0.4),
    "glass": ("Glass", "#DCEBEF", 0.05, 0.0, 0.0, 0.18),
    "lamp": ("Lamp glow", "#FFE2B0", 0.5, 0.0, 3.0),
    "hedge": ("Garden | hedge", "#3F6B3A", 0.95),
    "leaf": ("Garden | tree canopy", "#4C7A40", 0.95),
    "bark": ("Garden | bark", "#5A4636", 0.9),
}


def linear(colour):
    """Convert #RRGGBB to the linear values Blender stores."""
    text = colour.lstrip("#")
    channels = [int(text[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]


def material(finish):
    """Return the material for a palette key or for the name of a material already in the file.

    A material that already exists under the palette's name is reused unchanged, so a finish the
    room has adjusted stays as reviewed.
    """
    if finish not in PALETTE:
        found = bpy.data.materials.get(finish)
        if found is None:
            raise ValueError(f"{finish!r} is neither a palette finish nor a material in this file")
        return found
    name, colour, roughness, *rest = PALETTE[finish]
    metallic, emission, alpha = (list(rest) + [0.0, 0.0, 1.0][len(rest):])
    found = bpy.data.materials.get(name)
    if found is not None:
        return found
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    shader = next(node for node in made.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    rgb = linear(colour)
    shader.inputs["Base Color"].default_value = (*rgb, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        glow = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        glow.default_value = (*rgb, 1.0)
        shader.inputs["Emission Strength"].default_value = emission
    if alpha < 1:
        shader.inputs["Alpha"].default_value = alpha
        if hasattr(made, "surface_render_method"):
            made.surface_render_method = "BLENDED"
    made.diffuse_color = (*rgb, alpha)
    return made


def collection(name):
    """Return the named collection, creating it under the scene when it is new."""
    found = bpy.data.collections.get(name)
    if found is None:
        found = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(found)
    return found


def new_root(name, collection_name):
    """Create the empty that carries the asset's name, tags and placement."""
    if name in bpy.data.objects:
        raise ValueError(f"An object named {name!r} already exists. Give each instance its own name")
    root = bpy.data.objects.new(name, None)
    root.empty_display_size = 0.2
    collection(collection_name).objects.link(root)
    return root


def _attach(root, part, mesh, finish, smooth=False):
    mesh.materials.append(material(finish))
    if smooth:
        for face in mesh.polygons:
            face.use_smooth = True
    obj = bpy.data.objects.new(f"{root.name} | {part}", mesh)
    root.users_collection[0].objects.link(obj)
    obj.parent = root
    return obj


def _soften(obj, width, segments=3):
    edge = obj.modifiers.new("Soft edge", "BEVEL")
    edge.width = width
    edge.segments = segments
    edge.limit_method = "ANGLE"
    edge.angle_limit = math.radians(50)
    for face in obj.data.polygons:
        face.use_smooth = True


def box(root, part, x0, y0, z0, x1, y1, z1, finish, bevel=0.0):
    """An axis-aligned block. The bevel rounds its edges inwards and keeps the stated size."""
    corners = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
               (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = bpy.data.meshes.new(f"{root.name} | {part}")
    mesh.from_pydata(corners, [], faces)
    mesh.update()
    obj = _attach(root, part, mesh, finish)
    if bevel:
        _soften(obj, bevel)
    return obj


def cylinder(root, part, x, y, z0, z1, radius, finish, segments=32):
    """An upright cylinder. Use a multiple of four segments so its plan size is exact."""
    ring = [(x + radius * math.cos(2 * math.pi * i / segments), y + radius * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]
    points = [(px, py, z0) for px, py in ring] + [(px, py, z1) for px, py in ring]
    faces = [tuple(range(segments - 1, -1, -1)), tuple(range(segments, 2 * segments))]
    faces += [(i, (i + 1) % segments, segments + (i + 1) % segments, segments + i) for i in range(segments)]
    mesh = bpy.data.meshes.new(f"{root.name} | {part}")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    for face in mesh.polygons[2:]:
        face.use_smooth = True
    return _attach(root, part, mesh, finish)


def slab(root, part, outline, z0, z1, finish, bevel=0.0):
    """A plan outline, anticlockwise from above, extruded between two heights. Used for cushions."""
    count = len(outline)
    points = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
    faces += [(i, (i + 1) % count, count + (i + 1) % count, count + i) for i in range(count)]
    mesh = bpy.data.meshes.new(f"{root.name} | {part}")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = _attach(root, part, mesh, finish)
    if bevel:
        _soften(obj, bevel, segments=5)
    return obj


def ellipsoid(root, part, centre, radii, finish):
    """A rounded mass whose extreme points lie exactly on its three axes."""
    build = bmesh.new()
    bmesh.ops.create_uvsphere(build, u_segments=16, v_segments=8, radius=1.0)
    for vertex in build.verts:
        vertex.co = [centre[i] + radii[i] * vertex.co[i] for i in range(3)]
    mesh = bpy.data.meshes.new(f"{root.name} | {part}")
    build.to_mesh(mesh)
    build.free()
    return _attach(root, part, mesh, finish, smooth=True)


def tubes(root, part, lines, radius, finish, resolution=3):
    """One mesh from several round rods. Each line is (points, closed)."""
    curve = bpy.data.curves.new(f"{root.name} | {part} centre lines", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    curve.use_fill_caps = True
    for points, closed in lines:
        spline = curve.splines.new("POLY")
        spline.points.add(len(points) - 1)
        spline.use_cyclic_u = closed
        for point, position in zip(spline.points, points):
            point.co = (*position, 1.0)
    holder = bpy.data.objects.new(curve.name, curve)
    root.users_collection[0].objects.link(holder)
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    mesh = bpy.data.meshes.new_from_object(holder.evaluated_get(graph))
    mesh.name = f"{root.name} | {part}"
    bpy.data.objects.remove(holder, do_unlink=True)
    bpy.data.curves.remove(curve)
    return _attach(root, part, mesh, finish, smooth=True)


def rod_to_floor(top, foot, radius):
    """Centre line for a raked leg whose angled end cap just touches the floor at the foot."""
    length = math.dist(top, foot)
    upright = abs(top[2] - foot[2]) / length
    return [tuple(top), (foot[0], foot[1], foot[2] + radius * math.sqrt(max(0.0, 1 - upright ** 2)))]


def bounds(root, world=False):
    """Evaluated mesh extent as [x0, y0, z0, x1, y1, z1] in metres, in the root's own axes or the scene's."""
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    to_root = root.matrix_world.inverted()
    low, high = [math.inf] * 3, [-math.inf] * 3
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        shown = obj.evaluated_get(graph)
        mesh = shown.to_mesh()
        placed = shown.matrix_world if world else to_root @ shown.matrix_world
        for vertex in mesh.vertices:
            point = placed @ vertex.co
            for axis in range(3):
                low[axis] = min(low[axis], point[axis])
                high[axis] = max(high[axis], point[axis])
        shown.to_mesh_clear()
    if math.inf in low:
        raise ValueError(f"{root.name} has no mesh parts to measure")
    return low + high
