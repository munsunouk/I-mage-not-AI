"""Reproducible 1024x1024 raster review benchmark; generates inputs in a temp directory."""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from imreview.core import review  # noqa: E402


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    yy, xx = np.indices((size, size))
    checker = ((xx // 16 + yy // 16) % 2).astype(np.uint8)
    rgba = np.empty((size, size, 4), dtype=np.uint8)
    rgba[..., 0] = checker * 180 + 40
    rgba[..., 1] = checker * 120 + 30
    rgba[..., 2] = checker * 80 + 20
    rgba[..., 3] = 255

    with tempfile.TemporaryDirectory(prefix="imreview-benchmark-") as directory:
        root = Path(directory)
        asset = root / "asset.png"
        mask = root / "mask.png"
        Image.fromarray(rgba, "RGBA").save(asset)
        Image.fromarray(np.full((size, size), 255, dtype=np.uint8), "L").save(mask)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "0.5",
            "asset": {"path": "asset.png", "sha256": digest},
            "constraints": {"max_palette_colors": 4, "min_margin_ratio": 0},
            "features": [{
                "id": "checker", "role": "background",
                "geometry": {"type": "mask", "path": "mask.png"},
                "properties": {
                    "surface": "solid", "max_channel_range": 255,
                    "max_delta_e00": 100, "max_exceedance_ratio": 1,
                    "max_palette_colors": 4, "max_connected_components": 1,
                    "min_symmetry_iou": 1,
                },
            }],
        }
        durations = []
        result = None
        for _ in range(runs):
            start = time.perf_counter()
            result = review(manifest, root)
            durations.append(time.perf_counter() - start)
        assert result is not None
        if result["status"] != "PASS" or result["completeness"] != "COMPLETE":
            raise SystemExit(f"benchmark fixture must PASS/COMPLETE: {result['status']} {result['coverage']}")
        print(json.dumps({
            "size": [size, size], "runs": runs,
            "seconds": durations, "median_seconds": statistics.median(durations),
            "status": result["status"], "completeness": result["completeness"],
            "finding_count": len(result["results"]),
            "coverage": result["coverage"],
            "findings": [{"rule_id": f["rule_id"], "status": f["status"], "measured": f["measured"]}
                         for f in result["results"]],
        }, indent=2))


if __name__ == "__main__":
    main()
