from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).parent
source_path=Path(r'E:\I-mage-not-AI\artifacts\skill-segmentation-test\fox-forest.png')
meta=json.loads((root/'candidates'/'fox-forest.png.candidates.json').read_text(encoding='utf-8'))
source=Image.open(source_path).convert('RGB')
mask_root=root/'masks'/'fox-forest.png'
font_path=Path(r'C:\Windows\Fonts\arial.ttf')
font=ImageFont.truetype(str(font_path),18) if font_path.exists() else ImageFont.load_default()
small_font=ImageFont.truetype(str(font_path),14) if font_path.exists() else ImageFont.load_default()
card_w,card_h=400,330
cols,per_page=4,12
cands=meta['candidates']
for page,start in enumerate(range(0,len(cands),per_page),1):
    subset=cands[start:start+per_page]
    rows=(len(subset)+cols-1)//cols
    sheet=Image.new('RGB',(cols*card_w,rows*card_h),(248,248,248))
    draw=ImageDraw.Draw(sheet)
    for i,c in enumerate(subset):
        x=(i%cols)*card_w; y=(i//cols)*card_h
        mask=Image.open(mask_root/f"{c['id']}.png").convert('L')
        thumb=source.copy(); thumb.thumbnail((card_w-8,card_h-64))
        mthumb=mask.resize(thumb.size,Image.Resampling.NEAREST)
        overlay=Image.new('RGB',thumb.size,(255,40,70))
        alpha=mthumb.point(lambda v: 118 if v else 0)
        thumb=Image.composite(overlay,thumb,alpha)
        sheet.paste(thumb,(x+4,y+44))
        prompt=c.get('prompt') or ''
        label=c.get('label') or ''
        score=c.get('score')
        draw.text((x+6,y+3),f"{c['id']} | {label} | score={score:.3f}" if score is not None else f"{c['id']} | {label}",fill=(0,0,0),font=font)
        draw.text((x+6,y+24),f"prompt: {prompt}",fill=(60,60,60),font=small_font)
        draw.rectangle((x,y,x+card_w-1,y+card_h-1),outline=(160,160,160),width=1)
    out=root/f'contact-sheet-{page:02d}.jpg'
    sheet.save(out,quality=90)
    print(out)
print('candidate summary:')
for c in cands:
    mask=Image.open(mask_root/f"{c['id']}.png").convert('L')
    import numpy as np
    a=np.asarray(mask)
    print(f"{c['id']}\tprompt={c.get('prompt')}\tlabel={c.get('label')}\tscore={c.get('score')}\tcoverage={np.count_nonzero(a)/a.size:.4f}")
