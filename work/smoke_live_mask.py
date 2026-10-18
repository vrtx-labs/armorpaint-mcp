"""GPU smoke test: changing a generator parameter must refill without a fill call."""
import asyncio
from pathlib import Path
import numpy as np
from PIL import Image
from import_jens import ap

async def main():
    out=Path('C:/Projects/DigitalJens-extracted/live_mask_checks')
    out.mkdir(exist_ok=True)
    await ap('ap_project_new')
    await ap('ap_import_asset',path='C:/Projects/DigitalJens-extracted/DigitalJens.obj')
    await ap('ap_material_create',name='Live Mask Builder test')
    nodes=await ap('ap_node_list')
    output=next(int(n.split(',')[0]) for n in nodes['nodes'].split(';') if ',OUTPUT_MATERIAL_PBR,' in n)
    for n in nodes['nodes'].split(';'):
        if n and ',OUTPUT_MATERIAL_PBR,' not in n:
            await ap('ap_node_remove',id=int(n.split(',')[0]))
    gen=(await ap('ap_node_add',type='MASK_BUILDER',x=-300,y=0))['id']
    info=await ap('ap_mask_generator_get',id=gen)
    assert len(info['parameters'])==50
    await ap('ap_mask_generator_set',id=gen,parameters={'AO':0,'Curvature':0,'Grunge':1,'Use_Triplanar':1,'Level':.5})
    await ap('ap_node_connect',from_id=gen,from_socket=0,to_id=output,to_socket=0)
    await ap('ap_material_set_channels',base=True,opacity=True,occlusion=False,roughness=False,metallic=False,normal=False,height=False,emission=False,subsurface=False)
    await ap('ap_material_update')
    await ap('ap_layer_create',name='Live generator output',kind='fill')
    await ap('ap_layer_delete',name='Layer 1')
    await asyncio.sleep(.3)
    await ap('ap_export_pbr',directory=str(out),name='baseline')
    baseline=np.asarray(Image.open(out/'baseline_BaseColor.png'),dtype=np.float32)
    assert baseline.std()>5,'Generator did not produce nonconstant output'
    await ap('ap_mask_generator_set',id=gen,parameter='Level',value=0)
    await asyncio.sleep(.3)
    await ap('ap_export_pbr',directory=str(out),name='level_zero')
    zero=np.asarray(Image.open(out/'level_zero_BaseColor.png'))
    assert zero.max()==0,'Level 0 did not automatically update the fill'
    await ap('ap_mask_generator_set',id=gen,parameter='Level',value=1)
    await asyncio.sleep(.3)
    await ap('ap_export_pbr',directory=str(out),name='level_one')
    one=np.asarray(Image.open(out/'level_one_BaseColor.png'))
    assert one.max()==255 and one.mean()>zero.mean()+50,'Level 1 did not automatically update the fill'
    await ap('ap_mask_generator_set',id=gen,parameter='Level',value=.5)
    await ap('ap_capture_viewport',path=str(out/'smoke_view.png'),width=1000,height=1000,include_image=False)
    print('LIVE_MASK_SMOKE_PASSED',gen,float(baseline.std()))

asyncio.run(main())
