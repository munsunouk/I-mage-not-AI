from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json, numpy as np
root=Path(__file__).parent
src=np.asarray(Image.open(Path(r'E:\I-mage-not-AI\artifacts\skill-segmentation-test\fox-forest.png')).convert('RGB'),dtype=np.uint8)
meta=json.loads((root/'candidates'/'fox-forest.png.candidates.json').read_text(encoding='utf-8'))
maskdir=root/'masks'/'fox-forest.png'; out=root/'inspection-overlays'; out.mkdir(exist_ok=True)
fp=Path(r'C:\Windows\Fonts\arial.ttf'); font=ImageFont.truetype(str(fp),22) if fp.exists() else ImageFont.load_default()
for c in meta['candidates']:
 if c['id'] not in {'candidate-0003','candidate-0006','candidate-0007','candidate-0008','candidate-0009','candidate-0011','candidate-0013','candidate-0019','candidate-0020','candidate-0022'}: continue
 m=np.asarray(Image.open(maskdir/f"{c['id']}.png").convert('L'))>0
 result=src.copy(); result[m]=(0.42*result[m]+0.58*np.array([255,20,50])).astype(np.uint8)
 im=Image.fromarray(result); d=ImageDraw.Draw(im); d.text((16,12),f"{c['id']} | {c['prompt']} | {c['label']} | score={c.get('score'):.3f}",font=font,fill='white',stroke_width=2,stroke_fill='black')
 im.save(out/f"{c['id']}.jpg",quality=95)

