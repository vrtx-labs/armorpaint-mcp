import asyncio
import json
from pathlib import Path
from PIL import Image,ImageDraw
from import_jens import ap

async def main():
    out=Path('C:/Projects/DigitalJens-extracted/dirt_mask_example')
    generator=json.loads((out/'generator.json').read_text())
    await ap('ap_material_select',name=generator['material'])
    for label,level in [('less_dirt',.2),('more_dirt',.9)]:
        await ap('ap_mask_generator_set',id=generator['id'],parameter='Level',value=level)
        await asyncio.sleep(.5)
        await ap('ap_capture_viewport',path=str(out/f'{label}.png'),width=900,height=1000,include_image=False)
    await ap('ap_mask_generator_set',id=generator['id'],parameter='Level',value=.55)
    canvas=Image.new('RGB',(1800,1045),(28,28,28))
    draw=ImageDraw.Draw(canvas)
    for index,(label,title) in enumerate([('less_dirt','Less dirt - Level 0.20'),('more_dirt','More dirt - Level 0.90')]):
        with Image.open(out/f'{label}.png') as image:
            canvas.paste(image,(index*900,45))
        draw.text((index*900+30,15),title,fill='white')
    canvas.save(out/'live_dirt_comparison.png')

asyncio.run(main())
