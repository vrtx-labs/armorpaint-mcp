import asyncio
import json
import os
from pathlib import Path

os.environ["ARMORPAINT_DIR"] = "D:/Projects/armorpaint/paint/build/out"
from armorpaint_mcp.server import call_tool

ROOT = Path("P:/DLR/DLR 3D-Welten für mozu/development/models/logo")
OUT = ROOT / "MOZU_Illuminated_Sign"
WORK = Path(__file__).parent

async def ap(tool, **args):
    result = await call_tool(tool, args)
    data = json.loads(next(x.text for x in result if x.type == "text"))
    if not data.get("ok"):
        raise RuntimeError(f"{tool}: {data}")
    payload = data.get("result", data)
    print(tool, json.dumps(payload, ensure_ascii=True), flush=True)
    return payload

async def setup():
    OUT.mkdir(exist_ok=True)
    await ap("ap_import_asset", path=str(ROOT / "logo_3d.fbx"))
    await asyncio.sleep(3)
    await ap("ap_get_main_object")
    await ap("ap_layer_list")
    await ap("ap_node_list")
    await ap("ap_capture_viewport", path=str(WORK / "mesh-import.png"), width=1600, height=900, include_image=False)

if __name__ == "__main__":
    asyncio.run(setup())
