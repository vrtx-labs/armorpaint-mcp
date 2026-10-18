import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, ARMORPAINT_DIR=str(Path(__file__).resolve().parents[2] / "armorpaint/paint/build/out"))
    params = StdioServerParameters(command=sys.executable, args=["-m", "armorpaint_mcp"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            print('Starting MCP initialization...', flush=True)
            await asyncio.wait_for(session.initialize(), 20)
            print('Initialized; listing tools...', flush=True)
            tools = await asyncio.wait_for(session.list_tools(), 20)
            assert {"ap_undo", "ap_redo", "ap_layer_create", "ap_layer_update", "ap_bake_mesh_maps",
                    "ap_bake_map_start", "ap_smart_material_generate", "ap_smart_material_apply"} <= {t.name for t in tools.tools}
            assert {'ap_mask_generator_get','ap_mask_generator_set'} <= {t.name for t in tools.tools}
            print('Tools listed; pinging bridge...', flush=True)
            response = await asyncio.wait_for(session.call_tool("ap_ping", {}), 20)
            assert json.loads(response.content[0].text).get('ok'), response
            print("MCP stdio initialized:", len(tools.tools), "tools")
            print(response)
            info = await asyncio.wait_for(session.call_tool('ap_smart_material_info', {}), 20)
            assert json.loads(info.content[0].text)['recipe']['name']=='Machinery'
            print('Smart-material tools available over MCP stdio.')
            if len(sys.argv)>1:
                baked = await asyncio.wait_for(session.call_tool('ap_bake_mesh_maps',
                    {'directory':sys.argv[1],'samples':8}),120)
                assert json.loads(baked.content[0].text).get('ok'),baked
                print('Native mesh-map suite completed through MCP stdio:',baked.content[0].text,flush=True)

asyncio.run(main())
