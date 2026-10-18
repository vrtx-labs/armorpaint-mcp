"""Assemble native GPU mask generators; only the baked mesh inputs are images."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image


def prepare_mesh_map_images(manifest, directory):
    source = Path(manifest['mesh_maps'])
    maps = ('world_space_normal','ambient_occlusion','curvature','position')
    if source.is_dir():
        paths = {key:(source/f'{key}.png').resolve() for key in maps}
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise ValueError(f'Missing generator mesh maps: {missing}')
        return paths
    if not source.is_file() or source.suffix.lower()!='.npz':
        raise ValueError('Live generators need the baked mesh-map NPZ or PNG directory')
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    directory = Path(directory)/'live_mesh_maps'
    directory.mkdir(parents=True,exist_ok=True)
    paths = {}
    with np.load(source,allow_pickle=False) as archive:
        for key in maps:
            if key not in archive:
                raise ValueError(f'Missing baked input for live mask generator: {key}')
            array = archive[key]
            if array.ndim==3:
                array = array[:,:,:3] if key in ('world_space_normal','position') else array[:,:,0]
            if not np.isfinite(array).all():
                raise ValueError(f'Non-finite mesh map: {key}')
            path = (directory/f'mg_{fingerprint}_{key}.png').resolve()
            Image.fromarray(np.rint(np.clip(array,0,1)*255).astype('uint8')).save(path)
            paths[key] = path
    return paths


async def create_generator_material(call, name, settings, maps, indices, node_type='MASK_BUILDER'):
    material = await call('ap_material_create',name=name)
    nodes = await call('ap_node_list')
    output = None
    for entry in nodes['nodes'].split(';'):
        if not entry:
            continue
        node_id = int(entry.split(',')[0])
        if ',OUTPUT_MATERIAL_PBR,' in entry:
            output = node_id
        else:
            await call('ap_node_remove',id=node_id)
    generator = (await call('ap_node_add',type=node_type,x=30,y=20))['id']
    await call('ap_mask_generator_set',id=generator,parameters={k:v for k,v in settings.items() if k!='$outputsize'})
    for row,(key,socket) in enumerate((('world_space_normal',0),('ambient_occlusion',1),('curvature',2),('position',6))):
        image = (await call('ap_node_add',type='TEX_IMAGE',x=-650,y=row*190))['id']
        await call('ap_node_set_value',id=image,kind='button',button=0,value=indices[str(maps[key])])
        await call('ap_node_set_value',id=image,kind='button',button=1,value=1)
        await call('ap_node_connect',from_id=image,from_socket=0,to_id=generator,to_socket=socket)
    await call('ap_node_connect',from_id=generator,from_socket=0,to_id=output,to_socket=0)
    await call('ap_material_set_channels',base=True,opacity=True,occlusion=False,roughness=False,metallic=False,
               normal=False,height=False,emission=False,subsurface=False)
    await call('ap_material_update')
    return {'material':material['name'],'id':generator,'type':node_type}
