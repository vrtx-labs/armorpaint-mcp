import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/MOZU_Illuminated_Sign")
raw = (ROOT / "MOZU_Weathered_Illuminated.glb").read_bytes()
magic, version, size = struct.unpack_from("<4sII",raw)
assert magic == b"glTF" and version == 2 and size == len(raw)
json_size, chunk_type = struct.unpack_from("<II",raw,12)
gltf = json.loads(raw[20:20+json_size])
assert len(gltf["meshes"]) == 5
triangles = sum(gltf["accessors"][p["indices"]]["count"]//3 for m in gltf["meshes"] for p in m["primitives"])
original = len(np.load(Path(__file__).with_name("mesh_surfaces.npz"))["position"])
assert triangles == original, (triangles, original)
material = gltf["materials"][0]
assert "emissiveTexture" in material and "normalTexture" in material
assert material["extensions"]["KHR_materials_emissive_strength"]["emissiveStrength"] == 2.0
assert "metallicRoughnessTexture" in material["pbrMetallicRoughness"]
for image in gltf["images"]:
    assert "bufferView" in image
project = ROOT / "MOZU_Weathered_Illuminated.arm"
assert project.stat().st_size > 10_000_000
assert (ROOT / "MOZU_Weathered_Illuminated.blend").stat().st_size > 10_000_000
for name in ["MOZU_Lit_Hero.png","MOZU_Night.png","MOZU_Back.png"]:
    image = Image.open(ROOT / "previews" / name)
    assert image.size == (2400,1100)
report = {"glb_meshes":5,"triangles_original":original,"triangles_delivered":triangles,
          "embedded_images":len(gltf["images"]),"emission_strength":2.0,
          "project_bytes":project.stat().st_size,
          "glb_bytes":len(raw),"status":"passed"}
(ROOT / "artifact-verification.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
