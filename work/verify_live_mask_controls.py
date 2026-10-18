"""Verify actual GPU output, atomic edits, undo/redo and persistence of live masks."""
import asyncio
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image
from armorpaint_mcp.server import call_tool
from import_jens import ap

ROOT=Path('C:/Projects/DigitalJens-extracted')
OUT=ROOT/'live_mask_checks'

async def main():
    OUT.mkdir(exist_ok=True)
    await ap('ap_project_open',path=str(ROOT/'Dirt_Mask_Live_Example.arm'))
    saved=json.loads((ROOT/'dirt_mask_example/generator.json').read_text())
    await ap('ap_material_select',name=saved['material'])
    await ap('ap_layer_select',name=saved['mask'])
    node=saved['id']
    original={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    report={}
    timings=[]
    async def render(label,settings):
        start=time.perf_counter()
        await ap('ap_mask_generator_set',id=node,parameters={**original,**settings})
        await ap('ap_mask_generator_get',id=node)
        timings.append((time.perf_counter()-start)*1000)
        await asyncio.sleep(.15)
        await ap('ap_export_pbr',directory=str(OUT),name=label)
        return np.asarray(Image.open(OUT/f'{label}_BaseColor.png'),dtype=np.float32)
    def changed(name,a,b,minimum=.1):
        delta=float(np.abs(a-b).mean())
        report[name]=delta
        assert delta>minimum,(name,delta)
    base={'AO':0,'Curvature':0,'Grunge':1,'Level':.5,'Invert':0,'Use_Triplanar':1}
    seed0=await render('seed0',base)
    seed7=await render('seed7',{**base,'$randomseed':7})
    changed('seed changes pattern',seed0,seed7,1)
    again=await render('seed0_again',base)
    assert np.array_equal(seed0,again),'Same seed and settings did not reproduce identical GPU output'
    empty=await render('zero',{**base,'Level':0})
    full=await render('one',{**base,'Level':1})
    assert empty.mean()>full.mean()+30,'Dirt coverage endpoints are wrong'
    inverted=await render('one_inverted',{**base,'Level':1,'Invert':1})
    np.testing.assert_array_equal(empty,inverted)
    ao0=await render('ao0',{**base,'Grunge':0,'AO':0,'Level':.65})
    ao1=await render('ao1',{**base,'Grunge':0,'AO':1,'AO_Noisiness':0,'AO_Range':.9,'Level':.65})
    changed('baked AO affects mask',ao0,ao1,1)
    convex=await render('convex',{**base,'Grunge':0,'Curvature':1,'Curvature_Noisiness':0,
        'Curvature_Convex_Range':.8,'Curvature_Concave_Range':0,'Level':.65})
    concave=await render('concave',{**base,'Grunge':0,'Curvature':1,'Curvature_Noisiness':0,
        'Curvature_Convex_Range':0,'Curvature_Concave_Range':.8,'Level':.65})
    changed('convex and concave differ',convex,concave,1)
    smooth=await render('smooth',{**base,'Grunge':0,'Curvature':1,'Curvature_Noisiness':0,
        'Curvature_Convex_Range':0,'Curvature_Concave_Range':.8,'Curvature_Smoothness':8,'Level':.65})
    changed('curvature smoothing resamples map',concave,smooth)
    scratches=await render('scratches',{**base,'Grunge':0,'Scratches':1,'Scratches_Amount':1000,'Level':.7})
    blank=await render('blank',{**base,'Grunge':0,'Level':.7})
    changed('procedural scratches',blank,scratches)
    scatter=await render('scatter',{**base,'Grunge':0,'Scatter':1,'Scatter_Density':.6,'Scatter_Size':2.5,'Level':.7})
    changed('procedural scatter',blank,scatter)
    # Invalid batches must not partially change any parameter.
    before={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    result=await call_tool('ap_mask_generator_set',{'id':node,'parameters':{'Level':.123,'NotAControl':1}})
    assert json.loads(result[0].text)['ok'] is False
    after={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    assert before==after,'Invalid batch partially applied'
    # Use source-provided scalar inputs and an actual Image Texture for custom grunge.
    checker=np.indices((64,64)).sum(axis=0)//8%2
    image=OUT/'custom_grunge.png'
    Image.fromarray((checker*255).astype('uint8')).save(image)
    await ap('ap_import_asset',path=str(image))
    index=(await ap('ap_project_list_texture_assets'))['count']-1
    image_node=(await ap('ap_node_add',type='TEX_IMAGE',x=-650,y=800))['id']
    await ap('ap_node_set_value',id=image_node,kind='button',button=0,value=index)
    await ap('ap_node_connect',from_id=image_node,from_socket=0,to_id=node,to_socket=3)
    uv=await render('custom_uv',{**base,'Grunge_Use_Custom_Grunge':1,'Use_Triplanar':0})
    tri=await render('custom_triplanar',{**base,'Grunge_Use_Custom_Grunge':1,'Use_Triplanar':1})
    changed('custom grunge triplanar projection',uv,tri,1)
    await ap('ap_pack_assets')
    project=OUT/'verified_controls.arm'
    await ap('ap_project_save_as',path=str(project))
    await asyncio.sleep(2)
    expected={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    await ap('ap_project_open',path=str(project))
    await ap('ap_material_select',name=saved['material'])
    await ap('ap_layer_select',name=saved['mask'])
    actual={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    assert actual==expected,'Generator controls were not retained on save/reopen'
    old=actual['Level']
    await ap('ap_mask_generator_set',id=node,parameter='Level',value=.123)
    await ap('ap_undo')
    undo={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    assert undo['Level']==old,'Undo did not restore generator settings'
    await ap('ap_redo')
    redo={p['name']:p['value'] for p in (await ap('ap_mask_generator_get',id=node))['parameters']}
    assert abs(redo['Level']-.123)<1e-6,'Redo did not restore generator edit'
    report.update({'control_count':len(actual),'atomic_validation':True,'save_reload':True,'undo_redo':True,'seed_reproducible':True})
    report['edit_and_next_frame_median_ms']=float(np.median(timings))
    (OUT/'live_control_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    await ap('ap_project_open',path=str(ROOT/'Dirt_Mask_Live_Example.arm'))
    await ap('ap_material_select',name=saved['material'])
    await ap('ap_layer_select',name=saved['mask'])
    print('LIVE_CONTROL_VERIFICATION_PASSED',json.dumps(report,indent=2))

asyncio.run(main())
