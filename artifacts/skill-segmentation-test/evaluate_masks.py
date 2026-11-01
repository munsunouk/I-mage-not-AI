"""Check mask integrity and summarize geometry without claiming semantic accuracy."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).parent
IMAGE_SIZE = Image.open(ROOT / "fox-forest.png").size
mask_files = sorted((ROOT / "masks").glob("*.png"))
arrays: dict[str, np.ndarray] = {}
report: dict[str, object] = {"source_size": list(IMAGE_SIZE), "masks": {}, "pairwise_overlap": []}

for path in mask_files:
    image = Image.open(path).convert("L")
    data = np.asarray(image)
    binary = np.isin(data, [0, 255]).all()
    foreground = data > 0
    labels, components = ndimage.label(foreground)
    ys, xs = np.where(foreground)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None
    arrays[path.stem] = foreground
    report["masks"][path.stem] = {
        "size": list(image.size),
        "same_size_as_source": image.size == IMAGE_SIZE,
        "binary_0_255": bool(binary and set(np.unique(data).tolist()).issubset({0, 255})),
        "foreground_pixels": int(foreground.sum()),
        "occupancy": float(foreground.mean()),
        "bbox_xyxy": bbox,
        "connected_components_8": int(components),
    }

for (name_a, mask_a), (name_b, mask_b) in itertools.combinations(arrays.items(), 2):
    intersection = int(np.logical_and(mask_a, mask_b).sum())
    if not intersection:
        continue
    smaller = min(int(mask_a.sum()), int(mask_b.sum()))
    union = int(np.logical_or(mask_a, mask_b).sum())
    report["pairwise_overlap"].append({
        "a": name_a,
        "b": name_b,
        "intersection_pixels": intersection,
        "fraction_of_smaller_mask": intersection / smaller,
        "iou": intersection / union,
    })

(ROOT / "mask-integrity.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
