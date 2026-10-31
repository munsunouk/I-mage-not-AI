"""Run all declared CLI checks on the 24 clean counterparts as false-positive controls."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


from prepare_multimetric_icon_dataset import DATA, make_icon, make_policy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-04"
MAP = json.loads((OUT / "evaluator/ground-truth-map.json").read_text(encoding="utf-8"))["samples"]
SHAPES = ("orb", "shield", "hex", "potion")


def main() -> None:
    base = OUT / "evaluator/preflight-clean"
    base.mkdir(parents=True, exist_ok=True)
    for sample_id, row in MAP.items():
        variant = int(row["case_id"].split("-")[1]) - 1
        fault_info = next(case for case in json.loads((DATA / "dataset.json").read_text(encoding="utf-8"))["cases"]
                          if case["case_id"] == row["case_id"])
        variant = fault_info["variant"]
        kind = SHAPES[variant]
        clean, masks = make_icon(kind, variant)
        folder = base / sample_id
        folder.mkdir(parents=True, exist_ok=True)
        asset = folder / "asset.png"
        shutil.copyfile(DATA / row["clean_asset"], asset)
        mask_dir = folder / "masks"
        mask_dir.mkdir(exist_ok=True)
        for name, mask in masks.items():
            mask.save(mask_dir / f"{name}.png", optimize=False)
        case = dict(fault_info)
        case["input_sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
        manifest = make_policy(case, clean, masks, masks)
        manifest["asset"]["sha256"] = case["input_sha256"]
        for feature in manifest["features"]:
            feature["geometry"]["path"] = "masks/" + Path(feature["geometry"]["path"]).name
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        output = folder / "report.json"
        run = subprocess.run([sys.executable, "-m", "i_mage_not_ai", "review", "--manifest", str(manifest_path), "--output", str(output)],
                             cwd=ROOT, capture_output=True, text=True)
        if run.returncode not in (0, 1, 2):
            raise RuntimeError(f"{sample_id}: CLI returned {run.returncode}: {run.stderr}")
        report = json.loads(output.read_text(encoding="utf-8"))
        if report.get("completeness") != "COMPLETE" or any(item.get("status") != "PASS" for item in report["results"]):
            raise RuntimeError(f"{sample_id}: clean control has a non-PASS finding")
    print(json.dumps({"status": "PASS", "clean_controls": len(MAP), "reports": str(base)}, indent=2))


if __name__ == "__main__":
    main()
