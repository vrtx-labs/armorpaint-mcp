"""Compare exported PBR maps on UV-covered texels, without lighting differences."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]/'DigitalJens-extracted'

def image(path,size=2048):
    with Image.open(path) as im:
        return np.asarray(im.convert('RGB').resize((size,size),Image.Resampling.BILINEAR),dtype=np.float32)/255

def main(candidate,output):
    with np.load(ROOT/'native_mesh_maps_visible/mesh_maps.npz') as maps:
        valid=maps['coverage']>.5
        native=maps['world_space_normal']*2-1
    original=image(ROOT/'mesh_maps/world_space_normal.png')*2-1
    alignment={}
    for name,array in [('identity',original),('vertical_flip',original[::-1])]:
        cosine=np.sum(native*array,axis=-1)/np.maximum(np.linalg.norm(native,axis=-1)*np.linalg.norm(array,axis=-1),1e-6)
        alignment[name]=float(cosine[valid].mean())
    report={'covered_pixels':int(valid.sum()),'world_normal_alignment':alignment,'candidate':str(candidate),'channels':{},'bake_ranges':{}}
    for name in ('curvature','ambient_occlusion','thickness'):
        expected=image(ROOT/'mesh_maps'/f'{name}.png')[:,:,0][valid]
        actual=image(ROOT/'native_mesh_maps_visible'/f'{name}.png')[:,:,0][valid]
        report['bake_ranges'][name]={'painter_mean':float(expected.mean()),'painter_std':float(expected.std()),
                                   'native_mean':float(actual.mean()),'native_std':float(actual.std())}
    for channel,suffix in [('base_color','Base_Color'),('roughness','Roughness'),('metallic','Metallic')]:
        expected=image(ROOT.parent/'DigitalJens'/f'jens_{suffix}.png')
        path=candidate/f'{channel}.png'
        if not path.exists():
            path=candidate/f'diagnostic_{dict(base_color="BaseColor",roughness="Roughness",metallic="Metallic")[channel]}.png'
        actual=image(path)
        error=np.abs(expected-actual)[valid]
        report['channels'][channel]={'mean_absolute_error':float(error.mean()),'rmse':float(np.sqrt((error**2).mean())),
                                    'within_1_byte':float((error<=1.01/255).mean())}
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('candidate',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    main(args.candidate,args.output)
