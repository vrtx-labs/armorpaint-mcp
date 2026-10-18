import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, ARMORPAINT_DIR="D:/Projects/armorpaint/paint/build/out")
    params = StdioServerParameters(command="D:/Projects/armorpaint-mcp/.venv/Scripts/python.exe", args=["-m", "armorpaint_mcp"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {"ap_undo", "ap_redo", "ap_layer_create", "ap_layer_update"} <= {t.name for t in tools.tools}
            response = await session.call_tool("ap_ping", {})
            print("MCP stdio initialized:", len(tools.tools), "tools")
            print(response)

asyncio.run(main())
