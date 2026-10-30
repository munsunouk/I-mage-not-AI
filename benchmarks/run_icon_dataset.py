"""Run the CLI detector on clean and faulty images in the synthetic icon set."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import statistics
import sys
import time
from pathlib import Path

from imreview import __version__
from imreview.typer_cli import app
from typer.testing import CliRunner


RULES = ("COLOR-001", "GEOMETRY-002")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


runner = CliRunner()


def invoke(args: list[str]):
    """Invoke the same Typer command used by the installed `i-mage-not-ai` CLI."""
    return runner.invoke(app, args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("benchmarks/datasets/icon"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/icon-v0.2.0"))
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10:
        raise ValueError("repeat must be between 1 and 10")

    dataset_dir = args.dataset.resolve()
    dataset_file = dataset_dir / "dataset.json"
    dataset = json.loads(dataset_file.read_text(encoding="utf-8"))
    cases = dataset.get("cases")
    if dataset.get("schema_version") != "1" or dataset.get("kind") != "synthetic" or not isinstance(cases, list) or not cases:
        raise ValueError("expected a non-empty schema 1 synthetic dataset")
    output_dir = args.output.resolve()
    reviews_dir = output_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    predictions: list[dict[str, str]] = []
    durations: list[float] = []
    executions = 0
    inputs_dir = reviews_dir / "inputs"
    for case in cases:
        case_id = case["case_id"]
        for variant, asset_key, evaluated_case_id in (
            ("faulty", "faulty_asset", case_id),
            ("clean", "clean_asset", f"{case_id}-clean"),
        ):
            asset_source = (dataset_dir / case[asset_key]).resolve()
            if dataset_dir not in asset_source.parents or not asset_source.is_file():
                raise ValueError(f"unsafe or missing asset for {case_id} {variant}")
            expected_hash = case.get("sha256") if variant == "faulty" else case.get("clean_sha256")
            if not expected_hash or sha256(asset_source) != expected_hash:
                raise ValueError(f"source hash mismatch for {case_id} {variant}")

            image_work = inputs_dir / f"{case_id}-{variant}"
            image_work.mkdir(parents=True, exist_ok=True)
            asset_copy = image_work / "asset.png"
            shutil.copyfile(asset_source, asset_copy)
            manifest_path = image_work / "manifest.json"
            manifest = {
                "schema_version": "0.5",
                "asset": {"path": "asset.png", "format": "png", "sha256": sha256(asset_copy)},
                "intent": {"kind": "icon", "style": "flat", "purpose": "synthetic benchmark case", "origin": "agent_inference"},
                "constraints": {"max_palette_colors": 1, "min_margin_ratio": 0.1},
                "features": [],
            }
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            report_path = reviews_dir / f"{case_id}-{variant}.json"
            command = ["review", "--manifest", str(manifest_path), "--output", str(report_path)]
            case_durations = []
            report: dict = {}
            for _ in range(args.repeat):
                start = time.perf_counter()
                completed = invoke(command)
                case_durations.append(time.perf_counter() - start)
                executions += 1
                if not report_path.is_file():
                    raise RuntimeError(f"review did not write a report for {case_id} {variant}: {completed.output}")
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if completed.exit_code not in (0, 1) or report.get("completeness") != "COMPLETE":
                    raise RuntimeError(f"incomplete CLI review for {case_id} {variant}: {completed.output}")
            durations.append(statistics.median(case_durations))
            by_rule = {finding["rule_id"]: finding["status"] for finding in report.get("results", [])}
            if not set(RULES).issubset(by_rule):
                raise RuntimeError(f"missing rule output for {case_id} {variant}: {sorted(by_rule)}")
            predictions.extend({"case_id": evaluated_case_id, "rule_id": rule_id, "status": by_rule[rule_id]} for rule_id in RULES)

    predictions_file = output_dir / "predictions.json"
    predictions_doc = {
        "schema_version": "1",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "system": {"name": "i-mage-not-ai CLI", "version": __version__},
        "findings": predictions,
    }
    predictions_file.write_text(json.dumps(predictions_doc, indent=2) + "\n", encoding="utf-8")
    score_file = output_dir / "score.json"
    score_command = ["benchmark", "score", "--ground-truth", str(dataset_file), "--predictions", str(predictions_file), "--output", str(score_file)]
    scored = invoke(score_command)
    if scored.exit_code != 0 or not score_file.is_file():
        raise RuntimeError(f"benchmark score failed: {scored.output}")

    metadata = {
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": sha256(dataset_file),
        "image_units": 2 * len(cases),
        "repeats_per_image": args.repeat,
        "cli_invocations": executions,
        "cli_wall_seconds_per_image_median": statistics.median(durations),
        "cli_wall_seconds_total_median_summed": sum(durations),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "imreview_version": __version__,
        "timing_scope": "in-process Typer CLI invocation plus review command; excludes Python interpreter startup",
    }
    (output_dir / "run-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    score = json.loads(score_file.read_text(encoding="utf-8"))
    metric = score.get("metrics", score)
    decision_count = len(predictions)
    tp, fp, fn = metric["true_positives"], metric["false_positives"], metric["false_negatives"]
    tn = decision_count - tp - fp - fn
    score["evaluation_counts"] = {
        "input_images": 2 * len(cases),
        "rule_decisions": decision_count,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "accuracy": (tp + tn) / decision_count if decision_count else None,
    }
    prediction_map = {(item["case_id"], item["rule_id"]): item["status"] for item in predictions}
    truth = {(item["case_id"], item["rule_id"]) for item in dataset["findings"]}
    per_rule = {}
    for rule_id in RULES:
        keys = [key for key in prediction_map if key[1] == rule_id]
        rule_tp = sum(key in truth and prediction_map[key] == "FAIL" for key in keys)
        rule_fp = sum(key not in truth and prediction_map[key] == "FAIL" for key in keys)
        rule_fn = sum(key in truth and prediction_map[key] != "FAIL" for key in keys)
        rule_tn = len(keys) - rule_tp - rule_fp - rule_fn
        precision = rule_tp / (rule_tp + rule_fp) if rule_tp + rule_fp else None
        recall = rule_tp / (rule_tp + rule_fn) if rule_tp + rule_fn else None
        f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
        per_rule[rule_id] = {"decisions": len(keys), "tp": rule_tp, "fp": rule_fp, "fn": rule_fn, "tn": rule_tn,
                             "precision": precision, "recall": recall, "f1": f1}
    score["per_rule"] = per_rule
    score_file.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    metric_keys = ("cases", "ground_truth_violations", "predicted_violations", "true_positives", "false_positives", "false_negatives", "precision", "recall", "f1", "status", "dataset_id", "dataset_version")
    summary = {key: metric.get(key) for key in metric_keys}
    print(json.dumps({"status": score.get("status"), "metrics": summary, "evaluation_counts": score["evaluation_counts"], "per_rule": per_rule, "run_metadata": metadata, "output": str(output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"benchmark run failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
