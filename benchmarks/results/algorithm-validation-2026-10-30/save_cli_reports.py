"""Recreate the saved CLI JSON evidence for algorithm golden fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


def run(name: str, *args: str | Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "i_mage_not_ai", *map(str, args)],
        cwd=ROOT.parents[2], capture_output=True, text=True,
    )
    if result.returncode not in (0, 1, 2):
        raise RuntimeError(f"{name}: CLI exit {result.returncode}: {result.stderr}")
    report = json.loads(result.stdout)
    (ROOT / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


alpha = FIXTURES / "alpha"
run("alpha-inspect", "inspect", alpha / "alpha.png")
run("alpha-review", "review", "--manifest", alpha / "manifest.json")
run("mask-review", "review", "--manifest", FIXTURES / "mask" / "manifest.json")

patterns = FIXTURES / "raster-patterns"
def write_manifest(name: str, image: str, features: list[dict]) -> Path:
    image_path = patterns / image
    import hashlib
    doc = {
        "schema_version": "0.5",
        "asset": {"path": image, "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()},
        "features": features,
        "constraints": {},
    }
    manifest = patterns / f"{name}-manifest.json"
    manifest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return manifest


all_mask = {"id": "background", "role": "background",
            "geometry": {"type": "mask", "path": "all.png"},
            "properties": {"max_periodic_energy_ratio": 0.9,
                           "min_occupancy_ratio": 1.0,
                           "max_gradient_fit_r2": 0.9,
                           "gradient_allowed": False}}
run("checker-review", "review", "--manifest",
    write_manifest("checker", "checker.png", [all_mask]))
run("gradient-review", "review", "--manifest",
    write_manifest("gradient", "gradient.png", [all_mask]))
seam_mask = {"id": "background", "role": "background",
             "properties": {"seamless_tile": True, "max_tile_edge_error": 4.0}}
run("tile-review", "review", "--manifest",
    write_manifest("tile", "seam.png", [seam_mask]))

svg = FIXTURES / "svg"
run("svg-review", "review", "--manifest", svg / "svg-manifest.json")

game = FIXTURES / "game-trace"
run("game-trace-review", "game", "analyze", "--trace", game / "trace.json",
    "--policy", game / "policy.json")
runtime = FIXTURES / "runtime-evidence"
run("runtime-evidence-review", "game", "runtime-check", "--evidence",
    runtime / "runtime-evidence.json", "--policy", runtime / "runtime-policy.json")
