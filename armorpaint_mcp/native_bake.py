"""Collect native ArmorPaint bakes as a portable smart-material mesh-map set."""
import asyncio
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image


async def bake_maps(directory, call, samples=32, timeout=600):
    directory=Path(directory).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    kinds={'world_space_normal':'world_space_normal','position':'position',
           'curvature':'signed_curvature','ambient_occlusion':'ambient_occlusion','thickness':'thickness',
           'normal':'normal'}
    for name,kind in kinds.items():
        target=directory/f'{name}.png'
        if target.exists():
            raise ValueError(f'Bake output exists: {target}; use a new directory')
    for name,kind in kinds.items():
        target=directory/f'{name}.png'
        started=await call('ap_bake_map_start',kind=kind,path=str(target),samples=samples)
        deadline=time.monotonic()+timeout
        while True:
            await asyncio.sleep(.2)
            status=await call('ap_bake_map_status')
            if status['job']!=started['job']:
                raise RuntimeError('Another native bake replaced this job')
            if not status['pending']:
                if status['state']!=2 or not target.is_file():
                    raise RuntimeError(f'Native {kind} bake failed: {status}')
                break
            if time.monotonic()>deadline:
                raise TimeoutError(f'Native {kind} is still baking; poll ap_bake_map_status')
    maps={name:np.asarray(Image.open(directory/f'{name}.png').convert('RGB'),dtype=np.float32)/255 for name in kinds}
    for name in ('curvature','ambient_occlusion','thickness'):
        maps[name]=maps[name][:,:,0]
    # Native normal baker produces OpenGL; the portable recipe's inputs use Painter DirectX.
    maps['normal'][:,:,1]=1-maps['normal'][:,:,1]
    vectors=maps['world_space_normal']*2-1
    coverage=np.abs(np.linalg.norm(vectors,axis=-1)-1)<.06
    maps['coverage']=coverage.astype(np.float32)
    maps['curvature'][~coverage]=.5
    maps['ambient_occlusion'][~coverage]=1
    path=directory/'mesh_maps.npz'
    np.savez_compressed(path,**maps)
    (directory/'bake.json').write_text(json.dumps({'backend':'ArmorPaint native GPU','samples':samples,
        'normal':'Native transfer using current high-poly selection; self-bake when it is the same mesh',
        'curvature':'signed normal/position differential estimate, neutral 0.5',
        'maps':list(kinds)},indent=2),encoding='utf-8')
    return {'mesh_maps':str(path),'directory':str(directory),'maps':list(kinds)}
