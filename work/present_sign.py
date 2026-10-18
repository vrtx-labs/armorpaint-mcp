"""Link the ArmorPaint exports to the untouched FBX meshes and render a preview."""
import bpy
from pathlib import Path
from mathutils import Vector
import math

ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/MOZU_Illuminated_Sign")
TEX = ROOT / "textures"
PREVIEW = ROOT / "previews"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT.parent / "logo_3d.fbx"))
sign = [o for o in bpy.context.scene.objects if o.type == "MESH"]
mat = bpy.data.materials.new("MOZU - Weathered Illuminated Sign")
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
shader = nodes.get("Principled BSDF")
shader.location = (400,100)

def image(name, location, data=False):
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(TEX / f"MOZU_Sign_{name}.png"),check_existing=True)
    tex.label = name
    tex.location = location
    if data:
        tex.image.colorspace_settings.name = "Non-Color"
    return tex

base = image("BaseColor",(-500,500))
links.new(base.outputs["Color"],shader.inputs["Base Color"])
rough = image("Roughness",(-500,200),True)
links.new(rough.outputs["Color"],shader.inputs["Roughness"])
metal = image("Metallic",(-500,-100),True)
links.new(metal.outputs["Color"],shader.inputs["Metallic"])
normal = image("NormalGL",(-500,-400),True)
normal_map = nodes.new("ShaderNodeNormalMap")
normal_map.location = (100,-300)
links.new(normal.outputs["Color"],normal_map.inputs["Color"])
links.new(normal_map.outputs["Normal"],shader.inputs["Normal"])
emission = image("EmissionRGB",(-500,-700))
links.new(emission.outputs["Color"],shader.inputs["Emission Color"])
shader.inputs["Emission Strength"].default_value = 4.0
for obj in sign:
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# Deliver an original-geometry GLB with the shared PBR material and emissive strength.
bpy.ops.object.select_all(action="DESELECT")
for obj in sign:
    obj.select_set(True)
bpy.context.view_layer.objects.active = sign[0]
bpy.ops.export_scene.gltf(filepath=str(ROOT / "MOZU_Weathered_Illuminated.glb"),export_format="GLB",use_selection=True,
                          export_apply=False,export_yup=True)

# A non-destructive render-only bevel catches light on the metal housing edges.
for obj in sign:
    bevel = obj.modifiers.new("Preview edge highlights (render only)","BEVEL")
    bevel.width = 0.0015
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bevel.show_viewport = False

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for dev in prefs.devices:
        dev.use = dev.type != "CPU"
    if any(dev.use for dev in prefs.devices):
        scene.cycles.device = "GPU"
except Exception:
    pass
scene.render.resolution_x = 2400
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("Preview world")
scene.world.color = (0.035,0.035,0.035)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.4

def simple_material(name,color,roughness):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color,1)
    bsdf.inputs["Roughness"].default_value = roughness
    return m

backdrop = simple_material("Preview backdrop - charcoal concrete",(0.025,0.034,0.043),0.82)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-0.07))
floor = bpy.context.object
floor.name = "PREVIEW - floor"
floor.data.materials.append(backdrop)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,1.4,0),rotation=(math.pi/2,0,0))
wall = bpy.context.object
wall.name = "PREVIEW - wall"
wall.data.materials.append(backdrop)

def aim(obj,target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()

def area(name,location,power,size,color):
    data = bpy.data.lights.new(name,"AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location = location
    aim(obj,(0,0,1))
    return obj

area("PREVIEW - cool softbox",(-3,-4,6),1200,5,(0.72,0.84,1.0))
area("PREVIEW - warm edge",(5,-1,5),900,3,(1.0,0.78,0.55))
area("PREVIEW - left rim",(-6,0.7,3),650,3,(0.60,0.74,1.0))
bpy.ops.object.camera_add(location=(2.2,-15.5,3.5))
camera = bpy.context.object
camera.name = "PREVIEW - camera"
camera.data.lens = 47
aim(camera,(0.02,0.15,0.95))
scene.camera = camera
scene.use_nodes = True
cnodes, clinks = scene.node_tree.nodes, scene.node_tree.links
cnodes.clear()
render = cnodes.new("CompositorNodeRLayers")
glare = cnodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 0.7
glare.size = 8
glare.mix = -0.85
composite = cnodes.new("CompositorNodeComposite")
clinks.new(render.outputs["Image"],glare.inputs["Image"])
clinks.new(glare.outputs["Image"],composite.inputs["Image"])

# Pack the exported image maps into the linked Blender scene.
bpy.ops.file.pack_all()
scene.render.filepath = str(PREVIEW / "MOZU_Lit_Hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "MOZU_Weathered_Illuminated.blend"))
bpy.ops.render.render(write_still=True)
print("Delivered linked GLB, Blender scene, and lit preview.")
