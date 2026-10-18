"""Build the recovered Painter reference or the editable procedural reconstruction."""
import argparse
import asyncio
import json
from pathlib import Path
from PIL import Image
import numpy as np
from import_jens import ap
from armorpaint_mcp.material_stack import apply_manifest

ROOT = Path(__file__).resolve().parents[2] / 'DigitalJens-extracted'

async def main(mode):
    if mode=='reference':
        folder = ROOT / 'painter_reference_textures'
        supplied = ROOT.parent/'DigitalJens'
        normal_source = supplied/'jens_Normal_DirectX.png' if supplied.exists() else ROOT/'mesh_maps/normal.png'
        n = np.asarray(Image.open(normal_source),dtype=np.float32)/255
        n[:,:,1]=1-n[:,:,1]
        Image.fromarray(np.rint(n*255).astype('uint8')).save(folder/'normal.png')
        height = np.load(folder/'height.npy')
        # Keep the recovered signed values in NPY; normalize to AP's neutral 0.5.
        Image.fromarray(np.rint(np.clip(height+.5,0,1)*255).astype('uint8')).save(folder/'height_armorpaint.png')
        data = {'schema':1,'size':2048,'layers':[{'name':'Recovered Painter appearance','channels':{
            key:str(folder/f'{key}.png') for key in ('base_color','roughness','metallic')}}],
            'normal':str(folder/'normal.png'),'ambient_occlusion':str(ROOT/'mesh_maps/ambient_occlusion.png')}
        data['layers'][0]['channels']['height']=str(folder/'height_armorpaint.png')
        if supplied.exists():
            data['layers'][0]['channels'].update({k:str(supplied/f'jens_{suffix}.png')
                for k,suffix in [('base_color','Base_Color'),('roughness','Roughness'),('metallic','Metallic')]})
            # The supplied normal already includes Painter's height/normal blending.
            data['layers'][0]['channels'].pop('height')
        manifest = folder/'reference.json'
        manifest.write_text(json.dumps(data,indent=2),encoding='utf-8')
    else:
        manifest = ROOT/('machinery_native/machinery.json' if mode=='native' else 'machinery_procedural/machinery.json')
    await ap('ap_project_new')
    await ap('ap_import_asset',path=str(ROOT/'DigitalJens.obj'))
    print(await ap('ap_smart_material_apply',manifest=str(manifest),prefix='Machinery' if mode!='reference' else 'Painter Reference'))
    await ap('ap_layer_delete',name='Layer 1')
    await ap('ap_view_set',view='front')
    obj = await ap('ap_get_main_object')
    await ap('ap_object_set_visible',name=obj['name'],visible=True)
    await ap('ap_set_config',rp_grain=0,rp_bloom=0)
    project = ROOT/f'DigitalJens_{mode}.arm'
    await ap('ap_pack_assets')
    await ap('ap_project_save_as',path=str(project))
    await asyncio.sleep(4)
    if not project.exists() or project.stat().st_size<100000:
        raise RuntimeError('Project save did not complete')
    await ap('ap_capture_viewport',path=str(ROOT/f'{mode}_preview.png'),width=1100,height=1100,include_image=False)
    print('Saved',project)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['reference','procedural','native','live_masks'])
    asyncio.run(main(parser.parse_args().mode))
