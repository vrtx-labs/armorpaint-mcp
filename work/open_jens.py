import asyncio
import sys
from import_jens import ap

async def main():
    await ap('ap_project_open',path=f'C:/Projects/DigitalJens-extracted/DigitalJens_{sys.argv[1] if len(sys.argv)>1 else "procedural"}.arm')
    obj=await ap('ap_get_main_object')
    await ap('ap_object_set_visible',name=obj['name'],visible=True)

asyncio.run(main())
