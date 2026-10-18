import math
import pytest
from armorpaint_mcp.server import NODE_TYPES, _build_wire_args
from armorpaint_mcp.transport import BadArgs


def test_native_generator_nodes_are_available_to_graph_tools():
    assert {'MASK_BUILDER','MASK_EDGE_WEAR','MASK_DIRT','MASK_DUST'}<=NODE_TYPES


def test_mask_parameter_batches_are_flat_and_preserve_seed():
    wire=_build_wire_args('ap_mask_generator_set',{'id':9,'parameters':{'Level':.4,'$randomseed':7}})
    assert wire['id']==9
    fields=dict(entry.split('=') for entry in wire['changes'].split('|'))
    assert {key:float(value) for key,value in fields.items()}=={'Level':.4,'$randomseed':7}


@pytest.mark.parametrize('arguments',[
    {'id':1,'parameters':{}},
    {'id':1,'parameters':{'Level|AO':1}},
    {'id':1,'parameters':{'Level':math.inf}},
    {'id':1,'parameters':{'Level':True}},
    {'id':1,'parameters':{'Level':.4},'parameter':'AO','value':1},
])
def test_bad_mask_parameters_are_rejected_before_transport(arguments):
    with pytest.raises(BadArgs):
        _build_wire_args('ap_mask_generator_set',arguments)


def test_baked_inputs_remain_numeric_not_color_corrected(tmp_path):
    np=pytest.importorskip('numpy')
    Image=pytest.importorskip('PIL.Image')
    from armorpaint_mcp.live_masks import prepare_mesh_map_images
    source=tmp_path/'maps.npz'
    np.savez(source,world_space_normal=np.full((8,8,3),.5),position=np.full((8,8,3),.25),
             curvature=np.full((8,8),.5),ambient_occlusion=np.full((8,8),.75))
    paths=prepare_mesh_map_images({'mesh_maps':str(source)},tmp_path)
    assert np.asarray(Image.open(paths['curvature'])).mean()==128
    assert np.asarray(Image.open(paths['ambient_occlusion'])).mean()==191
    assert np.asarray(Image.open(paths['position'])).mean()==64
    assert len(paths)==4
