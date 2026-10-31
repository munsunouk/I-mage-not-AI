from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

review=Path(__file__).parent
repo=Path(r'E:\I-mage-not-AI')
source=repo/'artifacts'/'skill-segmentation-test'/'fox-forest.png'
candidate_root=repo/'artifacts'/'xal-fox-candidates-01'
raw_meta_path=candidate_root/'candidates'/'fox-forest.png.candidates.json'
raw_meta=json.loads(raw_meta_path.read_text(encoding='utf-8'))
source_copy=review/'source'/'fox-forest.png'
shutil.copy2(source,source_copy)
with Image.open(source_copy) as im:
    width,height=im.size
    source_rgb=np.asarray(im.convert('RGB'))

def load_candidate(candidate_id: str) -> np.ndarray:
    path=candidate_root/'masks'/'fox-forest.png'/f'{candidate_id}.png'
    with Image.open(path) as im:
        array=np.asarray(im.convert('L'))
    if array.shape != (height,width):
        raise ValueError(f'{candidate_id} mask dimensions differ from source')
    return array > 0

raw={c['id']:c for c in raw_meta['candidates']}
char=load_candidate('candidate-0001')
head=load_candidate('candidate-0003') & char
tail=load_candidate('candidate-0006') & char
scarf=load_candidate('candidate-0007') & char
flower=load_candidate('candidate-0008')
mushroom=load_candidate('candidate-0009')
sky=load_candidate('candidate-0011')
mountains=load_candidate('candidate-0013')
trunk=load_candidate('candidate-0019')
foliage=load_candidate('candidate-0020') & ~flower & ~trunk
conifer=load_candidate('candidate-0022')
body=char & ~head & ~tail & ~scarf
body_labels,body_count=ndimage.label(body,structure=np.ones((3,3),dtype=np.uint8))
if body_count:
    body_sizes=np.bincount(body_labels.ravel()); body_sizes[0]=0
    body=body_labels==int(np.argmax(body_sizes))
features=[
    ('fox_character','character',char,None,'candidate-0001','accepted','Whole fox silhouette; XAL contour visually follows the visible character.'),
    ('fox_head','head',head,'fox_character','candidate-0003','accepted_refined','Head and ears. Mask clipped to the whole-character silhouette; cheek-to-scarf boundary remains approximate.'),
    ('fox_body','body',body,'fox_character',None,'derived_from_approved_candidates','Computed as whole fox minus approved head, tail, and scarf masks, then limited to the largest 8-connected component to remove subtraction artifacts.'),
    ('fox_tail','tail',tail,'fox_character','candidate-0006','accepted_refined','Tail candidate clipped to the whole-character silhouette; attachment boundary remains approximate.'),
    ('fox_scarf','clothing',scarf,'fox_character','candidate-0007','accepted_refined','Teal scarf and hanging ends; clipped to whole-character silhouette.'),
    ('pink_flower','flower',flower,None,'candidate-0008','accepted','Flower petals and center align with the visible blossom.'),
    ('blue_mushroom','mushroom',mushroom,None,'candidate-0009','accepted','Cap and stem align with the blue mushroom at lower right.'),
    ('sky','background_region',sky,None,'candidate-0011','accepted','Sky and clouds above the mountain ridge; coarse edge around overlapping foreground branches.'),
    ('mountain_range','background_region',mountains,None,'candidate-0013','accepted','Visible distant mountain range; lower boundary against water/trees is coarse.'),
    ('left_tree_trunk','tree_trunk',trunk,None,'candidate-0019','accepted','Main left tree trunk and branching portions; preserves the candidate extent.'),
    ('left_foreground_foliage','vegetation',foliage,None,'candidate-0020','accepted_refined','Left foreground foliage with flower and tree-trunk pixels removed using their separately approved masks.'),
    ('right_background_conifer','vegetation',conifer,None,'candidate-0022','accepted','Right-edge conifer silhouette; edge-clipped by the source canvas.'),
]
mask_dir=review/'masks'; evidence=[]; manifest_features=[]
for feature_id,role,mask,parent,candidate_id,decision,note in features:
    out=mask_dir/f'{feature_id}.png'
    Image.fromarray((mask.astype(np.uint8)*255),mode='L').save(out)
    candidate=raw.get(candidate_id) if candidate_id else None
    manifest_feature={
        'id':feature_id,'role':role,'geometry':{'type':'mask','path':f'masks/{feature_id}.png'},
        'provenance':{'origin':'agent_inferred','review_decision':decision,'review_note':note,
            'candidate_id':candidate_id,
            'candidate_stage':'../xal-fox-candidates-01/candidates/fox-forest.png.candidates.json',
            'model_id':raw_meta['inference']['model_id'],
            'model_config':raw_meta['inference']['config'],
            'prompt':candidate.get('prompt') if candidate else None,
            'xal_label':candidate.get('label') if candidate else None,
            'xal_score':candidate.get('score') if candidate else None,
            'generation_prompt':'unavailable_in_existing_artifacts'}
    }
    if parent: manifest_feature['parent_id']=parent
    if feature_id=='fox_body':
        manifest_feature['provenance']['source_candidate_ids']=['candidate-0001','candidate-0003','candidate-0006','candidate-0007']
    manifest_features.append(manifest_feature)
    evidence.append({'feature_id':feature_id,'decision':decision,'candidate_id':candidate_id,
        'prompt':candidate.get('prompt') if candidate else None,'label':candidate.get('label') if candidate else None,
        'score':candidate.get('score') if candidate else None,'final_mask':f'masks/{feature_id}.png',
        'mask_pixels':int(np.count_nonzero(mask)),'coverage_ratio':float(np.count_nonzero(mask)/(width*height)),
        'note':note})

source_hash=hashlib.sha256(source_copy.read_bytes()).hexdigest()
manifest={
 'schema_version':'0.5',
 'asset':{'path':'source/fox-forest.png','format':'png','sha256':source_hash},
 'intent':{'kind':'game_asset','style':'storybook','purpose':'Review X-AnyLabeling feature proposals on the existing fox forest image','origin':'agent_inference',
    'generation_prompt':None,'generation_prompt_note':'The exact image-generation prompt was not present in the existing repository artifacts.'},
 'features':manifest_features,
 'constraints':{},
}
(review/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

decisions={
 'schema':'xanylabeling.codex-review.v1','status':'reviewed_features_only','source_sha256':source_hash,
 'source_image':'source/fox-forest.png','generation_prompt':None,
 'generation_prompt_note':'Not found in repository artifacts; feature inventory was drafted from the unchanged image and the prior segmentation-trial notes.',
 'candidate_metadata':'../xal-fox-candidates-01/candidates/fox-forest.png.candidates.json',
 'features':evidence,
 'rejected_candidates':[
   {'candidate_id':'candidate-0002','reason':'Duplicate full-character mask returned for the fox-head prompt; candidate-0003 isolates the head.'},
   {'candidate_id':'candidate-0004','reason':'Duplicate full-character mask returned for the fox-body prompt; body was derived by subtracting reviewed parts.'},
   {'candidate_id':'candidate-0005','reason':'Duplicate full-character mask returned for the fox-tail prompt; candidate-0006 isolates the tail.'},
   {'candidate_id':'candidate-0010','reason':'False positive: whole fox returned for the blue-mushroom prompt.'},
   {'candidate_id':'candidate-0012','reason':'Duplicate sky region; candidate-0011 retained.'},
   {'candidate_id':'candidate-0014','reason':'Duplicate/fragmentary mountain proposal; candidate-0013 retained as the clearest range extent.'},
   {'candidate_id':'candidate-0015','reason':'Duplicate/fragmentary mountain proposal; candidate-0013 retained as the clearest range extent.'},
   {'candidate_id':'candidate-0016','reason':'Duplicate/fragmentary mountain proposal; candidate-0013 retained as the clearest range extent.'},
   {'candidate_id':'candidate-0017','reason':'Duplicate/fragmentary mountain proposal; candidate-0013 retained as the clearest range extent.'},
   {'candidate_id':'candidate-0018','reason':'Small branch fragment; candidate-0019 is the more complete left tree/trunk proposal.'},
   {'candidate_id':'candidate-0021','reason':'Tiny foliage fragment, not a useful standalone feature.'},
   {'candidate_id':'candidate-0023','reason':'Tiny foliage fragment, not a useful standalone feature.'},
 ],
 'unresolved_boundaries':['Fox head-to-scarf and torso-to-tail attachment pixels are approximate.','Mountain lower edge is a coarse separation from the lake and distant forest.','The foliage mask is a broad candidate region, not individual leaves.','The right conifer mask touches the image border.']
}
(review/'review-decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(review/'generation-context.md').write_text(
 '# Source and generation context\n\n'
 '- Source copied byte-for-byte from `../skill-segmentation-test/fox-forest.png`; SHA-256 is recorded in `manifest.json`.\n'
 '- The exact image-generation prompt was not found in the repository artifacts.\n'
 '- Existing trial notes described a storybook fox with head/body/tail/scarf, pink flower, blue mushroom, and a coarse distant sky/mountain region.\n'
 '- Candidate prompts used for this XAL run are recorded in the candidate metadata JSON.\n',encoding='utf-8')

# Render one Codex-approved feature outline overlay for visual audit.
colors=[(255,30,30),(40,130,255),(0,200,255),(255,150,0),(0,255,100),(255,0,200),(0,255,255),(230,220,0),(255,100,0),(180,80,255),(0,180,120),(240,60,100)]
canvas=Image.fromarray(source_rgb.copy()); draw=ImageDraw.Draw(canvas)
for (feature_id,role,mask,*rest),color in zip(features,colors):
    mask_im=Image.fromarray((mask.astype(np.uint8)*255),mode='L')
    contour=mask_im.filter(ImageFilter.MaxFilter(3)).point(lambda v:255 if v else 0)
    inner=mask_im.filter(ImageFilter.MinFilter(3)).point(lambda v:255 if v else 0)
    edge=np.asarray(contour)>0; inside=np.asarray(inner)>0; outline=edge & ~inside
    arr=np.asarray(canvas).copy(); arr[outline]=color; canvas=Image.fromarray(arr)
font_path=Path(r'C:\Windows\Fonts\arial.ttf')
font=ImageFont.truetype(str(font_path),22) if font_path.exists() else ImageFont.load_default()
ImageDraw.Draw(canvas).text((16,14),'Codex-reviewed XAL feature boundaries (colored outlines)',font=font,fill='white',stroke_width=2,stroke_fill='black')
canvas.save(review/'approved-feature-overlay.jpg',quality=95)
print(json.dumps({'source_sha256':source_hash,'size':[width,height],'features':len(features),'masks':len(list(mask_dir.glob('*.png'))),'review_dir':str(review)},ensure_ascii=False))
