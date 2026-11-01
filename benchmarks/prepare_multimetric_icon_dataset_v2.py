"""Prepare a label-blind benchmark around four freshly generated icon designs.

The only mask is the binary foreground alpha produced by a fixed neutral-gray
background key. This supports global silhouette/alpha checks, not semantic-part
metrics such as gem color, symmetry, or feature overlap.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks/datasets/icon-multimetric-v2"
RAW = DATA / "generated-contact-sheet.png"
SIZE = 128
KINDS = ("potion", "owl-mask", "compass", "beetle")
CONDITIONS = ("normal", "center", "margin", "palette", "component", "compound")
RULES = {"normal": [], "center": ["GEOMETRY-001"], "margin": ["GEOMETRY-001", "GEOMETRY-002"],
         "palette": ["COLOR-001"], "component": ["TOPOLOGY-001", "CHARACTER-002"],
         "compound": ["GEOMETRY-001", "COLOR-001", "TOPOLOGY-001", "CHARACTER-002"]}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGBA")).copy()


def make_icon_crops() -> None:
    sheet = Image.open(RAW).convert("RGB")
    w, h = sheet.size
    for i, kind in enumerate(KINDS):
        x0, x1 = (0, w // 2) if i % 2 == 0 else (w // 2, w)
        y0, y1 = (0, h // 2) if i < 2 else (h // 2, h)
        crop = sheet.crop((x0, y0, x1, y1))
        src = np.asarray(crop).astype(np.int16)
        corners = np.stack([src[0, 0], src[0, -1], src[-1, 0], src[-1, -1]])
        bg = np.median(corners, axis=0)
        distance = np.sqrt(np.square(src - bg).sum(axis=2))
        # A deterministic key only; retain edges with a short alpha ramp.
        alpha = np.clip((distance - 10.0) * 255.0 / 28.0, 0, 255).astype(np.uint8)
        ys, xs = np.where(alpha > 0)
        if not len(xs):
            raise ValueError(f"empty keyed icon: {kind}")
        pad = int(min(crop.size) * .04)
        bbox = (max(0, xs.min()-pad), max(0, ys.min()-pad),
                min(crop.width, xs.max()+1+pad), min(crop.height, ys.max()+1+pad))
        fg = np.dstack([src.clip(0, 255).astype(np.uint8), alpha])
        keyed = Image.fromarray(fg, "RGBA").crop(bbox)
        scale = 0.80 * SIZE / max(keyed.size)
        resized = keyed.resize((round(keyed.width*scale), round(keyed.height*scale)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.alpha_composite(resized, ((SIZE-resized.width)//2, (SIZE-resized.height)//2))
        canvas.save(DATA / "clean" / f"{kind}.png", optimize=False)


def alpha_mask(a: np.ndarray) -> np.ndarray:
    return a[:, :, 3] > 0


def centroid_offset(a: np.ndarray) -> float:
    ys, xs = np.where(a[:, :, 3] > 0)
    if not len(xs):
        return 0.0
    weights = a[ys, xs, 3].astype(np.float64)
    cx = np.average(xs + .5, weights=weights); cy = np.average(ys + .5, weights=weights)
    return float(np.hypot(cx-SIZE/2, cy-SIZE/2) / SIZE)


def bbox(a: np.ndarray):
    ys, xs = np.where(a[:, :, 3] > 0)
    if not len(xs): return None
    return int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)


def components(mask: np.ndarray) -> int:
    seen = np.zeros(mask.shape, dtype=bool); h, w = mask.shape; n = 0
    for y, x in zip(*np.where(mask)):
        if seen[y, x]: continue
        n += 1; seen[y, x] = True; stack = [(y, x)]
        while stack:
            cy, cx = stack.pop()
            for yy in range(max(0, cy-1), min(h, cy+2)):
                for xx in range(max(0, cx-1), min(w, cx+2)):
                    if mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True; stack.append((yy, xx))
    return n


def shifted(a: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(a); h, w = a.shape[:2]
    sx0=max(0,-dx); sx1=min(w,w-dx); sy0=max(0,-dy); sy1=min(h,h-dy)
    out[sy0+dy:sy1+dy, sx0+dx:sx1+dx] = a[sy0:sy1, sx0:sx1]
    return out


def mutate(clean: np.ndarray, condition: str) -> np.ndarray:
    a=clean.copy(); box=bbox(a)
    if box is None: raise ValueError("empty clean art")
    x0,y0,x1,y1=box
    if condition in ("center", "compound"):
        a=shifted(a, 0, 8)
    if condition == "margin":
        # Move the silhouette to a 2 px left margin without clipping; this
        # reliably violates the shared 3% margin policy and may also shift its centroid.
        a=shifted(a, 2-x0, 0)
    if condition in ("palette", "compound"):
        # Pick colors absent from this clean source palette; generated art can
        # already contain any fixed RGB values chosen in advance.
        base_colors={tuple(map(int,px[:3])) for px in clean.reshape(-1,4) if px[3]}
        m=a[:,:,3] >= 240; yy,xx=np.where(m)
        if len(xx) < 16: raise ValueError("not enough opaque pixels for palette patch")
        visible=a[:,:,:3][a[:,:,3]>0]
        unique,counts=np.unique(visible,axis=0,return_counts=True)
        repeated={tuple(map(int,c)) for c,n in zip(unique,counts) if n>1}
        keep=[k for k,(y,x) in enumerate(zip(yy,xx)) if tuple(map(int,a[y,x,:3])) in repeated]
        if len(keep)<16: raise ValueError("not enough repeated-color opaque pixels for palette patch")
        new_colors: list[tuple[int,int,int]]=[]; candidate=0
        while len(new_colors) < 16:
            color=((candidate*17+251)%256,(candidate*67+3)%256,(candidate*113+11)%256)
            if color not in base_colors and color not in new_colors: new_colors.append(color)
            candidate += 1
        # A small, visibly foreign patch guarantees new exact RGB values even
        # when a generated illustration already has thousands of palette colors.
        for j,color in enumerate(new_colors):
            k=keep[j]
            a[yy[k],xx[k],:3]=np.asarray(color,dtype=np.uint8)
    if condition in ("component", "compound"):
        m=alpha_mask(a); ys,xs=np.where(m)
        candidates=[(x,y) for x,y in ((x0-3,y0-3),(x1+2,y0-3),(x0-3,y1+2),(x1+2,y1+2))
                    if 1<=x<SIZE-1 and 1<=y<SIZE-1 and not m[max(0,y-1):y+2,max(0,x-1):x+2].any()]
        if not candidates: raise ValueError(f"no detached-speck location {condition}")
        x,y=candidates[0]; speck_rgb=a[ys[len(xs)//2],xs[len(xs)//2],:3].copy(); a[y,x,:3]=speck_rgb; a[y,x,3]=255
    return a


def policy(asset_hash: str, threshold: dict, mask_path: str) -> dict:
    return {"schema_version":"0.5", "asset":{"path":"asset.png","format":"png","sha256":asset_hash},
        "constraints":{"max_normalized_centroid_offset":threshold["max_centroid"],
                       "min_margin_ratio":0.03,"max_palette_colors":threshold["max_palette"]},
        "features":[{"id":"foreground","role":"foreground","geometry":{"type":"mask","path":mask_path},
                      "properties":{"max_connected_components":threshold["components"],
                                    "max_silhouette_components":threshold["components"],
                                    "min_occupancy_ratio":0.05}}]}


def main() -> None:
    (DATA/"clean").mkdir(parents=True,exist_ok=True); (DATA/"faulty").mkdir(parents=True,exist_ok=True)
    if not RAW.is_file(): raise FileNotFoundError(f"Copy generated image sheet to {RAW}")
    make_icon_crops()
    cases=[]
    for kind in KINDS:
        clean_path=DATA/"clean"/f"{kind}.png"; clean=rgba(clean_path); box=bbox(clean); assert box
        colors={tuple(px[:3]) for px in clean.reshape(-1,4) if px[3]}
        thresholds={"max_centroid":centroid_offset(clean)+0.02,"max_palette":len(colors),"components":components(alpha_mask(clean))}
        for condition in CONDITIONS:
            case_id=f"{kind}-{condition}"
            a=mutate(clean,condition)
            input_path=DATA/"faulty"/f"{case_id}.png"; Image.fromarray(a,"RGBA").save(input_path,optimize=False)
            mask=Image.fromarray((a[:,:,3]>0).astype(np.uint8)*255,"L")
            mp=DATA/"faulty"/f"{case_id}-silhouette.png"; mask.save(mp,optimize=False)
            cases.append({"case_id":case_id,"kind":kind,"condition":condition,"expected_rules":RULES[condition],
                "input_sha256":sha(input_path),"clean_sha256":sha(clean_path),"clean_asset":f"clean/{kind}.png",
                "faulty_asset":f"faulty/{case_id}.png","mask":"faulty/"+mp.name,"thresholds":thresholds})
    random.Random(20261031).shuffle(cases)
    (DATA/"dataset.json").write_text(json.dumps({"version":"2.0.0","source":"image_gen four-up icon sheet",
        "source_prompt":"A four quadrant sheet of a teal potion, blue owl mask, violet crystal compass and orange mechanical beetle on flat grey.",
        "mask_method":"deterministic neutral-grey color key to binary foreground; no semantic-part masks",
        "cases":cases},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"cases":len(cases),"conditions":CONDITIONS,"source":str(RAW)},indent=2))


if __name__=="__main__": main()
