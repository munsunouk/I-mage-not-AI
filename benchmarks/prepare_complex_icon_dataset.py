"""Prepare a fixed-seed, fault-injected dataset from a 4x5 generated icon sheet."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


OUT = Path("benchmarks/datasets/complex-icon-v1")
SOURCE = OUT / "source-sheet.png"
SIZE = 128


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba_palette(image: Image.Image) -> set[tuple[int, int, int]]:
    pixels = image.convert("RGBA").getdata()
    return {p[:3] for p in pixels if p[3] > 0}


def main() -> None:
    sheet = Image.open(SOURCE).convert("RGBA")
    if sheet.size != (1122, 1402):
        raise ValueError(f"unexpected source dimensions: {sheet.size}")
    clean_dir, faulty_dir = OUT / "clean", OUT / "faulty"
    clean_dir.mkdir(parents=True, exist_ok=True)
    faulty_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    # The generated sprite sheet has a consistent four-column layout but its
    # rows follow the artwork's visual gaps, not equal-height boundaries.
    x_edges = (0, 275, 553, 833, 1122)
    y_edges = (0, 275, 553, 819, 1080, 1402)
    for index in range(20):
        row, col = divmod(index, 4)
        cell = sheet.crop((x_edges[col], y_edges[row], x_edges[col + 1], y_edges[row + 1]))
        alpha = cell.getchannel("A")
        # Ignore near-transparent generation fringe while retaining antialiased edges.
        alpha = alpha.point(lambda value: 0 if value < 24 else value)
        cell.putalpha(alpha)
        bbox = alpha.getbbox()
        if not bbox:
            raise ValueError(f"empty icon crop {index}")
        icon = cell.crop(bbox)
        icon.thumbnail((88, 88), Image.Resampling.LANCZOS)
        clean = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        clean.alpha_composite(icon, ((SIZE - icon.width) // 2, (SIZE - icon.height) // 2))
        case_id = f"complex-{index + 1:02d}"
        clean_path = clean_dir / f"{case_id}.png"
        clean.save(clean_path, optimize=False)

        limit_colors = len(rgba_palette(clean))
        faulty = clean.copy()
        if index % 2 == 0:
            rule = "COLOR-001"
            colors = rgba_palette(clean)
            patch_color = next(color for color in ((255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 64)) if color not in colors)
            clean_alpha = clean.getchannel("A")
            bbox = clean_alpha.getbbox()
            candidates = []
            for y in range(16, SIZE - 20):
                for x in range(16, SIZE - 20):
                    if all(clean_alpha.getpixel((px, py)) == 0
                           for py in range(y, y + 5) for px in range(x, x + 5)):
                        outside = (x + 5 <= bbox[0] or x >= bbox[2] or y + 5 <= bbox[1] or y >= bbox[3])
                        if outside:
                            # Prefer a corner location that is well separated
                            # from the artwork while retaining >=12% margins.
                            corner_distance = min(x + y, (SIZE - x - 5) + y,
                                                  x + (SIZE - y - 5),
                                                  (SIZE - x - 5) + (SIZE - y - 5))
                            candidates.append((corner_distance, x, y))
            if not candidates:
                raise ValueError(f"no safe transparent patch location for {case_id}")
            _, x, y = min(candidates)
            draw = ImageDraw.Draw(faulty)
            # A compact irregular sparkle makes the added palette color visible
            # while keeping the repair region deterministic and local.
            for dx, dy in ((2, 0), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3), (2, 4)):
                draw.point((x + dx, y + dy), fill=patch_color + (255,))
            allowed_regions = [[x, y, x + 5, y + 5]]
        else:
            rule = "GEOMETRY-002"
            dx, dy = ((16, 0), (0, -16), (-16, 0), (0, 16))[(index // 2) % 4]
            faulty = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
            faulty.alpha_composite(clean, (dx, dy))
            allowed_regions = [[0, 0, SIZE, SIZE]]
        faulty_path = faulty_dir / f"{case_id}-faulty.png"
        faulty.save(faulty_path, optimize=False)
        cases.append({
            "case_id": case_id,
            "clean_asset": clean_path.relative_to(OUT).as_posix(),
            "clean_sha256": digest(clean_path),
            "faulty_asset": faulty_path.relative_to(OUT).as_posix(),
            "sha256": digest(faulty_path),
            "injected_rule": rule,
            "allowed_regions": allowed_regions,
            "requirements": {"max_palette_colors": limit_colors, "min_margin_ratio": 0.12},
        })
    doc = {
        "schema_version": "1", "dataset_id": "imreview-synthetic-complex-rpg-icons",
        "dataset_version": "1.0.1", "kind": "synthetic", "generator_version": "1",
        "source_sheet_sha256": digest(SOURCE), "canvas": [SIZE, SIZE], "cases": cases,
        "findings": [{"case_id": case["case_id"], "rule_id": case["injected_rule"]} for case in cases],
    }
    (OUT / "dataset.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": str(OUT / 'dataset.json'), "source_sha256": doc["source_sheet_sha256"],
                      "cases": len(cases), "colors": {case["case_id"]: case["requirements"]["max_palette_colors"] for case in cases}}, indent=2))


if __name__ == "__main__":
    main()
