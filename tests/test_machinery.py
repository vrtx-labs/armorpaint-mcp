import asyncio
import json
import pytest
np = pytest.importorskip('numpy')
Image = pytest.importorskip('PIL.Image')
from armorpaint_mcp.machinery import MASK_DEFAULTS, generate, mask_builder, noise, recipe
from armorpaint_mcp.server import call_tool, _build_wire_args
from armorpaint_mcp.transport import BadArgs


def maps(size=16):
    y,x=np.mgrid[:size,:size].astype(np.float32)/size
    pos=np.stack([x,y,np.full_like(x,.5)],axis=-1)
    return {'position':pos,'world_space_normal':np.broadcast_to([.5,1,.5],pos.shape),
            'ambient_occlusion':np.ones((size,size),np.float32),
            'curvature':np.full((size,size),.5,np.float32),
            'normal':np.broadcast_to([.5,.5,1],pos.shape)}


def test_noise_is_position_based_across_uv_seams():
    pos=maps()['position'].copy()
    pos[-1,-1]=pos[0,0]
    values=noise(pos,15,seed=7)
    assert values[0,0]==values[-1,-1]
    assert not np.array_equal(values,noise(pos,15,seed=8))


def test_generator_polarity_and_geometry_response():
    data=maps()
    settings={**MASK_DEFAULTS,'Grunge':0,'Curvature':0,'AO_Noisiness':0,
              'AO_Range':.5,'AO_Contrast':1,'Contrast':.8,'Level':.5}
    clean=mask_builder(data,settings)
    data['ambient_occlusion'][:,:8]=0
    dirty=mask_builder(data,settings)
    assert dirty[:,:8].mean()>clean[:,:8].mean()+.5
    inverse=mask_builder(data,{**settings,'Invert':1})
    np.testing.assert_allclose(dirty+inverse,1,atol=1e-6)
    assert np.isfinite(dirty).all()


def test_generate_round_trip_and_manifest_resources(tmp_path):
    archive=tmp_path/'maps.npz'
    np.savez(archive,**maps())
    result=generate(archive,tmp_path/'material',256)
    manifest=json.loads(open(result['manifest'],encoding='utf-8').read())
    assert len(manifest['layers'])==4
    assert manifest['layers'][-1]['enabled'] is False
    for layer in manifest['layers']:
        for path in layer['channels'].values():
            with Image.open(path) as image:
                assert image.size==(256,256)
    dirty=np.asarray(Image.open(manifest['masks']['dirty']))
    paint=np.asarray(Image.open(manifest['masks']['paint']),dtype=np.int16)
    assert (dirty<=paint+1).all()  # subgroup mask also restricts Dirty Paint


def test_unknown_recipe_controls_are_rejected():
    with pytest.raises(ValueError):
        recipe({'paint':{'not_a_parameter':1}})


def test_local_tools_validate_without_live_bridge():
    result=asyncio.run(call_tool('ap_mesh_bake_status',{'job':'absent'}))
    assert json.loads(result[0].text)['code']=='bad_args'


def test_native_baker_argument_mapping_and_output_protection(tmp_path):
    output=tmp_path/'curvature.png'
    args=_build_wire_args('ap_bake_map_start',{'kind':'signed_curvature','path':str(output),'samples':8})
    assert args['type']==14 and args['samples']==8
    output.touch()
    with pytest.raises(BadArgs,match='already exists'):
        _build_wire_args('ap_bake_map_start',{'kind':'signed_curvature','path':str(output)})
    result=asyncio.run(call_tool('ap_smart_material_generate',{
        'mesh_maps':'C:/missing.npz','output':'C:/unused','settings':[]}))
    assert json.loads(result[0].text)['code']=='bad_args'
