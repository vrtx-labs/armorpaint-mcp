import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/MOZU_Illuminated_Sign")
TEX = ROOT / "textures"
base = np.asarray(Image.open(TEX / "MOZU_Sign_BaseColor.png").convert("RGB"))
mask = np.asarray(Image.open(TEX / "MOZU_Sign_EmissionMask.png").convert("L"))
inset = np.asarray(Image.open(ROOT / "source_maps/inset_mask.png").convert("L")) > 127
assert base.shape == (4096,4096,3)
assert np.mean(mask[inset] > 200) > 0.98
outside = ~ndi.binary_dilation(inset, iterations=4)
assert np.mean(mask[outside] > 200) < 0.0001
emission = (base.astype(np.float32) * (mask.astype(np.float32)/255)[...,None]).astype(np.uint8)
emission[~inset] = 0
Image.fromarray(emission).save(TEX / "MOZU_Sign_EmissionRGB.png")
rough = np.asarray(Image.open(TEX / "MOZU_Sign_Roughness.png").convert("L"))
metal = np.asarray(Image.open(TEX / "MOZU_Sign_Metallic.png").convert("L"))
ao = np.asarray(Image.open(TEX / "MOZU_Sign_Occlusion.png").convert("L"))
Image.fromarray(np.stack([ao,rough,metal],axis=-1)).save(TEX / "MOZU_Sign_ORM.png")
normal = np.array(Image.open(TEX / "MOZU_Sign_NormalGL.png").convert("RGB"))
normal[...,1] = 255-normal[...,1]
Image.fromarray(normal).save(TEX / "MOZU_Sign_NormalDX.png")
report = {
    "resolution":[4096,4096], "emission_coverage_on_inset":float(np.mean(mask[inset]>200)),
    "emission_leakage_outside_inset_with_4px_tolerance":float(np.mean(mask[outside]>200)),
    "final_emission_rgb_pixels_outside_inset":int(np.count_nonzero(emission[~inset])),
    "textures":{p.name:{"bytes":p.stat().st_size,"size":Image.open(p).size} for p in TEX.glob("*.png")},
}
(ROOT / "verification.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
