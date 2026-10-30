"""Score the blind v2 icon benchmark with shared labels and output-derived masks."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-05"
RULES = ["IMAGE-001", "GEOMETRY-001", "GEOMETRY-002", "COLOR-001", "COLOR-002",
         "TOPOLOGY-001", "CHARACTER-002", "BACKGROUND-003"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGBA")).copy()


def cli_report(arm: str, sid: str, asset: Path, mask: Path, thresholds: dict) -> dict:
    base = RUN / "sessions" / arm / "outputs"
    checkdir = base / "output-recheck" / sid
    checkdir.mkdir(parents=True, exist_ok=True)
    rp = checkdir / "report.json"
    if rp.is_file():
        cached = read_json(rp)
        if cached.get("asset", {}).get("sha256") == digest(asset) and cached.get("completeness") == "COMPLETE":
            return cached
    shutil.copyfile(asset, checkdir / "asset.png")
    mask.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((image(asset)[:, :, 3] > 0).astype(np.uint8) * 255, "L").save(mask)
    manifest = {
        "schema_version": "0.5",
        "asset": {"path": "asset.png", "format": "png", "sha256": digest(asset)},
        "constraints": {
            "max_normalized_centroid_offset": thresholds["max_centroid"],
            "min_margin_ratio": 0.03,
            "max_palette_colors": thresholds["max_palette"],
        },
        "features": [{"id": "foreground", "role": "foreground",
                      "geometry": {"type": "mask", "path": "silhouette.png"},
                      "properties": {"max_connected_components": thresholds["components"],
                                     "max_silhouette_components": thresholds["components"],
                                     "min_occupancy_ratio": 0.05}}],
    }
    mp = base / "output-recheck" / sid / "manifest.json"
    write_json(mp, manifest)
    cmd = [str(ROOT / ".venv/Scripts/python.exe"), "-m", "i_mage_not_ai", "review",
           "--manifest", str(mp), "--output", str(rp)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode not in (0, 1, 2) or not rp.is_file():
        raise RuntimeError(f"output CLI recheck failed {arm}/{sid}: {r.stderr}\n{r.stdout}")
    return read_json(rp)


def set_stats(expected: set[str], predicted: set[str]) -> dict:
    tp, fp, fn = len(expected & predicted), len(predicted - expected), len(expected - predicted)
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else (1.0 if not expected else 0.0),
            "recall": tp / (tp + fn) if tp + fn else 1.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
            "exact_set_match": expected == predicted}


def repair_metrics(clean: Path, faulty: Path, output: Path) -> dict:
    c, f, o = image(clean), image(faulty), image(output)
    cm, om = c[:, :, 3] > 0, o[:, :, 3] > 0
    union = np.logical_or(cm, om).sum()
    inter = np.logical_and(cm, om).sum()
    rgb_mae = float(np.abs(c[:, :, :3].astype(np.int16) - o[:, :, :3].astype(np.int16)).mean() / 255)
    rgba_mae = float(np.abs(c.astype(np.int16) - o.astype(np.int16)).mean() / 255)
    vis = np.logical_or(cm, om)
    visible_rgba_mae = float(np.abs(c.astype(np.int16) - o.astype(np.int16))[vis].mean() / 255) if vis.any() else 0.0
    return {"output_sha256": digest(output), "clean_exact": np.array_equal(c, o),
            "faulty_exact": np.array_equal(f, o), "full_canvas_rgba_mae_vs_clean": rgba_mae,
            "visible_union_rgba_mae_vs_clean": visible_rgba_mae, "rgb_mae_vs_clean": rgb_mae,
            "silhouette_iou_vs_clean": float(inter / union) if union else 1.0,
            "changed_alpha_pixels_vs_clean": int(np.count_nonzero(cm != om))}


def main() -> None:
    truth = read_json(RUN / "evaluator/ground-truth-map.json")["samples"]
    arm_results = {}
    for arm in ("agent-only", "agent-cli"):
        base = RUN / "sessions" / arm
        decisions_obj = read_json(base / "outputs/decisions.json")
        decisions = decisions_obj.get("decisions", [])
        by_id = {x.get("sample_id"): x for x in decisions}
        if len(by_id) != 24 or set(by_id) != set(truth):
            raise ValueError(f"{arm}: expected 24 unique structured decisions, got {len(by_id)}")
        stats = []; per_condition = {}; per_sample = []; repair = []; recheck = []
        for sid, hidden in sorted(truth.items()):
            pred = by_id[sid].get("diagnosed_rule_ids")
            if not isinstance(pred, list) or any(x not in RULES for x in pred):
                raise ValueError(f"invalid diagnosed_rule_ids in {arm}/{sid}: {pred}")
            expected, predicted = set(hidden["expected_rules"]), set(pred)
            s = set_stats(expected, predicted); stats.append(s)
            per_condition.setdefault(hidden["condition"], []).append(s)
            per_sample.append({"sample_id": sid, "condition": hidden["condition"], "kind": hidden["kind"],
                               "expected_rules": sorted(expected), "predicted_rules": sorted(predicted), **s})
            out = base / "outputs/repaired" / f"{sid}.png"
            inp = base / "inputs" / sid / "asset.png"
            clean = RUN.parent.parent / "datasets/icon-multimetric-v2" / hidden["clean_asset"]
            if not out.is_file(): raise FileNotFoundError(f"missing repair {arm}/{sid}: {out}")
            repair.append({"sample_id": sid, "condition": hidden["condition"], "kind": hidden["kind"],
                           **repair_metrics(clean, inp, out)})
            report = cli_report(arm, sid, out, base / "outputs/output-recheck" / sid / "silhouette.png", hidden["thresholds"])
            failures = sorted({x["rule_id"] for x in report.get("results", []) if x.get("status") == "FAIL"})
            recheck.append({"sample_id": sid, "condition": hidden["condition"],
                            "completeness": report.get("completeness"), "remaining_fail_rules": failures,
                            "passes_all_supported_policy_checks": report.get("completeness") == "COMPLETE" and not failures})
        clean_cases = [x for x in repair if x["condition"] == "normal"]
        fault_cases = [x for x in repair if x["condition"] != "normal"]
        totals = {k: sum(x[k] for x in stats) for k in ("tp", "fp", "fn")}
        totals["precision"] = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 0.0
        totals["recall"] = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 1.0
        totals["f1"] = 2 * totals["tp"] / (2 * totals["tp"] + totals["fp"] + totals["fn"]) if 2 * totals["tp"] + totals["fp"] + totals["fn"] else 1.0
        def macro(items):
            n = len(items)
            return {k: sum(x[k] for x in items) / n if n else None
                    for k in ("precision", "recall", "f1", "exact_set_match")}
        arm_results[arm] = {
            "n": len(stats), "diagnosis_micro": totals,
            "diagnosis_macro_per_sample": macro(stats),
            "diagnosis_by_condition": {c: {"n": len(v), **macro(v)} for c, v in sorted(per_condition.items())},
            "normal_specificity": sum(not x["predicted_rules"] for x in per_sample if x["condition"] == "normal") / len(clean_cases),
            "fault_detection_recall": sum(bool(set(x["expected_rules"]) & set(x["predicted_rules"])) for x in per_sample if x["condition"] != "normal") / len(fault_cases),
            "clean_control_preservation_rate": sum(x["clean_exact"] for x in clean_cases) / len(clean_cases),
            "repair_exact_recovery_rate_on_faults": sum(x["clean_exact"] for x in fault_cases) / len(fault_cases),
            "repair_policy_pass_rate": sum(x["passes_all_supported_policy_checks"] for x in recheck) / len(recheck),
            "mean_fault_silhouette_iou_vs_clean": sum(x["silhouette_iou_vs_clean"] for x in fault_cases) / len(fault_cases),
            "per_sample": per_sample, "repair_metrics": repair, "output_policy_recheck": recheck,
        }
        if arm == "agent-cli":
            cli_sets = []
            for sid, hidden in sorted(truth.items()):
                report = read_json(base / "outputs/cli-reports" / f"{sid}.json")
                found = {x["rule_id"] for x in report["results"] if x["status"] == "FAIL"}
                cli_sets.append({"sid": sid, **set_stats(set(hidden["expected_rules"]), found)})
            arm_results[arm]["standalone_cli_diagnosis_macro"] = macro(cli_sets)
            arm_results[arm]["standalone_cli_diagnosis_exact_set_accuracy"] = sum(x["exact_set_match"] for x in cli_sets) / len(cli_sets)
    result = {"version": "2.0.0", "protocol": "same blinded 24 inputs, fixed clean-derived per-artwork thresholds, identical structured rule-ID scoring, hidden labels used only by scorer; output masks regenerated from each submitted RGBA alpha", "scores": arm_results}
    write_json(RUN / "evaluator/final-score.json", result)
    print(json.dumps({arm: {k:v for k,v in data.items() if k not in ("per_sample","repair_metrics","output_policy_recheck")} for arm,data in arm_results.items()}, indent=2))


if __name__ == "__main__":
    main()
