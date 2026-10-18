import pytest
from armorpaint_mcp.server import _build_wire_args
from armorpaint_mcp.transport import BadArgs

@pytest.mark.parametrize("tool,args", [
    ("ap_layer_create", {"name":"a", "kind":"invalid"}),
    ("ap_layer_update", {"name":"a", "opacity":1.1}),
    ("ap_layer_update", {"name":"a", "visible":"false"}),
    ("ap_layer_update", {"name":"a", "blending":18}),
    ("ap_layer_update", {"name":"a"}),
    ("ap_layer_move", {"name":"a", "index":-1}),
    ("ap_texture_resolution", {"size":3000}),
    ("ap_export_pbr", {"directory":"D:/output", "name":"../wrong"}),
    ("ap_view_set", {"view":"invalid"}),
])
def test_invalid_arguments_do_not_reach_native_api(tool, args):
    with pytest.raises(BadArgs):
        _build_wire_args(tool, args)

def test_false_zero_and_empty_group_are_not_dropped():
    args = {"name":"Layer", "visible":False, "opacity":0, "blending":0, "group":""}
    assert _build_wire_args("ap_layer_update",args) == args
