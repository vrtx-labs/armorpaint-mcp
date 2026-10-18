"""CLI for calling the same validated MCP tool handlers used by stdio clients."""
import asyncio
import json
import os
import sys

from pathlib import Path
os.environ.setdefault("ARMORPAINT_DIR", str(Path(__file__).resolve().parents[2] / "armorpaint/paint/build/out"))
from armorpaint_mcp.server import call_tool

async def main():
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    if name == "ap_quit" and not args:
        args = {"confirm": True}
    result = await call_tool(name, args)
    for item in result:
        if item.type == "text":
            print(item.text)
        else:
            print("[image returned]")

asyncio.run(main())
