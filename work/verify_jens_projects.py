"""Verify saved visibility/stage membership and material assets on reopen."""
import asyncio
from pathlib import Path
from import_jens import ap

async def main():
    root=Path('C:/Projects/DigitalJens-extracted')
    for mode in ('native','procedural','reference'):
        path=root/f'DigitalJens_{mode}.arm'
        await ap('ap_project_open',path=str(path))
        obj=await ap('ap_get_main_object')
        await ap('ap_object_set_visible',name=obj['name'],visible=True)
        await ap('ap_project_save')
        await asyncio.sleep(3)
        await ap('ap_project_open',path=str(path))
        obj=await ap('ap_get_main_object')
        assert obj['visible'],f'{mode}: object visibility was not retained on reopen'
        assets=await ap('ap_project_list_texture_assets')
        assert assets['count']>=5
        layers=await ap('ap_layer_list')
        assert layers['total']==(1 if mode=='reference' else 8)
        await ap('ap_capture_viewport',path=str(root/f'{mode}_preview.png'),width=1100,height=1100,include_image=False)
        print('Verified saved project:',path)

asyncio.run(main())
