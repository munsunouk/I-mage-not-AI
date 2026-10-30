"""Score isolated Agent Only vs Agent + CLI artifacts for one icon benchmark loop."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


ALIASES = {
    "COLOR-001": "COLOR-001",
    "exact_palette_count": "COLOR-001",
    "single_visible_rgb_color": "COLOR-001",
    "palette": "COLOR-001",
    "GEOMETRY-002": "GEOMETRY-002",
    "alpha_margin_ratio": "GEOMETRY-002",
    "transparent_margin": "GEOMETRY-002",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def score_findings(expected: set[tuple[str, str]], predicted: set[tuple[str, str]]) -> dict[str, Any]:
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"ground_truth_findings": len(expected), "predicted_findings": len(predicted), "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


def image_violations(path: Path) -> set[str]:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    colors = {pixel[:3] for count, pixel in (image.getcolors(maxcolors=image.width * image.height) or []) if count and pixel[3] > 0}
    result = set()
    if len(colors) > 1:
        result.add("COLOR-001")
    box = image.getchannel("A").getbbox()
    if box is None:
        result.add("GEOMETRY-002")
    else:
        width, height = image.size
        margins = (box[0] / width, box[1] / height, (width - box[2]) / width, (height - box[3]) / height)
        if min(margins) < 0.1:
            result.add("GEOMETRY-002")
    return result


def diagnoses(doc: dict[str, Any]) -> set[tuple[str, str]]:
    result = set()
    for sample_id, row in doc.items():
        values = row.get("diagnosis", []) if isinstance(row, dict) else []
        if isinstance(values, str):
            values = [values]
        for value in values:
            rule = ALIASES.get(str(value))
            if rule:
                result.add((sample_id, rule))
    return result


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    root = repo / "benchmarks" / "results" / "icon-isolated-loop-02"
    dataset = load(repo / "benchmarks" / "datasets" / "icon" / "dataset.json")
    truth_map = load(root / "evaluator" / "ground-truth-map.json")
    verified = load(root / "verified-result.json")
    sample_to_case = {item["sample_id"]: item["case_id"] for item in truth_map["samples"]}
    expected = {(item["case_id"], item["injected_rule"]) for item in dataset["cases"]}
    decisions = {
        "agent_only": diagnoses(load(root / "agent-only" / "decisions.json")),
        "agent_plus_tool": diagnoses(load(root / "agent-cli" / "decisions.json")),
    }
    # Translate anonymized sample IDs to dataset case IDs only in this evaluator.
    decisions = {track: {(sample_to_case[sample_id], rule) for sample_id, rule in findings} for track, findings in decisions.items()}

    cli_sample_count = 0
    for item in truth_map["samples"]:
        sample_id = item["sample_id"]
        report_path = root / "agent-cli" / sample_id / "report.json"
        report = load(report_path)
        if report.get("asset", {}).get("sha256") != item["asset_sha256"]:
            raise ValueError(f"CLI report asset hash differs from blind input for {sample_id}")
        if report.get("completeness") != "COMPLETE":
            raise ValueError(f"CLI report is incomplete for {sample_id}")
        cli_sample_count += 1
    if cli_sample_count != len(truth_map["samples"]):
        raise ValueError("not every blind input has a CLI report")

    tracks: dict[str, Any] = {}
    for track_key, result_key, folder_key in (
        ("agent_only", "agent_only", "agent-only"),
        ("agent_plus_tool", "agent_plus_tool", "agent-cli"),
    ):
        detect = score_findings(expected, decisions[track_key])
        official = verified["tracks"][result_key]
        regressed_cases = 0
        for case in dataset["cases"]:
            before = repo / "benchmarks" / "datasets" / "icon" / case["faulty_asset"]
            output = root / folder_key / f"{next(s for s,c in sample_to_case.items() if c == case['case_id'])}.png"
            newly_failed = image_violations(output) - image_violations(before)
            regressed_cases += bool(newly_failed)
        tracks[track_key] = {
            "detection": detect,
            "repair": {
                "fix_success_rate": official.get("fix_success_rate"),
                "regression_rate": regressed_cases / len(dataset["cases"]),
                "regression_cases": regressed_cases,
                "preservation_rate": official.get("preservation_rate"),
                "changed_pixels": official.get("changed_pixels"),
                "changes_outside_allowed_region": official.get("changes_outside_allowed_region"),
            },
        }

    baseline, candidate = tracks["agent_only"], tracks["agent_plus_tool"]
    deltas = {}
    for family, keys in (("detection", ("precision", "recall", "f1")),
                         ("repair", ("fix_success_rate", "regression_rate", "preservation_rate"))):
        deltas[family] = {key: candidate[family][key] - baseline[family][key] for key in keys
                          if candidate[family].get(key) is not None and baseline[family].get(key) is not None}
    # The stock evaluator's precision/recall describe defects remaining after
    # repair. For this gallery we display the separately scored pre-repair
    # diagnoses while retaining repair and preservation metrics from the
    # official verified result.
    gallery_result = json.loads(json.dumps(verified))
    for track_key in ("agent_only", "agent_plus_tool"):
        diagnosis = tracks[track_key]["detection"]
        gallery_track = gallery_result["tracks"][track_key]
        for key in ("ground_truth_violations", "predicted_violations", "true_positives", "false_positives", "false_negatives", "precision", "recall", "f1"):
            gallery_track[key] = diagnosis[{"ground_truth_violations": "ground_truth_findings", "predicted_violations": "predicted_findings", "true_positives": "tp", "false_positives": "fp", "false_negatives": "fn"}.get(key, key)]
        gallery_track["diagnosis_scored_before_repair"] = True
    (root / "gallery-result.json").write_text(json.dumps(gallery_result, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "ISOLATED_SINGLE_LOOP_EXPLORATORY",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "faulty_images": len(dataset["cases"]),
        "clean_control_images_shown_to_agents": 0,
        "cli_reports_validated": cli_sample_count,
        "tracks": tracks,
        "agent_plus_tool_minus_agent_only": deltas,
        "session_isolation": {
            "agent_only_thread_id": "01a18cfa-55b8-7280-bfd1-bc240c4edd3b",
            "agent_plus_cli_thread_id": "01a18cfa-59ba-76a0-a732-f3f1b8ad89c8",
            "separate_projectless_threads": True,
            "ground_truth_mapping_exposed_to_sessions": False,
            "model_snapshot": "same local default configuration; exact snapshot unavailable",
            "attempt_limit": 1,
        },
        "limitations": [
            "One run on a small, public synthetic dataset; results are exploratory, not a general image-quality claim.",
            "The two Codex sessions had isolated conversation histories and received anonymized inputs, but filesystem separation was procedural rather than OS-enforced.",
            "No token or API-cost telemetry was available; projectless task durations include setup and tool use and are not comparable model-inference timings.",
            "The dataset contains fault-injected images only in agent input, so clean-image false-positive rates are not measured.",
        ],
    }
    (root / "comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
