import asyncio
from pathlib import Path
from import_jens import ap

async def main():
    await ap('ap_get_context')
    await ap('ap_layer_list')
    await ap('ap_material_get_active')
    await ap('ap_node_list')
    out=Path('C:/Projects/DigitalJens-extracted/diagnostic_export')
    out.mkdir(exist_ok=True)
    await ap('ap_export_pbr',directory=str(out),name='diagnostic')

asyncio.run(main())
