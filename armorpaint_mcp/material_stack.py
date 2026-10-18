"""Assemble generated PBR resources as editable native ArmorPaint fill layers."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path


async def apply_manifest(manifest_path, call, prefix='Machinery'):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported smart-material manifest')
    live = bool(manifest.get('recipe') and manifest.get('mesh_maps'))
    maps = {}
    if live:
        from .live_masks import prepare_mesh_map_images, create_generator_material
        maps = prepare_mesh_map_images(manifest,manifest_path.parent)
    image_paths = {Path(p).resolve() for layer in manifest['layers'] for p in layer['channels'].values()}
    if not live:
        image_paths.update(Path(p).resolve() for p in manifest.get('masks',{}).values())
    image_paths.update(maps.values())
    image_paths.update(Path(manifest[k]).resolve() for k in ('normal','ambient_occlusion') if manifest.get(k))
    missing = [str(p) for p in image_paths if not p.is_file()]
    if missing:
        raise ValueError(f'Missing material resources: {missing}')
    await call('ap_texture_resolution',size=max(2048,manifest['size']))
    indices = {}
    for path in sorted(image_paths):
        before = await call('ap_project_list_texture_assets')
        await call('ap_import_asset',path=str(path))
        after = await call('ap_project_list_texture_assets')
        names = after['names'].split('|') if after['names'] else []
        if after['count'] > before['count']:
            indices[str(path)] = after['count']-1
        else:
            matches = [i for i,n in enumerate(names) if n == path.name or n == path.stem]
            if len(matches) != 1:
                raise ValueError(f'Cannot resolve already imported image {path}; use a fresh project or unique filenames')
            indices[str(path)] = matches[0]

    async def material(name, channels, mask=False):
        await call('ap_material_create',name=name)
        nodes = await call('ap_node_list')
        output = next(int(n.split(',')[0]) for n in nodes['nodes'].split(';') if ',OUTPUT_MATERIAL_PBR,' in n)
        # A newly created material has a Color -> Base Color link. Remove its
        # source before wiring images: duplicate links leave the first source active.
        for entry in nodes['nodes'].split(';'):
            if entry and ',OUTPUT_MATERIAL_PBR,' not in entry:
                await call('ap_node_remove',id=int(entry.split(',')[0]))
        for row,(channel,path) in enumerate(channels.items()):
            node = (await call('ap_node_add',type='TEX_IMAGE',x=-500,y=row*180))['id']
            await call('ap_node_set_value',id=node,kind='button',button=0,value=indices[str(Path(path).resolve())])
            # Mask baking consumes Base Color numerically. The node's explicit
            # Linear option gamma-encodes this socket; Auto leaves mask bytes intact.
            await call('ap_node_set_value',id=node,kind='button',button=1,value=0 if mask else (2 if channel=='base_color' else 1))
            await call('ap_node_connect',from_id=node,from_socket=0,to_id=output,
                to_socket={'base_color':0,'occlusion':2,'roughness':3,'metallic':4,'normal':5,'height':7}[channel])
        # Alpha is layer coverage, even for an opaque material. A cleared fill
        # layer with opacity writes disabled remains completely invisible.
        await call('ap_material_set_channels',**{k:(k=='opacity' or k in channels or (k=='base' and 'base_color' in channels))
            for k in ('base','opacity','occlusion','roughness','metallic','normal','height','emission','subsurface')})
        await call('ap_material_update')

    created = []
    machinery_group = None
    generators = {}
    for i,layer in enumerate(manifest['layers']):
        name = f'{prefix} - {layer["name"]}'
        channels = dict(layer['channels'])
        if i == 0:
            for key,target in [('normal','normal'),('ambient_occlusion','occlusion')]:
                if manifest.get(key):
                    channels[target]=manifest[key]
        await material(name,channels)
        native = await call('ap_layer_create',name=name,kind='fill')
        name = native['name']
        created.append(name)
        await call('ap_layer_update',name=name,visible=layer.get('enabled',True))
        if len(manifest['layers']) == 1:
            continue
        if live:
            if layer['name']=='Clean Paint':
                machinery_group = (await call('ap_layer_create',name=f'{prefix} - Paint',kind='group'))['name']
            elif layer['name']=='Dirty Paint':
                await call('ap_layer_update',name=name,group=machinery_group,opacity=manifest['recipe']['dirty_opacity'])
            elif layer['name']=='Dust':
                await call('ap_layer_update',name=name,group='',opacity=manifest['recipe']['dust_opacity'])
        elif i == 0:
            machinery_group = (await call('ap_layer_create',name=prefix,kind='group'))['name']
        else:
            # Native ArmorPaint groups are one level deep. Flatten the Painter
            # Paint subgroup and use its multiplied mask on Dirty Paint.
            await call('ap_layer_update',name=name,group=machinery_group)
            if layer['name']!='Clean Paint':
                opacity = manifest['recipe']['dirty_opacity'] if layer['name']=='Dirty Paint' else manifest['recipe']['dust_opacity']
                await call('ap_layer_update',name=name,opacity=opacity)
        key = {'Clean Paint':'paint','Dirty Paint':'dirty','Dust':'dust'}.get(layer['name'])
        if key:
            if live:
                generators[key] = await create_generator_material(call,f'{prefix} - MG Mask Builder - {key}',manifest['recipe'][key],maps,indices)
            else:
                await material(f'{prefix} - MG Mask Builder - {key}',{'base_color':manifest['masks'][key]},mask=True)
            await call('ap_layer_select',name=machinery_group if live and key=='paint' else name)
            mask_name = (await call('ap_layer_create',name=f'{prefix} - MG Mask Builder - {key}',kind='fill_mask'))['name']
            created.append(mask_name)
            if live:
                generators[key]['layer'] = mask_name
            await call('ap_layer_select',name=name)
    # Let scheduled fill-layer updates reach the render path before the caller saves/captures.
    await asyncio.sleep(1)
    result = {'created':created,'group':machinery_group,'manifest':str(manifest_path.resolve()),'live_masks':live,'generators':generators}
    if live:
        (manifest_path.parent/'live_generators.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
