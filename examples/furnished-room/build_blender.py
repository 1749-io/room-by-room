"""Construct the original Alder library in an empty Blender scene. Inputs are in mm."""
import math

import bpy
import bmesh
from mathutils import Vector


def material(name, colour, roughness=0.65, grain=None, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1)
    mat.use_nodes = True
    tree = mat.node_tree
    shader = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if grain:
        coords = tree.nodes.new("ShaderNodeTexCoord")
        stretch = tree.nodes.new("ShaderNodeVectorMath")
        stretch.operation = "MULTIPLY"
        stretch.inputs[1].default_value = grain
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 1.8
        noise.inputs["Roughness"].default_value = 0.66
        tree.links.new(coords.outputs["Generated"], stretch.inputs[0])
        tree.links.new(stretch.outputs["Vector"], noise.inputs["Vector"])
        ramp = tree.nodes.new("ShaderNodeValToRGB")
        for stop, factor in zip(ramp.color_ramp.elements, (0.62, 1.22)):
            stop.color = (*[min(1, value * factor) for value in colour], 1)
        tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        tree.links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15
        bump.inputs["Distance"].default_value = 0.00045
        tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def build(spec):
    scene = bpy.context.scene
    if scene.objects or bpy.data.filepath:
        raise ValueError("Start in a separate, empty, unsaved Blender file")
    scene.name = "Alder library"
    scene.unit_settings.system = "METRIC"
    scene["design_revision"] = spec["revision"]
    shell, furnishings = spec["shell"], spec["furniture"]
    w, d, h, t = (shell[key] for key in ("width", "depth", "height", "wall"))
    collections = {}
    for name in ("Shell", "Chair", "Bookcase", "Lamp", "Room dressing", "Cameras and lighting"):
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        collections[name] = collection

    def piece(group, name, vertices, faces, mat, bevel=0):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v / 1000 for v in p) for p in vertices], [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collections[group].objects.link(obj)
        mesh.materials.append(mat)
        if bevel:
            edge = obj.modifiers.new("Rounded edges", "BEVEL")
            edge.width = bevel / 1000
            edge.segments = 5
            normal = obj.modifiers.new("Shading", "WEIGHTED_NORMAL")
            normal.keep_sharp = True
        return obj

    def block(group, name, x, y, z, a, b, c, mat, bevel=0, lean=0):
        if min(a, b, c) <= 0:
            raise ValueError("Invalid dimensions for " + name)
        base = [(x, y), (x + a, y), (x + a, y + b), (x, y + b)]
        vertices = [(u, v, z) for u, v in base] + [(u + lean, v, z + c) for u, v in base]
        faces = [(3, 2, 1, 0), (4, 5, 6, 7)] + [(i, (i+1)%4, (i+1)%4+4, i+4) for i in range(4)]
        return piece(group, name, vertices, faces, mat, bevel)

    def round_body(group, name, x, y, z, a, b, height, mat):
        n = 40
        vertices = []
        for radius, level in ((a, z), (b, z + height)):
            for i in range(n):
                angle = i * 2 * math.pi / n
                vertices.append((x + radius * math.cos(angle), y + radius * math.sin(angle), level))
        faces = [tuple(reversed(range(n))), tuple(range(n, n*2))]
        faces.extend((i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n))
        obj = piece(group, name, vertices, faces, mat)
        for poly in list(obj.data.polygons)[2:]:
            poly.use_smooth = True
        return obj

    oak = material("Oiled oak", (0.44, 0.254, 0.12), 0.43, (2, 14, 16))
    dark_oak = material("Oak end grain", (0.29, 0.156, 0.074), 0.48, (6, 7, 2))
    sage = material("Sage linen", (0.25, 0.345, 0.21), 0.94, (100, 90, 110))
    walls = material("AL-04 | chalk linen walls", (0.70, 0.64, 0.53), 0.92)
    trim = material("AL-01 | soft chalk joinery", (0.79, 0.76, 0.68), 0.59)
    case_paint = material("Retained painted bookcase", (0.41, 0.42, 0.35), 0.66)
    brass = material("Satin brass", (0.43, 0.28, 0.105), 0.32, metallic=0.72)
    paper = material("Warm paper", (0.77, 0.66, 0.48), 0.88)
    ceiling = material("Ceiling", (0.82, 0.80, 0.74))
    floor_colours = [(0.37, 0.225, 0.123), (0.34, 0.19, 0.095), (0.41, 0.256, 0.147)]
    boards = [material("Oak board " + str(i + 1), c, 0.53, (2, 15, 5)) for i, c in enumerate(floor_colours)]
    block("Shell", "Floor", 0, 0, -25, w, d, 24, dark_oak)
    for j in range(math.ceil(d / 150)):
        x, i = 0, 0
        while x < w:
            length = min(w-x, 1160 + ((j*379 + i*271) % 690))
            if length > 2:
                block("Shell", "Floorboard", x, j*150, -2, length-1.2, min(150, d-j*150)-1, 2, boards[(i+j)%3], 0.4)
            x += length
            i += 1
    block("Shell", "Ceiling", 0, 0, h, w, d, t, ceiling)
    block("Shell", "East wall", w, 0, 0, t, d, h, walls)
    block("Shell", "North wall", 0, d, 0, w, t, h, walls)
    door, window = shell["west_door"], shell["south_window"]
    hinge, leaf, top = door["hinge_y"], door["width"], door["height"]
    head = top + door["head_reveal"]
    block("Shell", "West before door", -t, 0, 0, t, hinge, h, walls)
    block("Shell", "West beyond door", -t, hinge+leaf, 0, t, d-hinge-leaf, h, walls)
    block("Shell", "DoorHead", -t, hinge, head, t, leaf, h-head, walls)
    block("Shell", "OpenDoor", 0, hinge, 0, leaf, door["leaf_thickness"], top, trim, 1)
    left, width, sill, upper = (window[key] for key in ("west_edge", "width", "sill", "head"))
    right = left + width
    block("Shell", "South west", 0, -t, 0, left, t, h, walls)
    block("Shell", "South east", right, -t, 0, w-right, t, h, walls)
    block("Shell", "WindowSill", left, -t, 0, width, t, sill, walls)
    block("Shell", "WindowHead", left, -t, upper, width, t, h-upper, walls)
    for x in (left, left+width/2-19, right-38):
        block("Shell", "Window frame", x, -74, sill+38, 38, 48, upper-sill-76, trim, 2)
    for level in (sill, upper-38):
        block("Shell", "Window rail", left, -74, level, width, 48, 38, trim, 2)
    glass = material("Clear window glass", (1, 1, 1), 0.02)
    glass_shader = next(node for node in glass.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    glass_shader.inputs["Transmission Weight"].default_value = 1
    glass_shader.inputs["IOR"].default_value = 1.45
    for pane_left, pane_right in ((left+38, left+width/2-19), (left+width/2+19, right-38)):
        block("Shell", "Window glass", pane_left, -55, sill+38, pane_right-pane_left, 4, upper-sill-76, glass)
    block("Shell", "Painted sill", left-22, -80, sill-23, width+44, 116, 23, trim, 3)
    block("Shell", "East skirting", w-13, 0, 0, 13, d, 87, trim, 2)
    block("Shell", "South skirting", 0, 0, 0, w, 13, 87, trim, 2)

    x, y, z, a, b, c = furnishings["chair"]["box"]
    seat = block("Chair", "L01 | seat cushion", x, y+55, z+320, a-125, b-110, 152, sage, 54)
    seat["shopping_ref"], seat["furnishing_room"] = "L01", "library"
    block("Chair", "L01 | inclined back cushion", x+a-188, y+48, z+423, 112, b-96, c-423, sage, 47, lean=76)
    for side in (y, y+b-47):
        block("Chair", "Oak arm", x+38, side, z+557, a-94, 47, 47, oak, 16)
        block("Chair", "Arm post", x+97, side+5, z+300, 35, 36, 257, dark_oak, 8)
        for dx, rake in ((39, 42), (a-66, -40)):
            block("Chair", "Oak foot", x+dx, side+3, z, 42, 41, 330, dark_oak, 6, lean=rake)
        block("Chair", "Side seat rail", x+64, side, z+282, a-130, 47, 58, oak, 9)
        block("Chair", "Oak back upright", x+a-137, side+4, z+320, 40, 39, c-355, oak, 9, lean=71)
    block("Chair", "Front seat rail", x+53, y+29, z+278, 49, b-58, 64, oak, 8)
    block("Chair", "Oak back rail", x+a-68, y+20, z+703, 68, b-40, 46, oak, 8)

    x, y, z, a, b, c = furnishings["bookcase"]["box"]
    shelf = furnishings["shelves"]
    block("Bookcase", "Back panel", x, y+b-14, z, a, 14, c, case_paint)
    for level in (0, 355, 704, 1047, c-24):
        block("Bookcase", "Existing painted shelf", x, y, z+level, a, b, 24, case_paint, 2)
    # The bought pair meet at the middle. The retained end posts stop at their underside.
    for xpos in (x, x+a/2-10, x+a-20):
        for base, end in ((z, shelf["shelf_top"]-22), (shelf["shelf_top"], z+c)):
            block("Bookcase", "Painted upright", xpos, y+5, base, 20, b-7, end-base, case_paint, 2)
    for i in range(shelf["quantity"]):
        board = block("Bookcase", "L02 | shelf " + str(i+1), x+i*shelf["length"], y,
                      shelf["shelf_top"]-22, shelf["length"], b, 22, oak, 2)
        board["shopping_ref"], board["furnishing_room"] = "L02", "library"
    jacket_colours = [(0.19, 0.23, 0.23), (0.44, 0.19, 0.11), (0.59, 0.49, 0.32),
                      (0.25, 0.32, 0.21), (0.64, 0.58, 0.46), (0.30, 0.20, 0.15)]
    jackets = [material("Cloth cover " + str(i+1), col, 0.87) for i, col in enumerate(jacket_colours)]
    for level, start, count in ((24, 62, 12), (24, 1055, 9), (379, 303, 9), (379, 976, 13),
                                (728, 36, 14), (1071, 347, 9), (1071, 1160, 8),
                                (shelf["shelf_top"], 86, 10), (shelf["shelf_top"], 1050, 7)):
        offset = start
        for i in range(count):
            bw = 21 + (17*i+start) % 27
            bh = 150 + (13*i+start) % 92
            mat = jackets[(i*5+start)%len(jackets)]
            block("Bookcase", "Clothbound volume", x+offset, y+23+i%4*7, level, bw, 148+i%6*8, bh, mat, 2)
            block("Bookcase", "Spine band", x+offset+3, y+22+i%4*7, level+bh*0.75, bw-6, 1, 2.5, paper)
            offset += bw+2

    lamp = furnishings["lamp"]
    lx, ly = lamp["centre"]
    radius, high = lamp["radius"], lamp["height"]
    round_body("Lamp", "Weighted base", lx, ly, 0, radius, radius-5, 29, brass)
    round_body("Lamp", "Lamp stem", lx, ly, 28, 10, 10, high-216, brass)
    round_body("Lamp", "Warm paper shade", lx, ly, high-190, radius, radius*0.66, 190, paper)

    # An original two-colour cut-paper print, built entirely from geometry.
    art_y, art_z = 1620, 1460
    block("Room dressing", "Oak picture frame", w-38, art_y-230, art_z-325, 37, 460, 650, oak, 4)
    block("Room dressing", "Paper mount", w-39, art_y-218, art_z-313, 2, 436, 626, trim)
    block("Room dressing", "Print field", w-40, art_y-155, art_z-216, 2, 310, 432, paper)
    for i, colour in enumerate((jackets[1], jackets[3])):
        coords = [(w-42-i, art_y+u, art_z+v) for u, v in
                  [(-155, -215), (155, -215), (155, 8-i*90), (54, 73-i*104), (-155, -18-i*112)]]
        piece("Room dressing", "Paper landscape", coords, [(4, 3, 2, 1, 0)], colour)

    def camera(name, location, target, lens):
        data = bpy.data.cameras.new(name)
        obj = bpy.data.objects.new(name, data)
        collections["Cameras and lighting"].objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()
        data.lens, data.clip_start = lens, 0.03
        return obj

    scene.camera = camera("View from the hall", (0.10, 1.62, 1.34), (2.50, 1.54, 1.12), 16)
    camera("West door and head", (3.51, 2.49, 1.38), (0.25, 0.87, 1.17), 25)
    world = bpy.data.worlds.new("Overcast daylight")
    scene.world = world
    world.use_nodes = True
    sky = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    sky.inputs["Color"].default_value = (0.84, 0.91, 1.0, 1)
    sky.inputs["Strength"].default_value = 1.7
    for name, pos, target, watts, size, colour in (
        ("South daylight", (2.15, -0.43, 2.04), (1.25, 2.45, 0.8), 160, 1.3, (1, 0.90, 0.78)),
        ("Hall bounce", (0.10, 1.62, 2.16), (2.30, 1.8, 1.0), 48, 1.5, (1, 0.94, 0.84))):
        light = bpy.data.lights.new(name, "AREA")
        obj = bpy.data.objects.new(name, light)
        collections["Cameras and lighting"].objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()
        light.energy, light.size, light.color = watts, size, colour
        obj.visible_camera = False
        obj.visible_glossy = False
        obj.visible_transmission = False
        light.specular_factor = 0
        light.transmission_factor = 0
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.view_settings.exposure = 0.85
    scene.render.resolution_x, scene.render.resolution_y = 1280, 832
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return scene


def measure(spec):
    """Read evaluated mesh vertices in world coordinates after reopening the saved scene."""
    scene = bpy.context.scene
    if scene.name != "Alder library" or scene["design_revision"] != spec["revision"]:
        raise ValueError("Open the saved Alder scene for this design revision")
    deps = bpy.context.evaluated_depsgraph_get()

    def bounds(objects):
        points = []
        for source in objects:
            obj = source.evaluated_get(deps)
            mesh = obj.to_mesh()
            try:
                points.extend(obj.matrix_world @ vertex.co for vertex in mesh.vertices)
            finally:
                obj.to_mesh_clear()
        low = [min(point[i] for point in points) for i in range(3)]
        high = [max(point[i] for point in points) for i in range(3)]
        return [round(value * 1000, 2) for value in low + high]

    actual = {name: bounds([scene.objects[name]]) for name in ("DoorHead", "OpenDoor", "WindowSill", "WindowHead")}
    head = scene.objects["DoorHead"].evaluated_get(deps)
    section = bmesh.new()
    try:
        section.from_mesh(head.data)
        section.transform(head.matrix_world)
        b = actual["DoorHead"]
        volume = (b[3]-b[0]) * (b[4]-b[1]) * (b[5]-b[2]) / 1e9
        if any(not e.is_manifold for e in section.edges) or abs(section.calc_volume(signed=True) - volume) > 0.000001:
            raise ValueError("The reopened head must be a solid rectangular partition")
    finally:
        section.free()
    for name in ("Chair", "Bookcase", "Lamp"):
        actual[name] = bounds(scene.collection.children[name].objects)
    products = {}
    for obj in scene.objects:
        ref = obj.get("shopping_ref")
        if ref:
            if obj.get("furnishing_room") != "library" or obj.hide_render:
                raise ValueError("Unassigned or hidden furnishing: " + obj.name)
            products.setdefault(ref, []).append({
                "object": obj.name, "material": obj.data.materials[0].name, "bounds_mm": bounds([obj])})
    furniture = spec["furniture"]
    shelves = furniture["shelves"]
    if set(products) != {"L01", "L02"} or len(products["L01"]) != 1 or len(products["L02"]) != shelves["quantity"]:
        raise ValueError("The furnished scene differs from the selected schedule quantities")
    if products["L01"][0]["material"] != "Sage linen" or any(row["material"] != "Oiled oak" for row in products["L02"]):
        raise ValueError("The retained upholstery or shelf finish differs from the selected variants")
    wood = {slot.material.name for obj in scene.collection.children["Chair"].objects for slot in obj.material_slots}
    if "Oiled oak" not in wood:
        raise ValueError("The retained chair requires its oak frame")
    for item in products["L02"]:
        x0, _, _, x1, _, top = item["bounds_mm"]
        if x1 - x0 != shelves["length"] or top != shelves["shelf_top"]:
            raise ValueError("The installed shelf differs in length or elevation")
    for name in ("Chair", "Bookcase"):
        x, y, z, a, b, c = furniture[name.lower()]["box"]
        expected = [x, y, z, x+a, y+b, z+c]
        if any(abs(v - ref) > 1 for v, ref in zip(actual[name], expected)):
            raise ValueError(name + " differs from its accepted CAD envelope: " + str(actual[name]))
    return {"design_revision": scene["design_revision"], "camera": scene.camera.name, "products": products,
            "bounds_mm": actual, "external_images": [img.name for img in bpy.data.images if img.filepath]}
