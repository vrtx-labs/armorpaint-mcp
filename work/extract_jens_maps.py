"""Export embedded float mesh maps losslessly to NumPy, plus portable PNGs."""
import json
import re
from pathlib import Path
import h5py
import lz4.block
import numpy as np
from PIL import Image
from qt_resources import QtReader

ROOT = Path(__file__).resolve().parent
doc = json.loads((ROOT / 'digitaljens_reference/datasets/paint/document.json').read_text())
out = ROOT.parents[1] / 'DigitalJens-extracted'
out.mkdir(exist_ok=True)
maps = out / 'mesh_maps'
maps.mkdir(exist_ok=True)
aliases = {0: 'id', 1: 'ambient_occlusion', 2: 'curvature', 3: 'world_space_normal', 4: 'position', 5: 'thickness'}
material = doc['materials'][0]
sources = [(aliases[m['usage']], m['urlToBitmapRes']) for m in material['additionalMaps']]
sources.append(('normal', material['normalMapBitmap']['urlToBitmapRes']))
arrays = {}
with h5py.File(ROOT / 'digitaljens_reference/DigitalJens.spp', 'r') as project:
    for name, url in sources:
        version = url.split('?version=')[1]
        raw = project['resources/' + version][()].tobytes()
        reader = QtReader(raw)
        meta = reader.mapping()
        pixels = raw[reader.pos:]
        if meta['compression'] == 'lz4':
            pixels = lz4.block.decompress(pixels, uncompressed_size=meta['dataSizeRaw'])
        channels = 4 if meta['format'] == 7 else 1
        array = np.frombuffer(pixels, dtype='<f4').reshape(meta['height'], meta['width'], channels)
        if not np.isfinite(array).all():
            raise ValueError(f'Non-finite {name}')
        arrays[name] = array
        image = np.rint(np.clip(array, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(image[:, :, :3] if channels == 4 else image[:, :, 0]).save(maps / f'{name}.png')
        print(name, array.shape, float(array.min()), float(array.max()))
    for key in ('1', '2', '128', '8192'):
        raw = project['texture-cache/jens/' + key][()].tobytes()
        reader = QtReader(raw)
        meta = reader.mapping()
        compressed_size = reader.number('I')
        decoded = lz4.block.decompress(raw[reader.pos:reader.pos+compressed_size], uncompressed_size=meta['bufferSize'])
        name = {'1':'base_color', '2':'height', '128':'roughness', '8192':'metallic'}[key]
        reference = out / 'painter_reference_textures'
        reference.mkdir(exist_ok=True)
        if key == '1':
            image = np.frombuffer(decoded, np.uint8).reshape(2048,2048,4)[::-1,:,:3]
        elif key == '2':
            values = np.frombuffer(decoded, '<f2').reshape(2048,2048,2)[::-1,:,0].astype(np.float32)
            print('CACHE height range', float(values.min()), float(values.max()))
            np.save(reference / 'height.npy', values)
            image = np.rint(np.clip(values, 0, 1)*255).astype(np.uint8)
        else:
            image = np.frombuffer(decoded, np.uint8).reshape(2048,2048,2)[::-1,:,0]
        Image.fromarray(image).save(reference / f'{name}.png')
np.savez_compressed(maps / 'mesh_maps.npz', **arrays)

def walk(v):
    if isinstance(v, dict):
        yield v
        for child in v.values():
            yield from walk(child)
    elif isinstance(v, list):
        for child in v:
            yield from walk(child)

machinery = next(v for v in walk(doc) if v.get('label') == 'Machinery' and v.get('_type') == 'DataLayerGroup')
(out / 'machinery_painter_stack.json').write_text(json.dumps(machinery, indent=2), encoding='utf-8')
layers = []
for v in walk(machinery):
    if v.get('_type') not in ('DataLayerGroup', 'DataLayerColor'):
        continue
    layer = {'name':v['label'], 'kind':v['_type'], 'enabled':v['enabled'], 'generators':[], 'uniforms':[]}
    # Each layer's own actions/mask actions, excluding child layers.
    for action in [v.get('actions'), v.get('maskActions')]:
        for item in walk(action):
            if item.get('_type') == 'DataProcedural':
                layer['generators'].append({'resource':item.get('urlToSubstance') or item.get('urlToResource'),
                    'parameters':{p['identifier']:p['value'] for p in item.get('tweaks', []) if 'value' in p}})
            if item.get('_type') == 'DataSourceUniform':
                layer['uniforms'].append(item)
    layers.append(layer)
(out / 'machinery_summary.json').write_text(json.dumps(layers, indent=2), encoding='utf-8')
obj = out / 'DigitalJens.obj'
data = obj.read_bytes()
print('OBJ bytes:', len(data), 'NULs:', data.count(b'\0'), 'header:', repr(data[:160]))
print('Recovered Machinery:', ', '.join(layer['name'] for layer in layers))
