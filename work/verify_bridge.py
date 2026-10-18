import asyncio
import json
import os
from pathlib import Path

os.environ["ARMORPAINT_DIR"] = "D:/Projects/armorpaint/paint/build/out"
from armorpaint_mcp.server import call_tool

async def call(tool, **args):
    result = await call_tool(tool, args)
    data = json.loads(next(x.text for x in result if x.type == "text"))
    if not data.get("ok"):
        raise RuntimeError(f"{tool}: {data}")
    print(tool, json.dumps(data.get("result", data)))
    return data.get("result", data)

async def main():
    await call("ap_ping")
    await call("ap_project_new")
    layers = await call("ap_layer_list")
    initial = layers["total"]
    await call("ap_layer_create", name="MCP verification")
    assert (await call("ap_layer_list"))["total"] == initial + 1
    await call("ap_layer_update", name="MCP verification", opacity=0.42)
    await call("ap_undo")
    assert (await call("ap_layer_list"))["layers"][-1]["opacity"] == 1.0
    await call("ap_redo")
    assert abs((await call("ap_layer_list"))["layers"][-1]["opacity"] - 0.42) < 1e-5
    await call("ap_layer_update", name="MCP verification", visible=False)
    await call("ap_undo")
    assert (await call("ap_layer_list"))["layers"][-1]["visible"]
    await call("ap_layer_update", name="MCP verification", new_name="MCP renamed")
    await call("ap_undo")
    assert (await call("ap_layer_list"))["layers"][-1]["name"] == "MCP verification"
    await call("ap_redo")
    await call("ap_layer_duplicate", name="MCP renamed")
    assert (await call("ap_layer_list"))["total"] == initial + 2
    await call("ap_undo")
    assert (await call("ap_layer_list"))["total"] == initial + 1
    await call("ap_redo")
    await call("ap_layer_delete", name="MCP renamed")
    await call("ap_undo")
    assert (await call("ap_layer_list"))["total"] == initial + 2
    before_move = [x["name"] for x in (await call("ap_layer_list"))["layers"]]
    await call("ap_layer_move", name=before_move[-1], index=0)
    await call("ap_undo")
    assert [x["name"] for x in (await call("ap_layer_list"))["layers"]] == before_move
    await call("ap_redo")
    assert (await call("ap_layer_list"))["layers"][0]["name"] == before_move[-1]
    await call("ap_undo")
    await call("ap_layer_select", name="MCP renamed")
    await call("ap_layer_create", name="MCP mask", kind="white_mask")
    assert any(x["mask"] for x in (await call("ap_layer_list"))["layers"])
    await call("ap_layer_delete", name="MCP mask")
    await call("ap_layer_create", name="MCP group", kind="group")
    assert any(x["group"] for x in (await call("ap_layer_list"))["layers"])
    await call("ap_layer_update", name="MCP renamed", group="")
    await call("ap_undo")
    assert any(x["name"] == "MCP group" for x in (await call("ap_layer_list"))["layers"])
    await call("ap_redo")
    await call("ap_layer_create", name="MCP fill", kind="fill")
    await call("ap_layer_update", name="MCP fill", visible=False, opacity=0.6, blending=2)
    await call("ap_layer_delete", name="MCP fill")
    await call("ap_undo")
    restored = next(x for x in (await call("ap_layer_list"))["layers"] if x["name"] == "MCP fill")
    assert restored["fill"] and not restored["visible"] and restored["blending"] == 2
    assert abs(restored["opacity"] - 0.6) < 1e-5
    await call("ap_capture_viewport", path="D:/Projects/armorpaint-mcp/work/bridge-check.png", width=1280, height=720, include_image=False)
    assert Path("D:/Projects/armorpaint-mcp/work/bridge-check.png").stat().st_size > 1000
    await call("ap_project_new")
    print("Live layer, mask, group, native undo/redo, and viewport checks passed.")

asyncio.run(main())
