import asyncio
import json
import sys
from pathlib import Path
from import_jens import ap
from armorpaint_mcp.native_bake import bake_maps

async def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else 'C:/Projects/DigitalJens-extracted/native_mesh_maps_verified')
    before=await ap('ap_layer_list')
    object_before=await ap('ap_get_main_object')
    result=await bake_maps(out,ap,samples=8)
    after=await ap('ap_layer_list')
    assert before['layers']==after['layers'],(before,after)
    object_after=await ap('ap_get_main_object')
    assert object_before['visible']==object_after['visible'],(object_before,object_after)
    await ap('ap_capture_viewport',path=str(out/'viewport_after_bake.png'),width=1000,height=1000,include_image=False)
    print(json.dumps(result,indent=2))

asyncio.run(main())
