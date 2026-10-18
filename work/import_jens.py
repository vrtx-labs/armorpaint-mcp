import asyncio
import json
import os
from pathlib import Path
os.environ.setdefault('ARMORPAINT_DIR', str(Path(__file__).resolve().parents[2] / 'armorpaint/paint/build/out'))
from armorpaint_mcp.server import call_tool

async def ap(tool, **args):
    result = await call_tool(tool, args)
    payload = json.loads(next(v.text for v in result if v.type == 'text'))
    if not payload.get('ok'):
        raise RuntimeError(payload)
    print(tool, str(payload)[:500])
    return payload.get('result', payload)

async def main():
    await ap('ap_import_asset', path='C:/Projects/DigitalJens-extracted/DigitalJens.obj')
    await ap('ap_get_main_object')
    await ap('ap_capture_viewport', path='C:/Projects/DigitalJens-extracted/mesh_preview.png', width=900, height=1000, include_image=False)

if __name__ == '__main__':
    asyncio.run(main())
