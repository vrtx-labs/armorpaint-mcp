import asyncio
from import_jens import ap

async def main():
    await ap('ap_get_context')
    obj=await ap('ap_get_main_object')
    await ap('ap_object_set_visible',name=obj['name'],visible=True)
    await ap('ap_set_display_channel',mode='lit')
    await ap('ap_capture_viewport',path='C:/Projects/DigitalJens-extracted/current_view.png',width=1000,height=1000,include_image=False)

asyncio.run(main())
