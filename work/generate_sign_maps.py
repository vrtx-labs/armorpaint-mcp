"""Author UV-aligned PBR sources from the original FBX surface positions.

Geometry and UVs stay unchanged. These source images become separate editable
material/fill layers in ArmorPaint, where the final texture set is composited.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

WORK = Path(__file__).parent
ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo/MOZU_Illuminated_Sign")
OUT = ROOT / "source_maps"
OUT.mkdir(parents=True, exist_ok=True)
N = 4096
rng = np.random.default_rng(78219)
mesh = np.load(WORK / "mesh_surfaces.npz")
position = np.zeros((N, N, 3), np.float32)
kind = np.zeros((N, N), np.uint8)
print("Rasterizing original UVs", flush=True)
for points, uv, normal in zip(mesh["position"], mesh["uv"], mesh["normal"]):
    xy = uv.copy() * N
    xy[:, 1] = N - xy[:, 1]
    x0, y0 = np.maximum(np.floor(xy.min(axis=0)).astype(int), 0)
    x1, y1 = np.minimum(np.ceil(xy.max(axis=0)).astype(int), N - 1)
    if x1 < x0 or y1 < y0:
        continue
    a, b, c = xy
    det = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
    if abs(det) < 1e-8:
        continue
    yy, xx = np.mgrid[y0:y1+1, x0:x1+1].astype(np.float32)
    xx += 0.5
    yy += 0.5
    w0 = ((b[1]-c[1])*(xx-c[0]) + (c[0]-b[0])*(yy-c[1])) / det
    w1 = ((c[1]-a[1])*(xx-c[0]) + (a[0]-c[0])*(yy-c[1])) / det
    w2 = 1 - w0 - w1
    inside = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
    patch = position[y0:y1+1, x0:x1+1]
    for axis in range(3):
        value = w0 * points[0,axis] + w1 * points[1,axis] + w2 * points[2,axis]
        patch[..., axis][inside] = value[inside]
    # Recessed panel is 10 mm behind the frontmost metal lip.
    surface = 1
    if normal[1] < -0.99:
        surface = 2 if points[:, 1].mean() > 0.005 else 3
    kind[y0:y1+1, x0:x1+1][inside] = surface

valid = kind > 0
panel = kind == 2
rim = kind == 3
print("Surface pixels:", {str(i): int(np.sum(kind == i)) for i in range(4)}, flush=True)
Image.fromarray((kind * 70).astype(np.uint8)).resize((1024,1024)).save(WORK / "surface-classification.png")

# Six-texel gutter expansion prevents dark seams under mipmapping.
_, indices = ndi.distance_transform_edt(~valid, return_indices=True)
padding = ndi.binary_dilation(valid, iterations=6)
def padded(a):
    result = a.copy()
    gutter = padding & ~valid
    result[gutter] = a[indices[0][gutter], indices[1][gutter]]
    return result

def save(name, data, alpha=None):
    a = np.asarray(data)
    if a.ndim == 0:
        a = np.full((N, N), a, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, axis=2)
    if alpha is not None:
        a = np.concatenate([a, alpha[..., None]], axis=2)
    a = padded(a)
    Image.fromarray(np.uint8(np.clip(a * 255, 0, 255))).save(OUT / f"{name}.png")

# World-space noise stays continuous across the UV island seams.
coords = position.transpose(2, 0, 1)
minimum = mesh["position"].min(axis=(0,1)).astype(np.float32)
maximum = mesh["position"].max(axis=(0,1)).astype(np.float32)
def noise(scale, seed):
    local_rng = np.random.default_rng(seed)
    dims = np.ceil((maximum - minimum) * scale).astype(int) + 4
    grid = local_rng.random(tuple(dims), dtype=np.float32)
    sample = (coords - minimum[:,None,None]) * scale + 1
    return ndi.map_coordinates(grid, sample, order=1, mode="nearest", prefilter=False)

print("Authoring steel and oxidation", flush=True)
coarse = noise(5, 11)
medium = noise(24, 12)
fine = noise(110, 13)
micro = rng.random((N,N), dtype=np.float32)
spangle = noise(60, 18)
steel = np.empty((N,N,3), np.float32)
tone = 0.77 + 0.22*medium + 0.10*(spangle > 0.55) + 0.05*(fine - 0.5)
for c, value in enumerate([0.42,0.455,0.46]):
    steel[...,c] = tone * value
# Pale zinc-plated front lip, slightly warm from accumulated dust.
for c, value in enumerate([0.74,0.735,0.67]):
    steel[...,c][rim] = value * (0.86 + 0.15*medium[rim])

# Long fine fabrication marks and random fine scratches in world space.
z = position[...,2]
x = position[...,0]
marks = (np.sin(z*1700 + np.sin(x*4)*2) > 0.96) * (medium > 0.45)
steel += marks[...,None] * 0.032
steel += (micro[...,None] - 0.5) * 0.025
save("steel_base", steel)
rough_steel = np.clip(0.49 + (medium-0.5)*0.22 + (fine-0.5)*0.15,0.32,0.7)
rough_steel[rim] -= 0.08
save("steel_roughness", rough_steel)
save("steel_metallic", 0.88)

# Granular rust islands, near-edge bloom, pitting, and vertical rain trails.
rust_field = coarse*0.37 + medium*0.40 + fine*0.23
rust = np.clip((rust_field-0.57)*9,0,1)
rim_rust = np.clip((medium*0.55 + fine*0.45-0.65)*10,0,0.95)
rust[rim] = rim_rust[rim]
streak = noise(8, 43) * 0.55 + noise(45, 47)*0.45
drip = np.clip((np.sin(x*107 + np.sin(x*23)*5)*0.5+0.5-0.89)*5,0,1)
drip *= np.clip((streak-0.52)*5,0,0.5)
rust = np.maximum(rust, drip)
rust[panel | ~valid] = 0
rust_color = np.empty_like(steel)
for c, (dark, light) in enumerate([(0.12,0.39),(0.065,0.19),(0.028,0.065)]):
    rust_color[...,c] = dark + (0.25+0.75*fine)*(light-dark)
save("oxidation_base", rust_color, rust)
save("oxidation_roughness", np.clip(0.79+fine*0.17,0,1))

# Keep a deliberate narrow dark gasket around the red acrylic inset.
distance = ndi.distance_transform_edt(panel)
gasket = np.clip((3.5-distance)/2.5,0,1)*panel
grime = np.clip((coarse*0.5 + medium*0.5-0.62)*4,0,0.28)
red = np.empty_like(steel)
frost = 0.91 + (medium-0.5)*0.14 + (fine-0.5)*0.07
for c, value in enumerate([0.76,0.065,0.026]):
    red[...,c] = value * frost
red *= (1-grime[...,None]*0.65)
red = red*(1-gasket[...,None]*0.92)
# Delicate sun-faded flecks and scratches. Do not turn the sign into a noisy rust slab.
flecks = (fine > 0.66) * (micro > 0.76) * 0.25
red += flecks[...,None] * np.array([0.17,0.075,0.045],np.float32)
save("red_diffuser_base", red, panel.astype(np.float32))
save("red_diffuser_roughness", np.clip(0.30+fine*0.11+grime*0.3,0,1))
save("inset_mask", panel.astype(np.float32))
save("emission_color_source", red * panel[...,None])

# Restrained tangent-space micro-pitting. Avoid a dramatic fake bevel at UV seams.
relief = ndi.gaussian_filter((micro-0.5)*0.4 + (fine-0.5)*0.45,0.6)
dy, dx = np.gradient(relief)
normal = np.empty_like(steel)
normal[...,0] = 0.5 - dx*0.8
normal[...,1] = 0.5 + dy*0.8
normal[...,2] = np.sqrt(np.maximum(0,1-(dx*1.6)**2-(dy*1.6)**2))*0.5+0.5
save("steel_normal", normal)
normal[...,0] = 0.5-dx*0.18
normal[...,1] = 0.5+dy*0.18
normal[...,2] = 1
save("red_diffuser_normal", normal)

# A flat atlas proof helps audit alignment independently of a shaded viewport.
composite = steel*(1-rust[...,None]) + rust_color*rust[...,None]
composite[panel] = red[panel]
save("atlas_base_proof", composite)
Image.open(OUT / "atlas_base_proof.png").resize((1024,1024)).save(WORK / "atlas-proof.png")
metadata = {"resolution":N,"source":"../logo_3d.fbx","seed":78219,
            "surface_definition":"Normals toward -Y, recessed plane Y=0.01 m is emissive. Front lip Y=0 m, body/back remain metal.",
            "layers":["Galvanized steel body and pale zinc lip","Oxidation, pitting and rain streaks","Red illuminated inset diffuser"]}
(ROOT / "map-generation.json").write_text(json.dumps(metadata,indent=2))
print("Wrote PBR source maps:", OUT, flush=True)
