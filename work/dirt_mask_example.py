"""Build a minimal two-layer example and show live dirt amount changes."""
import asyncio
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from import_jens import ap
from armorpaint_mcp.live_masks import prepare_mesh_map_images, create_generator_material

ROOT=Path('C:/Projects/DigitalJens-extracted')
OUT=ROOT/'dirt_mask_example'

async def color_material(name,color,roughness):
    await ap('ap_material_create',name=name)
    nodes=await ap('ap_node_list')
    output=next(int(n.split(',')[0]) for n in nodes['nodes'].split(';') if ',OUTPUT_MATERIAL_PBR,' in n)
    rgb=next(int(n.split(',')[0]) for n in nodes['nodes'].split(';') if ',RGB,' in n)
    await ap('ap_node_set_value',id=rgb,kind='color',socket=0,is_input=False,color=color)
    await ap('ap_node_set_value',id=output,kind='float',socket=3,value=roughness)
    await ap('ap_node_set_value',id=output,kind='float',socket=4,value=0)
    await ap('ap_material_set_channels',base=True,opacity=True,occlusion=False,roughness=True,metallic=False,normal=False,height=False,emission=False,subsurface=False)
    await ap('ap_material_update')

async def main():
    OUT.mkdir(exist_ok=True)
    await ap('ap_project_new')
    await ap('ap_import_asset',path=str(ROOT/'DigitalJens.obj'))
    await color_material('Example - yellow paint',[1,.65,.03,1],.3)
    await ap('ap_layer_create',name='01 - Yellow paint',kind='fill')
    await color_material('Example - brown dirt',[.18,.095,.035,1],.9)
    await ap('ap_layer_create',name='02 - Brown dirt',kind='fill')
    maps=prepare_mesh_map_images({'mesh_maps':str(ROOT/'mesh_maps/mesh_maps.npz')},OUT)
    indices={}
    for path in maps.values():
        await ap('ap_import_asset',path=str(path))
        info=await ap('ap_project_list_texture_assets')
        indices[str(path)]=info['count']-1
    settings={'Level':.55,'Contrast':.45,'Grunge':.25,'AO':1,'AO_Range':.8,'AO_Noisiness':.5,
        'Curvature':1,'Curvature_Convex_Range':0,'Curvature_Concave_Range':.6,'Use_Triplanar':1}
    generator=await create_generator_material(ap,'Example - LIVE Dirt Mask',settings,maps,indices,node_type='MASK_DIRT')
    await ap('ap_layer_select',name='02 - Brown dirt')
    mask=(await ap('ap_layer_create',name='03 - LIVE dirt generator (edit Level)',kind='fill_mask'))['name']
    await ap('ap_layer_delete',name='Layer 1')
    await ap('ap_layer_select',name=mask)
    await ap('ap_material_select',name=generator['material'])
    await ap('ap_view_set',view='front',zoom=.3)
    obj=await ap('ap_get_main_object')
    await ap('ap_object_set_visible',name=obj['name'],visible=True)
    for label,level in [('less_dirt',.4),('more_dirt',.75)]:
        await ap('ap_mask_generator_set',id=generator['id'],parameter='Level',value=level)
        await asyncio.sleep(.4)
        await ap('ap_capture_viewport',path=str(OUT/f'{label}.png'),width=900,height=1000,include_image=False)
        await ap('ap_export_pbr',directory=str(OUT),name=label)
    less=np.asarray(Image.open(OUT/'less_dirt_BaseColor.png'),dtype=np.float32)
    more=np.asarray(Image.open(OUT/'more_dirt_BaseColor.png'),dtype=np.float32)
    assert less.mean()>more.mean()+3,'Increasing dirt Level did not darken the actual material'
    await ap('ap_mask_generator_set',id=generator['id'],parameter='Level',value=.55)
    await ap('ap_pack_assets')
    project=ROOT/'Dirt_Mask_Live_Example.arm'
    await ap('ap_project_save_as',path=str(project))
    await asyncio.sleep(3)
    panel=Image.new('RGB',(1800,1045),(28,28,28))
    draw=ImageDraw.Draw(panel)
    for i,(label,title) in enumerate([('less_dirt','Less dirt - Level 0.40'),('more_dirt','More dirt - Level 0.75')]):
        with Image.open(OUT/f'{label}.png') as image:
            panel.paste(image,(i*900,45))
        draw.text((i*900+30,15),title,fill='white')
    panel.save(OUT/'live_dirt_comparison.png')
    (OUT/'generator.json').write_text(json.dumps({**generator,'mask':mask,'project':str(project),'settings':settings},indent=2),encoding='utf-8')
    print('DIRT_EXAMPLE_READY',project,'live texture delta',float(np.abs(less-more).mean()))

asyncio.run(main())
