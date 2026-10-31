"""Package blinded inputs and save independent CLI preflight reports."""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from prepare_multimetric_icon_dataset import DATA, make_icon, make_policy, sha


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-04"
DATASET = json.loads((DATA / "dataset.json").read_text(encoding="utf-8"))
RULES = {"center": ["GEOMETRY-001"], "margin": ["GEOMETRY-002"],
         "color": ["COLOR-001", "COLOR-002", "SOLID-001", "SOLID-002"],
         "components": ["TOPOLOGY-001", "CHARACTER-002"],
         "symmetry": ["SYMMETRY-001"], "overlap": ["OVERLAP-001"]}


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def cli(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "i_mage_not_ai", *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True)


def main() -> None:
    rng = random.Random(8407)
    (OUT / "evaluator" / "preflight-cli").mkdir(parents=True, exist_ok=True)
    ordered = list(DATASET["cases"])
    rng.shuffle(ordered)
    public_map = []
    for condition in ("agent-only", "agent-cli"):
        session_root = OUT / "sessions" / condition
        (session_root / "inputs").mkdir(parents=True, exist_ok=True)
        (session_root / "outputs").mkdir(parents=True, exist_ok=True)
        prompt = """# Blind icon repair task

Repair the 24 supplied 128x128 RGBA fantasy inventory icons. Use one repair attempt per image. Preserve the intended icon artwork and all pixels that do not need correction.

Every input includes an image, a v0.5 manifest, and source-authored binary feature masks. The masks are aligned to that input: `silhouette` is the visible icon, `gem-pair` is its mirrored gem detail, and the two `gem` masks isolate uniform gem cores. Use the declared limits and findings supported by these inputs: palette (whole icon and masked gem), D65 CIELAB CIEDE2000, alpha-weighted centroid offset, four alpha-bbox margins, masked channel range, 8-connected components, silhouette component count/occupancy/bbox, horizontal reflection IoU, and the declared gem overlap constraint.

Save one corrected PNG per input under `outputs/sample-NN.png`, plus `decisions.json` with each sample's diagnosed rule IDs and concise evidence. Record every action. Keep the 128x128 canvas and transparent background. Do not look for evaluator labels or clean reference images.
"""
        if condition == "agent-only":
            prompt += "\nCondition: use visual reasoning only. Do not run i-mage-not-ai or any CLI diagnostic. You may use an image editor or direct pixel editing to make the repair.\n"
        else:
            prompt += "\nCondition: before editing each image, run `i-mage-not-ai review --manifest <sample manifest> --output <report.json>`. Base the diagnosis and correction on the saved CLI JSON findings, then visually check the image. Save one report per sample under `cli-reports/sample-NN.json`.\n"
        (session_root / "task-spec.md").write_text(prompt, encoding="utf-8")
        for index, row in enumerate(ordered, 1):
            sample_id = f"sample-{index:02d}"
            case_id = row["case_id"]
            source_asset = DATA / "faulty" / f"{case_id}.png"
            clean_asset = DATA / "clean" / f"{case_id}.png"
            package = session_root / "inputs" / sample_id
            package.mkdir(parents=True, exist_ok=True)
            asset_dest = package / "asset.png"
            shutil.copyfile(source_asset, asset_dest)
            clean, clean_masks = make_icon(("orb", "shield", "hex", "potion")[row["variant"]], row["variant"])
            input_masks = {}
            mask_dir = package / "masks"
            mask_dir.mkdir(exist_ok=True)
            for name, rel in row["mask_paths"].items():
                mask = Image.open(DATA / rel).convert("L")
                input_masks[name] = mask
                shutil.copyfile(DATA / rel, mask_dir / f"{name}.png")
            semantic = dict(row); semantic["input_sha256"] = sha(asset_dest)
            policy = make_policy(semantic, clean, clean_masks, input_masks)
            policy["asset"]["sha256"] = sha(asset_dest)
            for feature in policy["features"]:
                feature["geometry"]["path"] = "masks/" + Path(feature["geometry"]["path"]).name
            json_write(package / "manifest.json", policy)
            public_map.append({"sample_id": sample_id, "case_id": case_id,
                               "sha256": sha(asset_dest), "condition": condition})
            if condition == "agent-cli":
                (OUT / "evaluator" / "preflight-cli" / sample_id).mkdir(parents=True, exist_ok=True)
                preflight = cli("review", "--manifest", package / "manifest.json",
                                "--output", OUT / "evaluator" / "preflight-cli" / sample_id / "report.json")
                if preflight.returncode not in (0, 1, 2):
                    raise RuntimeError(f"preflight failed for {sample_id}: {preflight.stderr}")
                report = json.loads((OUT / "evaluator" / "preflight-cli" / sample_id / "report.json").read_text(encoding="utf-8"))
                if report.get("completeness") != "COMPLETE":
                    raise RuntimeError(f"incomplete preflight for {sample_id}: {report.get('completeness')}")
                failures = [r.get("rule_id") for r in report.get("results", []) if r.get("status") == "FAIL"]
                expected = set(RULES[row["fault"]])
                if set(failures) != expected:
                    raise RuntimeError(f"{sample_id} expected FAIL {expected}, got {failures}")
                control_dir = OUT / "evaluator" / "preflight-clean" / sample_id
                control_dir.mkdir(parents=True, exist_ok=True)
                control_asset = control_dir / "asset.png"
                shutil.copyfile(clean_asset, control_asset)
                control_masks = control_dir / "masks"
                control_masks.mkdir(exist_ok=True)
                for name, mask in clean_masks.items():
                    mask.save(control_masks / f"{name}.png", optimize=False)
                clean_case = dict(row); clean_case["input_sha256"] = sha(control_asset)
                clean_manifest = make_policy(clean_case, clean, clean_masks, clean_masks)
                clean_manifest["asset"]["sha256"] = sha(control_asset)
                for feature in clean_manifest["features"]:
                    feature["geometry"]["path"] = "masks/" + Path(feature["geometry"]["path"]).name
                json_write(control_dir / "manifest.json", clean_manifest)
                clean_report_path = control_dir / "report.json"
                clean_check = cli("review", "--manifest", control_dir / "manifest.json",
                                  "--output", clean_report_path)
                if clean_check.returncode not in (0, 1, 2):
                    raise RuntimeError(f"clean control failed for {sample_id}: {clean_check.stderr}")
                clean_report = json.loads(clean_report_path.read_text(encoding="utf-8"))
                if clean_report.get("completeness") != "COMPLETE" or any(
                        result.get("status") != "PASS" for result in clean_report.get("results", [])):
                    raise RuntimeError(f"clean control did not pass for {sample_id}")
    # One map per sample, not duplicated by session. Ground truth stays out of both task packages.
    unique = {row["sample_id"]: {"case_id": row["case_id"], "sha256": row["sha256"]} for row in public_map if row["condition"] == "agent-only"}
    for sample_id, item in unique.items():
        item["fault"] = next(row["fault"] for row in DATASET["cases"] if row["case_id"] == item["case_id"])
        item["expected_rules"] = RULES[item["fault"]]
        item["clean_asset"] = f"clean/{item['case_id']}.png"
        item["clean_sha256"] = next(row["clean_sha256"] for row in DATASET["cases"] if row["case_id"] == item["case_id"])
        item["mask_paths"] = next(row["mask_paths"] for row in DATASET["cases"] if row["case_id"] == item["case_id"])
    json_write(OUT / "evaluator" / "ground-truth-map.json", {"samples": unique})
    json_write(OUT / "protocol.json", {"dataset_id": DATASET["dataset_id"],
                                        "dataset_version": DATASET["dataset_version"],
                                        "cases": 24, "clean_controls": 24, "fault_types": sorted(RULES),
                                        "one_attempt_per_image": True,
                                        "sessions_have_independent_histories": True,
                                        "filesystem_isolation": "not OS-enforced"})
    print(json.dumps({"output": str(OUT), "sample_count": len(unique), "preflight_reports": 24}, indent=2))


if __name__ == "__main__":
    main()
