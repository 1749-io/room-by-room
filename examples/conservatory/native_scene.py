"""Run build(root) in an empty Blender startup scene through Blender MCP."""
def build(root):
    import bpy, runpy, json, math
    from pathlib import Path
    from mathutils import Vector
    root=Path(root)
    scene=bpy.context.scene
    if set(obj.name for obj in scene.objects)-{"Camera","Cube","Light"}:
        raise RuntimeError("Use a fresh isolated Blender session")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    colours={"clay":(.40,.16,.08),"green":(.16,.24,.14),"oak":(.51,.32,.16),
             "lime":(.86,.80,.66),"umber":(.51,.23,.10),"cream":(.84,.82,.74),
             "grass":(.22,.32,.14),"foliage":(.115,.25,.08),"glass":(.88,.96,.98)}
    materials={}
    for name,rgb in colours.items():
        mat=bpy.data.materials.new(name)
        mat.diffuse_color=(*rgb,1)
        mat.use_nodes=True
        bs=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value=(*rgb,1)
        bs.inputs["Roughness"].default_value=.64
        if name=="glass":
            nodes=mat.node_tree.nodes
            mat.node_tree.links.new(nodes.new("ShaderNodeBsdfTransparent").outputs[0],
                                    next(n for n in nodes if n.type=="OUTPUT_MATERIAL").inputs[0])
        materials[name]=mat
    def box(name,mat,x,y,z,sx,sy,sz):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2))
        ob=bpy.context.object
        ob.name=name
        ob.dimensions=(sx,sy,sz)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        ob.data.materials.append(materials[mat])
        mod=ob.modifiers.new("Soft edges","BEVEL")
        mod.width=.009
        mod.segments=2
        return ob
    for args in runpy.run_path(str(root/"layout.py"))["pieces"]():
        box(*args)
    box("Orchard meadow","grass",0,0,-.25,90,90,.12)
    survey=json.loads((root/"survey.json").read_text(encoding="utf-8-sig"))
    for tree in survey["trees"]:
        x,y=tree["east"],tree["north"]
        box(tree["name"]+" trunk","oak",x,y,-.12,.24,.24,tree["base"]+1)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,location=(x,y,(tree["base"]+tree["top"])/2))
        ob=bpy.context.object
        ob.name=tree["name"]
        ob.scale=(tree["radius"],tree["radius"],(tree["top"]-tree["base"])/2)
        ob.data.materials.append(materials["foliage"])
    box("Closed reading book","green",4.60,3.25,.86,.29,.21,.04)
    # Pots are placed on the garden perimeter, clear of the north circulation route.
    from random import Random
    rng=Random(17)
    def plant(name,x,y,z,rise,radius,leaf_count):
        pot_height=radius*1.4
        bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=radius*.72,radius2=radius,
                                       depth=pot_height,location=(x,y,z+pot_height/2))
        pot=bpy.context.object
        pot.name=name+" terracotta pot"
        pot.data.materials.append(materials["clay"])
        for n in range(leaf_count):
            angle=n*2.4
            radial=radius*rng.uniform(.35,1.45)
            height=rise*rng.uniform(.35,.90)
            base=Vector((x,y,z+pot_height-.02))
            end=base+Vector((math.cos(angle)*radial,math.sin(angle)*radial,height))
            stem=box(name+" stem","green",0,0,0,.009,.009,(end-base).length)
            stem.location=(end+base)/2
            stem.rotation_euler=(end-base).to_track_quat("Z","Y").to_euler()
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,location=end)
            leaf=bpy.context.object
            leaf.name=name+" leaf"
            leaf.scale=(radius*.31,radius*.80,.025)
            leaf.rotation_euler=(.25,rng.uniform(-.5,.5),angle)
            leaf.data.materials.append(materials["foliage"])
    plant("Floor philodendron",.56,.51,0,1.15,.25,28)
    box("Plant stand","oak",1.55,.28,0,.48,.43,.72)
    plant("Trailing ivy",1.55,.28,.72,.26,.13,18)
    box("Fern stand","oak",2.10,.24,0,.34,.34,.62)
    plant("Window fern",2.10,.24,.62,.25,.14,18)
    glassmat=bpy.data.materials.new("Wine goblet glass")
    glassmat.use_nodes=True
    bs=next(n for n in glassmat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    bs.inputs["Transmission Weight"].default_value=1
    bs.inputs["Roughness"].default_value=.055
    bs.inputs["IOR"].default_value=1.46
    wine=bpy.data.materials.new("Red wine")
    wine.diffuse_color=(.24,.012,.034,1)
    wine.use_nodes=True
    wb=next(n for n in wine.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    wb.inputs["Base Color"].default_value=(.24,.009,.024,1)
    wb.inputs["Roughness"].default_value=.16
    def revolve(name,x,y,profile,mat):
        verts=[(x+r*math.cos(i*math.tau/40),y+r*math.sin(i*math.tau/40),.78+h)
               for r,h in profile for i in range(40)]
        faces=[(k*40+i,k*40+(i+1)%40,(k+1)*40+(i+1)%40,(k+1)*40+i)
               for k in range(len(profile)-1) for i in range(40)]
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(verts,[],faces)
        ob=bpy.data.objects.new(name,mesh)
        scene.collection.objects.link(ob)
        ob.data.materials.append(mat)
        for face in mesh.polygons: face.use_smooth=True
    for label,x,y in (("West",1.65,1.65),("East",2.72,1.28)):
        revolve(label+" wine glass",x,y,[(.001,.003),(.038,.003),(.034,.007),(.004,.011),
                (.004,.09),(.03,.10),(.045,.13),(.043,.159),(.035,.195),(.033,.195),
                (.041,.156),(.043,.13),(.028,.104),(.001,.095)],glassmat)
        revolve(label+" half pour",x,y,[(.001,.098),(.028,.106),(.041,.131),
                (.041,.143),(.001,.143)],wine)
    bpy.ops.object.camera_add(location=(4.90,3.13,1.54))
    cam=bpy.context.object
    cam.rotation_euler=(Vector((1.64,.64,1.14))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.lens=27
    scene.camera=cam
    scene.world.use_nodes=True
    bg=next(n for n in scene.world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs[0].default_value=(.80,.86,.95,1)
    bg.inputs[1].default_value=.85
    bpy.ops.object.light_add(type="SUN",location=(0,0,4))
    sun=bpy.context.object
    sun.rotation_euler=Vector((.46,.67,-.62)).to_track_quat("-Z","Y").to_euler()
    sun.data.energy=2.1
    sun.data.angle=math.radians(8)
    scene.render.engine="CYCLES"
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.resolution_x,scene.render.resolution_y=1050,700
    scene.render.resolution_percentage=100
    scene.render.filepath="//camera.png"
    scene.name="Orchard Fold OF-02"
    dest=root/"reference"/"Orchard-Fold.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(dest))
    assert bpy.context.scene.camera and bpy.data.objects["Sliding doorway head"].location.z>2.10
    bpy.ops.render.render(write_still=True)

