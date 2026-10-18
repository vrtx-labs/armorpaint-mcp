"""Portable, deterministic Machinery material and MG-style mask reconstruction.

The algorithms are independent approximations, not a Substance bytecode runtime.
Colors and recipe settings were inspected in the local Painter 1.7.3 preset.
All numerical maps and computations use linear values; only base color is sRGB.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


MASK_DEFAULTS = {
    'Level': .5, 'Contrast': .5, 'Invert': 0, 'Use_Triplanar': 1,
    'Triplanar_Blending_Contrast': .5, 'Grunge': .3, 'Grunge_Scale': 3,
    'Grunge_Use_Custom_Grunge': 0, 'Grunge_Secondary_Custom_Grunge': 0., 'Grunge_Invert': 0,
    'AO': 1., 'AO_Range': .75, 'AO_Contrast': 0., 'AO_Noisiness': .75,
    'AO_Noise_Scale': 4, 'AO_Noise_Type': 1, 'AO_Invert': 0,
    'Curvature': 1., 'Curvature_Convex_Range': .5, 'Curvature_Convex_Contrast': 0.,
    'Curvature_Convex_Invert': 0, 'Curvature_Concave_Range': .6,
    'Curvature_Concave_Contrast': 0., 'Curvature_Concave_Invert': 0,
    'Curvature_Smoothness': 0., 'Curvature_Level_Boost': .25,
    'Curvature_Noisiness': .77, 'Curvature_Noise_Scale': 1, 'Curvature_Noise_Type': 4,
    'Top_Down_Gradient': 0., 'Gradient_Range': .5, 'Gradient_Contrast': .5, 'Gradient_Invert': 0,
    'World_Space_Normal': 0., 'World_Space_Normal_Top_Intensity': 0.,
    'World_Space_Normal_Bottom_Intensity': 0., 'World_Space_Normal_Front_Intensity': 0.,
    'World_Space_Normal_Back_Intensity': 0., 'World_Space_Normal_Right_Intensity': 0.,
    'World_Space_Normal_Left_Intensity': 0., 'Scratches': 0.,
    'Scratches_Amount': 2000, 'Scratches_Scale': .5, 'Scatter': 0., 'Scatter_Scale': 20,
    'Scatter_Density': 1., 'Scatter_Size': 1., 'Scatter_Size_Variation': .5,
    'Scatter_Opacity_Variation': 0., '$randomseed': 0,
}
RECIPE = {
    'name': 'Machinery', 'source_version': 'Substance Painter 1.7.3',
    'implementation': 'independent approximation; not pixel-identical to Substance',
    'paint': {**MASK_DEFAULTS, 'Level': .46, 'Contrast': .9, 'Invert': 1,
        'Triplanar_Blending_Contrast': .75, 'Grunge': .6, 'Grunge_Scale': 5,
        'AO': .9, 'AO_Range': .8, 'AO_Contrast': .5, 'AO_Noisiness': .7, 'AO_Noise_Scale': 1,
        'Curvature': .97, 'Curvature_Concave_Range': 0., 'Curvature_Smoothness': 1.2,
        'Curvature_Noisiness': 1., 'Curvature_Noise_Scale': 2,
        'World_Space_Normal_Bottom_Intensity': .65},
    'dirty': {**MASK_DEFAULTS, 'Level': .8, 'Contrast': .3, 'Triplanar_Blending_Contrast': .21},
    'dust': {**MASK_DEFAULTS, 'Level': .5, 'Contrast': .6, 'Grunge': .17, 'Grunge_Scale': 2,
        'AO': -.4, 'AO_Range': .91, 'AO_Noisiness': .5, 'AO_Noise_Scale': 2,
        'Curvature_Convex_Range': -.45, 'Curvature_Concave_Range': .48,
        'Curvature_Smoothness': 1.45, 'Curvature_Noisiness': .25, 'Curvature_Noise_Scale': 2,
        'World_Space_Normal_Top_Intensity': .95},
    'steel': {'metal_color': [.23129255, .14127760, .10384564], 'metal_roughness': .46153846,
        'noisiness': .15, 'surface_imperfections': .1, 'dirt': .61, 'dirt_contrast': .1,
        'dirt_scale': 1., 'rust': 1., 'normal_intensity': .5, 'seed': 0},
    'clean_color': [.92669368, .42770475, 0.], 'clean_roughness': .06635071,
    'clean_height': .03071678, 'dirty_color': [.72488660, .33490601, .00063695],
    'dirty_roughness': .35545024, 'dust_color': [.07038786, .05718586, .04586986],
    'dust_roughness': 1., 'dust_enabled': False, 'dirty_opacity': .8, 'dust_opacity': .71,
}


def recipe(overrides=None):
    result = copy.deepcopy(RECIPE)
    for key, value in (overrides or {}).items():
        if key not in result:
            raise ValueError(f'Unknown recipe setting {key}')
        if isinstance(result[key], dict):
            if not isinstance(value, dict) or set(value) - set(result[key]):
                raise ValueError(f'Unknown or invalid {key} parameters')
            result[key].update(value)
        else:
            result[key] = value
    return result


def srgb(value):
    v = np.clip(value, 0, 1)
    return np.where(v <= .0031308, 12.92 * v, 1.055 * v ** (1/2.4) - .055)


def resize(array, size):
    if array.shape[:2] == (size, size):
        return array.astype(np.float32, copy=False)
    if array.ndim == 2:
        return np.asarray(Image.fromarray(array.astype(np.float32)).resize((size,size), Image.Resampling.BILINEAR))
    return np.stack([resize(array[:,:,c], size) for c in range(array.shape[2])], axis=-1)


def blur(array, radius):
    if radius <= 0:
        return array
    # Smoothing is on the baked scalar map, not on color or tangent normals.
    return np.asarray(Image.fromarray(np.rint(np.clip(array,0,1)*255).astype('uint8')).filter(
        ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255


def noise(position, scale, seed=0):
    """Continuous 3D value noise: shared positions agree across UV seams."""
    p = position * scale
    cell = np.floor(p).astype(np.int64)
    f = p - cell
    f = f*f*(3-2*f)
    result = np.zeros(p.shape[:2], dtype=np.float32)
    for x in (0,1):
        for y in (0,1):
            for z in (0,1):
                h = ((cell[:,:,0]+x)*73856093 ^ (cell[:,:,1]+y)*19349663 ^
                     (cell[:,:,2]+z)*83492791 ^ (int(seed)&0xffffffff)*2654435761) & 0xffffffff
                h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
                n = (h ^ (h >> 16)).astype(np.float32) / 4294967295
                weight = (f[:,:,0] if x else 1-f[:,:,0]) * (f[:,:,1] if y else 1-f[:,:,1]) * (f[:,:,2] if z else 1-f[:,:,2])
                result += n * weight
    return result


def fbm(position, scale, seed=0, octaves=4):
    result = np.zeros(position.shape[:2], dtype=np.float32)
    for i in range(octaves):
        result += noise(position, scale*2**i, seed+i*31) * .5**i
    return result / sum(.5**i for i in range(octaves))


def levels(value, level, contrast):
    width = max(.015, 1-float(contrast))
    x = np.clip((value - (1-float(level))) / width + .5, 0, 1)
    return x*x*(3-2*x)


def mask_builder(maps, settings, custom_grunge=None, custom_grunge2=None, scatter_input=None):
    """MG-style geometry mask with the legacy control names and polarity."""
    p = {**MASK_DEFAULTS, **settings}
    pos, normal = maps['position'][:,:,:3], maps['world_space_normal'][:,:,:3]*2-1
    ao = np.squeeze(maps['ambient_occlusion'])
    curv = np.squeeze(maps['curvature'])
    if not p['Use_Triplanar']:
        y,x = np.mgrid[:ao.shape[0],:ao.shape[1]]
        pos = np.stack([x/ao.shape[1],y/ao.shape[0],np.zeros_like(x)],axis=-1).astype(np.float32)
    # Blend independently projected noises with normal-dependent weights.
    seed = int(p['$randomseed'])
    sharpness = 1+7*p['Triplanar_Blending_Contrast']
    weights = np.abs(normal)**sharpness
    weights /= np.maximum(weights.sum(axis=-1,keepdims=True),1e-6)
    def projected(scale, salt=0):
        result = np.zeros(ao.shape, np.float32)
        for axis in range(3):
            coords = pos.copy()
            coords[:,:,axis] = 0
            result += fbm(coords, scale, seed+salt+axis*73) * weights[:,:,axis]
        return result
    g = projected(8*2**(p['Grunge_Scale']*.5))
    if p['Grunge_Use_Custom_Grunge']:
        if custom_grunge is None:
            raise ValueError('Custom grunge is enabled but no custom_grunge map was supplied')
        g = np.squeeze(custom_grunge)
    if p['Grunge_Secondary_Custom_Grunge']:
        if custom_grunge2 is None:
            raise ValueError('Secondary grunge needs custom_grunge2')
        g = g*(1-p['Grunge_Secondary_Custom_Grunge'])+np.squeeze(custom_grunge2)*p['Grunge_Secondary_Custom_Grunge']
    if p['Grunge_Invert']:
        g = 1-g
    an = fbm(pos, 12*2**p['AO_Noise_Scale'], seed+int(p['AO_Noise_Type'])*17)
    cavities = levels(1-ao, p['AO_Range'], p['AO_Contrast'])
    if p['AO_Invert']:
        cavities = 1-cavities
    cavities *= 1-p['AO_Noisiness']+an*p['AO_Noisiness']*1.8
    curv = blur(curv, p['Curvature_Smoothness'])
    convex, concave = np.maximum(curv-.5,0)*2, np.maximum(.5-curv,0)*2
    cn = fbm(pos, 12*2**p['Curvature_Noise_Scale'], seed+int(p['Curvature_Noise_Type'])*43)
    cv = levels(convex, abs(p['Curvature_Convex_Range']), p['Curvature_Convex_Contrast'])
    cc = levels(concave, abs(p['Curvature_Concave_Range']), p['Curvature_Concave_Contrast'])
    if p['Curvature_Convex_Invert']:
        cv = 1-cv
    if p['Curvature_Concave_Invert']:
        cc = 1-cc
    curvature = cv*np.sign(p['Curvature_Convex_Range']) + cc*np.sign(p['Curvature_Concave_Range'])
    curvature *= (1-p['Curvature_Noisiness']+cn*p['Curvature_Noisiness']*2)
    curvature *= 1+p['Curvature_Level_Boost']
    score = p['Grunge']*g + .65*p['AO']*cavities + .65*p['Curvature']*curvature
    gradient = levels(pos[:,:,1], p['Gradient_Range'], p['Gradient_Contrast'])
    if p['Gradient_Invert']:
        gradient = 1-gradient
    score += p['Top_Down_Gradient']*gradient
    directions = [('Top',1,1),('Bottom',1,-1),('Front',2,1),('Back',2,-1),('Right',0,1),('Left',0,-1)]
    oriented = sum(np.maximum(normal[:,:,axis]*sign,0)*p[f'World_Space_Normal_{name}_Intensity'] for name,axis,sign in directions)
    score += p['World_Space_Normal']*oriented
    if p['Scratches']:
        q = pos.copy()
        q[:,:,0] *= max(1,p['Scratches_Amount']/30)
        q[:,:,1] *= max(.1,p['Scratches_Scale'])
        score += p['Scratches']*levels(noise(q, 20,seed+141), .1,.97)
    if p['Scatter']:
        density = np.clip(p['Scatter_Density']*.1,0,1)
        scatter = levels(noise(pos, max(1,p['Scatter_Scale']),seed+211), density,.95)
        scatter *= levels(noise(pos,max(1,p['Scatter_Scale'])*2,seed+212),p['Scatter_Size'],p['Scatter_Size_Variation'])
        scatter *= 1-p['Scatter_Opacity_Variation']+g*p['Scatter_Opacity_Variation']
        if scatter_input is not None:
            scatter *= np.squeeze(scatter_input)
        score += p['Scatter']*scatter
    result = levels(score, p['Level'],p['Contrast'])
    return np.clip(1-result if p['Invert'] else result,0,1).astype(np.float32)


def steel_material(position, settings):
    p = {**RECIPE['steel'], **settings}
    fine = fbm(position,180,p['seed'])
    broad = fbm(position,12*max(.1,p['dirt_scale']),p['seed']+7)
    rust = levels(broad,p['rust']*.65,p['dirt_contrast']+.4)
    dirt = levels(fbm(position,35,p['seed']+17),p['dirt'],.6)
    metal = np.asarray(p['metal_color'],np.float32)
    base = metal[None,None,:]*(.4+fine[:,:,None]*1.3)
    rust_color = np.array([.12,.038,.009],np.float32)[None,None,:]*(.6+fine[:,:,None])
    base = base*(1-rust[:,:,None]) + rust_color*rust[:,:,None]
    base *= 1-.6*dirt[:,:,None]
    rough = np.clip(p['metal_roughness']+rust*.3+dirt*.15+(fine-.5)*p['noisiness'],0,1)
    metallic = np.clip(1-rust*.88-dirt*.2,0,1)
    height = (fine-.5)*p['surface_imperfections']*.1-rust*.004
    return {'base_color':base,'roughness':rough,'metallic':metallic,'height':height}


def save_image(path, array, color=False):
    if color:
        array = srgb(array)
    image = np.rint(np.clip(array,0,1)*255).astype(np.uint8)
    Image.fromarray(image).save(path)


def generate(mesh_maps, output, size=2048, overrides=None):
    if size not in (256,512,1024,2048,4096):
        raise ValueError('size must be 256, 512, 1024, 2048, or 4096')
    settings = recipe(overrides)
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    source = Path(mesh_maps)
    required = ('position','world_space_normal','ambient_occlusion','curvature','normal')
    worksize = min(size,1024)
    if source.suffix == '.npz':
        with np.load(source,allow_pickle=False) as data:
            maps = {key:resize(data[key],worksize) for key in data.files}
    else:
        maps = {key:resize(np.asarray(Image.open(source/f'{key}.png'),dtype=np.float32)/255,worksize) for key in required}
    if set(required)-maps.keys():
        raise ValueError(f'Missing mesh maps: {set(required)-maps.keys()}')
    for key in required:
        if not np.isfinite(maps[key]).all():
            raise ValueError(f'Non-finite mesh map: {key}')
    paint = mask_builder(maps,settings['paint'])
    dirty = mask_builder(maps,settings['dirty'])
    dust = mask_builder(maps,settings['dust'])
    masks = {'paint':paint,'dirty':dirty,'dust':dust}
    steel = steel_material(maps['position'][:,:,:3],settings['steel'])
    layers = []
    for key,mask in masks.items():
        path = output/f'mask_{key}.png'
        save_image(path,resize(mask,size))
    save_image(output/'mask_dirty_with_paint.png',resize(dirty*paint,size))
    for name,channels,enabled in [
        ('Steel Rust and Wear',steel,True),
        ('Clean Paint',{'base_color':np.broadcast_to(settings['clean_color'],(*paint.shape,3)),
                        'roughness':np.full(paint.shape,settings['clean_roughness']),
                        'metallic':np.zeros(paint.shape),'height':np.full(paint.shape,settings['clean_height'])},True),
        ('Dirty Paint',{'base_color':np.broadcast_to(settings['dirty_color'],(*paint.shape,3)),
                        'roughness':np.full(paint.shape,settings['dirty_roughness'])},True),
        ('Dust',{'base_color':np.broadcast_to(settings['dust_color'],(*paint.shape,3)),
                 'roughness':np.full(paint.shape,settings['dust_roughness'])},settings['dust_enabled'])]:
        files = {}
        prefix = name.lower().replace(' ','_')
        for channel,array in channels.items():
            path = output/f'{prefix}_{channel}.png'
            # ArmorPaint uses zero height, not midpoint-gray, as the no-height value.
            save_image(path,resize(array,size),channel=='base_color')
            files[channel]=str(path)
        layers.append({'name':name,'enabled':enabled,'channels':files})
    normal = maps['normal'][:,:,:3].copy()
    normal = normal*2-1
    normal[:,:,:2] *= settings['steel']['normal_intensity']*2
    normal /= np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-8)
    normal = normal*.5+.5
    normal[:,:,1] = 1-normal[:,:,1]  # Painter DirectX -> ArmorPaint OpenGL
    save_image(output/'normal.png',resize(normal,size))
    save_image(output/'ambient_occlusion.png',resize(np.squeeze(maps['ambient_occlusion']),size))
    # A flattened PBR preview is useful outside ArmorPaint; editable layers are retained above.
    base,rough,metal = steel['base_color'].copy(),steel['roughness'].copy(),steel['metallic'].copy()
    base = base*(1-paint[:,:,None])+np.asarray(settings['clean_color'])[None,None,:]*paint[:,:,None]
    rough = rough*(1-paint)+settings['clean_roughness']*paint
    metal *= 1-paint
    for mask,color,r in [(dirty*paint*settings['dirty_opacity'],settings['dirty_color'],settings['dirty_roughness']),
                         (dust*settings['dust_opacity']*int(settings['dust_enabled']),settings['dust_color'],settings['dust_roughness'])]:
        base = base*(1-mask[:,:,None])+np.asarray(color)[None,None,:]*mask[:,:,None]
        rough = rough*(1-mask)+r*mask
    for key,array in [('base_color',base),('roughness',rough),('metallic',metal)]:
        save_image(output/f'{key}.png',resize(array,size),key=='base_color')
    manifest = {'schema':1,'size':size,'mesh_maps':str(source.resolve()),'recipe':settings,
        'layers':layers,'masks':{k:str(output/f'mask_{k}.png') for k in masks},
        'normal':str(output/'normal.png'),'ambient_occlusion':str(output/'ambient_occlusion.png')}
    manifest['masks']['dirty']=str(output/'mask_dirty_with_paint.png')
    path = output/'machinery.json'
    path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return {'manifest':str(path),'size':size,'layers':len(layers),'implementation':settings['implementation']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh_maps',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--size',type=int,default=2048)
    parser.add_argument('--settings',type=Path)
    args = parser.parse_args()
    overrides = json.loads(args.settings.read_text()) if args.settings else None
    print(json.dumps(generate(args.mesh_maps,args.output,args.size,overrides),indent=2))
