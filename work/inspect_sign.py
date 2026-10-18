import bpy
import json
from pathlib import Path

source = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/logo_3d.fbx")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(source))
report = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    coords = [list(obj.matrix_world @ v.co) for v in mesh.vertices]
    bins = {}
    for face in mesh.polygons:
        key = str(tuple(round(c, 2) for c in face.normal))
        bins[key] = bins.get(key, 0) + 1
    report.append({
        "name": obj.name, "vertices": len(mesh.vertices), "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles), "materials": [m.name if m else None for m in mesh.materials],
        "uv_layers": [uv.name for uv in mesh.uv_layers],
        "bbox_min": [min(v[a] for v in coords) for a in range(3)],
        "bbox_max": [max(v[a] for v in coords) for a in range(3)],
        "normals": bins,
    })
print(json.dumps(report, indent=2))
Path("D:/Projects/armorpaint-mcp/work/mesh_report.json").write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath="D:/Projects/armorpaint-mcp/work/source_inspection.blend")
