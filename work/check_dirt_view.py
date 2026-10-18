import asyncio
import json
from pathlib import Path
import numpy as np
from PIL import Image
from import_jens import ap

async def main():
    out=Path('C:/Projects/DigitalJens-extracted/dirt_mask_example')
    info=json.loads((out/'generator.json').read_text())
    print('Comparison image delta:',float(np.abs(np.asarray(Image.open(out/'less_dirt.png'),dtype=float)-np.asarray(Image.open(out/'more_dirt.png'),dtype=float)).mean()))
    await ap('ap_get_context')
    await ap('ap_mask_generator_set',id=info['id'],parameter='Level',value=0)
    await asyncio.sleep(1)
    await ap('ap_capture_viewport',path=str(out/'view_zero.png'),width=900,height=1000,include_image=False)
    await ap('ap_mask_generator_set',id=info['id'],parameter='Level',value=1)
    await asyncio.sleep(1)
    await ap('ap_capture_viewport',path=str(out/'view_one.png'),width=900,height=1000,include_image=False)
    print('Endpoint viewport delta:',float(np.abs(np.asarray(Image.open(out/'view_zero.png'),dtype=float)-np.asarray(Image.open(out/'view_one.png'),dtype=float)).mean()))
    await ap('ap_mask_generator_set',id=info['id'],parameter='Level',value=.55)

asyncio.run(main())
