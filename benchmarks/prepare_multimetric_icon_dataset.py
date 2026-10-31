"""Build a controlled icon benchmark with source-authored binary feature masks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks/datasets/icon-multimetric-v1"
SIZE = 128
CASES_PER_FAULT = 4
TYPES = ("orb", "shield", "hex", "potion")
FAULTS = ("center", "margin", "color", "components", "symmetry", "overlap")
BODY = ((37, 82, 139), (47, 113, 93), (134, 79, 144), (160, 94, 42))
ACCENT = ((244, 177, 58), (81, 204, 220), (235, 101, 130), (161, 222, 99))
OUTLINE = (36, 31, 48)
RIM = (244, 203, 112)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alpha_centroid(image: Image.Image) -> tuple[float, float]:
    alpha = image.getchannel("A")
    total = sum(alpha.getdata())
    if not total:
        raise ValueError("cannot measure centroid of an empty icon")
    pixels = cast(Any, alpha.load())
    cx = sum((x + .5) * pixels[x, y] for y in range(SIZE) for x in range(SIZE)) / total
    cy = sum((y + .5) * pixels[x, y] for y in range(SIZE) for x in range(SIZE)) / total
    return cx, cy


def alpha_centroid_offset(image: Image.Image) -> float:
    cx, cy = alpha_centroid(image)
    return ((cx - SIZE / 2) ** 2 / SIZE ** 2 + (cy - SIZE / 2) ** 2 / SIZE ** 2) ** .5


def polygon(kind: str) -> list[tuple[int, int]]:
    if kind == "shield":
        return [(27, 22), (101, 22), (106, 40), (98, 90), (64, 108), (30, 90), (22, 40)]
    if kind == "hex":
        return [(43, 22), (85, 22), (106, 43), (106, 85), (85, 106), (43, 106), (22, 85), (22, 43)]
    if kind == "potion":
        return [(49, 21), (79, 21), (79, 42), (94, 55), (102, 96), (91, 107), (37, 107), (26, 96), (34, 55), (49, 42)]
    return []


def draw_body(draw: ImageDraw.ImageDraw, kind: str, fill: tuple[int, int, int]) -> None:
    if kind == "orb":
        draw.ellipse((22, 22, 106, 106), fill=OUTLINE)
        draw.ellipse((27, 27, 101, 101), fill=fill)
        draw.ellipse((34, 34, 94, 94), outline=RIM, width=3)
    else:
        pts = polygon(kind)
        draw.polygon(pts, fill=OUTLINE)
        inner = [(64 + int((x - 64) * .88), 64 + int((y - 64) * .88)) for x, y in pts]
        draw.polygon(inner, fill=fill)
        inset = [(64 + int((x - 64) * .76), 64 + int((y - 64) * .76)) for x, y in pts]
        draw.line(inset + [inset[0]], fill=RIM, width=3, joint="curve")
    # Symmetric, crisp details give every icon several visible layers.
    draw.line((45, 66, 83, 66), fill=RIM, width=3)
    draw.line((64, 48, 64, 84), fill=RIM, width=3)
    draw.ellipse((58, 58, 70, 70), fill=OUTLINE)
    draw.ellipse((61, 61, 67, 67), fill=RIM)


def draw_gem(draw: ImageDraw.ImageDraw, center_x: int, color: tuple[int, int, int]) -> None:
    cy = 43
    draw.ellipse((center_x - 10, cy - 10, center_x + 10, cy + 10), fill=OUTLINE)
    draw.ellipse((center_x - 8, cy - 8, center_x + 8, cy + 8), fill=RIM)
    draw.ellipse((center_x - 6, cy - 6, center_x + 6, cy + 6), fill=color)
    highlight_dx = -3 if center_x < SIZE // 2 else 3
    draw.point((center_x + highlight_dx, cy - 3), fill=(255, 244, 210))


def make_icon(kind: str, variant: int, *, right_x: int = 83,
              color_fault: bool = False, speck: tuple[int, int] | None = None,
              shift_x: int = 0, shift_y: int = 0) -> tuple[Image.Image, dict[str, Image.Image]]:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_body(draw, kind, BODY[variant])
    draw_gem(draw, 44, ACCENT[variant])
    draw_gem(draw, right_x, ACCENT[variant])
    if color_fault:
        # A visible foreign-color fleck inside the precisely known right-gem fill mask.
        draw.rectangle((right_x - 1, 42, right_x + 1, 44), fill=(255, 0, 210))
    if speck is not None:
        draw.point(speck, fill=OUTLINE)

    masks: dict[str, Image.Image] = {}
    whole = image.getchannel("A").point(lambda value: 255 if value else 0)
    masks["silhouette"] = whole
    left = Image.new("L", (SIZE, SIZE), 0)
    right = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(left).ellipse((42, 41, 46, 45), fill=255)
    ImageDraw.Draw(right).ellipse((right_x - 2, 41, right_x + 2, 45), fill=255)
    masks["left-gem"] = left
    masks["right-gem"] = right
    pair = Image.new("L", (SIZE, SIZE), 0)
    pair.paste(255, mask=left)
    pair.paste(255, mask=right)
    masks["gem-pair"] = pair
    if shift_x or shift_y:
        moved = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        moved.alpha_composite(image, (shift_x, shift_y))
        image = moved
        for name, mask in list(masks.items()):
            shifted = Image.new("L", (SIZE, SIZE), 0)
            shifted.paste(mask, (shift_x, shift_y))
            masks[name] = shifted
    return image, masks


def component_count(mask: Image.Image) -> int:
    pixels = cast(Any, mask.load())
    seen: set[tuple[int, int]] = set()
    count = 0
    for y in range(SIZE):
        for x in range(SIZE):
            if not pixels[x, y] or (x, y) in seen:
                continue
            count += 1
            stack = [(x, y)]
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                for yy in range(max(0, cy - 1), min(SIZE, cy + 2)):
                    for xx in range(max(0, cx - 1), min(SIZE, cx + 2)):
                        if pixels[xx, yy] and (xx, yy) not in seen:
                            seen.add((xx, yy)); stack.append((xx, yy))
    return count


def pick_detached_pixel(mask: Image.Image) -> tuple[int, int]:
    px = cast(Any, mask.load())
    bbox = mask.getbbox()
    assert bbox is not None
    candidates = []
    for y in range(bbox[1] + 2, bbox[3] - 2):
        for x in range(bbox[0] + 2, bbox[2] - 2):
            if all(not px[xx, yy] for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)):
                candidates.append((abs(x - SIZE // 2) + abs(y - SIZE // 2), x, y))
    if not candidates:
        raise ValueError(f"no detached in-bbox location for silhouette {bbox}")
    _, x, y = min(candidates)
    return x, y


def write_mask(path: Path, mask: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(path, optimize=False)


def make_policy(case: dict, clean: Image.Image, clean_masks: dict[str, Image.Image],
                input_masks: dict[str, Image.Image]) -> dict:
    clean_alpha = clean.getchannel("A")
    clean_bbox = clean_alpha.getbbox()
    assert clean_bbox is not None
    occupancy = sum(cast(Any,clean_masks["silhouette"].getchannel("L").getdata())) / (255 * SIZE * SIZE)
    colors = {tuple(cast(Any,px)[:3]) for px in cast(Any,clean.convert("RGBA").getdata()) if px[3]}
    clean_components = component_count(clean_masks["silhouette"])
    fault = case["fault"]
    center_limit = alpha_centroid_offset(clean) + (0.01 if fault == "center" else 0.2)
    symmetry_limit = 0.98 if fault == "symmetry" else 0.0
    features = [
        {"id": "icon-silhouette", "role": "foreground", "geometry": {"type": "mask", "path": "masks/silhouette.png"},
         "properties": {"max_connected_components": clean_components,
                        "max_silhouette_components": clean_components,
                        "min_occupancy_ratio": max(0.1, occupancy * 0.7)}},
        {"id": "gem-pair", "role": "detail", "geometry": {"type": "mask", "path": "masks/gem-pair.png"},
         "properties": {"min_symmetry_iou": symmetry_limit}},
        {"id": "left-gem-lab", "role": "detail", "geometry": {"type": "mask", "path": "masks/left-gem.png"},
         "properties": {"max_palette_colors": 1, "palette_bin_size_lab": [20, 20, 20]}},
        {"id": "right-gem-lab", "role": "detail", "geometry": {"type": "mask", "path": "masks/right-gem.png"},
         "properties": {"max_palette_colors": 1, "palette_bin_size_lab": [20, 20, 20]}},
        {"id": "right-gem-exact", "role": "detail", "geometry": {"type": "mask", "path": "masks/right-gem.png"},
         "properties": {"max_palette_colors": 1}},
        {"id": "right-gem-solid", "role": "solid", "geometry": {"type": "mask", "path": "masks/right-gem.png"},
         "properties": {"surface": "solid", "max_channel_range": 0,
                        "max_delta_e00": 0.1, "delta_e_tolerance": 0.1,
                        "reference_rgb": list(ACCENT[case["variant"]])}},
    ]
    return {
        "schema_version": "0.5",
        "asset": {"path": "asset.png", "format": "png", "sha256": case["input_sha256"]},
        "constraints": {"max_normalized_centroid_offset": center_limit,
                        "min_margin_ratio": 0.12,
                        "max_palette_colors": len(colors)},
        "features": features,
        "overlap_constraints": [{"feature_a": "left-gem-lab", "feature_b": "right-gem-lab",
                                 "max_overlap_ratio": 0.0}],
    }


def main() -> None:
    for path in (DATA,):
        path.mkdir(parents=True, exist_ok=True)
    clean_dir, faulty_dir = DATA / "clean", DATA / "faulty"
    clean_dir.mkdir(exist_ok=True); faulty_dir.mkdir(exist_ok=True)
    rows = []
    for fault_index, fault in enumerate(FAULTS):
        for variant in range(CASES_PER_FAULT):
            case_number = fault_index * CASES_PER_FAULT + variant + 1
            case_id = f"multi-{case_number:02d}"
            kind = TYPES[variant]
            clean, clean_masks = make_icon(kind, variant)
            right_x = 83
            color_fault = speck = None
            shift = shift_y = 0
            if fault == "center":
                _, clean_cy = alpha_centroid(clean)
                shift_y = 4 if clean_cy >= SIZE / 2 else -4
            elif fault == "margin": shift = 14
            elif fault == "color": color_fault = True
            elif fault == "components": speck = pick_detached_pixel(clean_masks["silhouette"])
            elif fault == "symmetry": right_x += 10
            elif fault == "overlap": right_x = 44
            faulty, masks = make_icon(kind, variant, right_x=right_x, color_fault=bool(color_fault),
                                      speck=speck, shift_x=shift, shift_y=shift_y)
            clean_path = clean_dir / f"{case_id}.png"
            faulty_path = faulty_dir / f"{case_id}.png"
            clean.save(clean_path, optimize=False); faulty.save(faulty_path, optimize=False)
            case_info = {"case_id": case_id, "fault": fault, "variant": variant,
                         "input_sha256": sha(faulty_path), "clean_sha256": sha(clean_path)}
            in_mask_dir = DATA / "masks" / case_id
            for name, mask in masks.items(): write_mask(in_mask_dir / f"{name}.png", mask)
            case_info["mask_paths"] = {name: (in_mask_dir / f"{name}.png").relative_to(DATA).as_posix()
                                        for name in masks}
            case_info["fault_details"] = {"shift_x": shift, "shift_y": shift_y, "right_gem_center_x": right_x,
                                          "foreign_color_patch": color_fault, "detached_pixel": speck}
            rows.append(case_info)
    manifest = {"schema_version": "1", "dataset_id": "i_mage_not_ai-icon-multimetric",
                "dataset_version": "1.0.2", "kind": "controlled-synthetic",
                "canvas": [SIZE, SIZE], "cases": rows}
    (DATA / "dataset.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": str(DATA / "dataset.json"), "cases": len(rows),
                      "faults": {fault: sum(row["fault"] == fault for row in rows) for fault in FAULTS}}, indent=2))


if __name__ == "__main__":
    main()
