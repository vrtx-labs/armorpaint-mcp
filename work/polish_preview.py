import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/MOZU_Illuminated_Sign")
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "MOZU_Weathered_Illuminated.blend"))
scene = bpy.context.scene
mat = bpy.data.materials["MOZU - Weathered Illuminated Sign"]
shader = mat.node_tree.nodes.get("Principled BSDF")
for image in bpy.data.images:
    if image.name.startswith("MOZU_Sign_EmissionRGB"):
        image.unpack(method="REMOVE")
        image.filepath = str(ROOT / "textures/MOZU_Sign_EmissionRGB.png")
        image.reload()
        image.pack()
shader.inputs["Emission Strength"].default_value = 2.0
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = -0.3
for light in bpy.data.lights:
    light.energy *= 0.6
glare = next(n for n in scene.node_tree.nodes if n.bl_idname == "CompositorNodeGlare")
glare.mix = -0.65
scene.render.filepath = str(ROOT / "previews/MOZU_Lit_Hero.png")
bpy.ops.render.render(write_still=True)

# Re-export only the original meshes, with the finalized emissive material.
bpy.ops.object.select_all(action="DESELECT")
for obj in scene.objects:
    if obj.name.startswith("Logo_"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT / "MOZU_Weathered_Illuminated.glb"),export_format="GLB",use_selection=True,
                          export_apply=False,export_yup=True)
scene.render.filepath = str(ROOT / "previews/MOZU_Lit_Hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "MOZU_Weathered_Illuminated.blend"))

# Darker presentation makes it easy to judge the illumination separately from metal highlights.
for light in bpy.data.lights:
    light.energy *= 0.12
glare.mix = -0.3
scene.view_settings.exposure = -0.1
scene.render.filepath = str(ROOT / "previews/MOZU_Night.png")
bpy.ops.render.render(write_still=True)

# Back view of the same material and original geometry.
scene.objects["PREVIEW - wall"].hide_render = True
scene.camera.location = (2.4,15.5,3.5)
scene.camera.rotation_euler = (Vector((0.02,0.15,0.95))-scene.camera.location).to_track_quat("-Z","Y").to_euler()
light_data = bpy.data.lights.new("Back inspection softbox","AREA")
light_data.energy = 1500
light_data.size = 6
light = bpy.data.objects.new("Back inspection softbox",light_data)
scene.collection.objects.link(light)
light.location = (0,5,6)
light.rotation_euler = (Vector((0,0,1))-light.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath = str(ROOT / "previews/MOZU_Back.png")
bpy.ops.render.render(write_still=True)
print("Finalized red illumination, night preview, and back inspection.")
