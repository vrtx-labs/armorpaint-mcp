import bpy
import json
from collections import Counter
from pathlib import Path
import numpy as np

bpy.ops.wm.open_mainfile(filepath="D:/Projects/armorpaint-mcp/work/source_inspection.blend")
triangles, uvs, normals, names = [], [], [], []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    depth = Counter()
    for face in mesh.polygons:
        if face.normal.y < -0.99:
            depth[round(sum(mesh.vertices[i].co.y for i in face.vertices) / len(face.vertices), 5)] += 1
    print(obj.name, "front planes:", dict(depth), "dimensions:", list(obj.dimensions))
    for t in mesh.loop_triangles:
        triangles.append([list(obj.matrix_world @ mesh.vertices[i].co) for i in t.vertices])
        uvs.append([list(mesh.uv_layers.active.data[i].uv) for i in t.loops])
        normals.append(list(t.normal))
        names.append(obj.name)
np.savez_compressed("D:/Projects/armorpaint-mcp/work/mesh_surfaces.npz", position=np.array(triangles), uv=np.array(uvs), normal=np.array(normals), name=np.array(names))
