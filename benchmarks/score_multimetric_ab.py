"""Independently score the two blinded multimetric icon-repair runs."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from PIL import Image

from prepare_multimetric_icon_dataset import DATA, SIZE, make_icon, make_policy, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-04"
GROUND = json.loads((OUT / "evaluator/ground-truth-map.json").read_text(encoding="utf-8"))["samples"]
CASE_DATA = {item["case_id"]: item for item in json.loads((DATA / "dataset.json").read_text(encoding="utf-8"))["cases"]}
SHAPES = ("orb", "shield", "hex", "potion")
RULE_GROUPS = {
    "center": "center", "GEOMETRY-001": "center", "alpha_centroid_offset": "center", "centroid": "center",
    "margin": "margin", "GEOMETRY-002": "margin", "alpha_margin_ratio": "margin", "edge margin": "margin",
    "color": "color", "COLOR-001": "color", "COLOR-002": "color", "SOLID-001": "color", "SOLID-002": "color",
    "right-gem-lab": "color", "right-gem-exact": "color", "right-gem-solid": "color", "palette": "color", "delta e": "color",
    "components": "components", "TOPOLOGY-001": "components", "CHARACTER-002": "components", "mask_connected_components": "components", "silhouette": "components", "detached": "components",
    "symmetry": "symmetry", "SYMMETRY-001": "symmetry", "mask_reflection_iou": "symmetry", "gem-pair": "symmetry", "asymmetric": "symmetry",
    "overlap": "overlap", "OVERLAP-001": "overlap", "mask_intersection_ratio": "overlap",
    "absent": "overlap", "missing gem": "overlap", "farther outward": "symmetry",
    "magenta pixel": "color", "off-palette": "color", "detached speck": "components",
}


def normalized_groups(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, dict):
        values = [values]
    elif isinstance(values, str):
        values = [values]
    result: set[str] = set()
    for item in values:
        text = str(item.get("rule_id") or item.get("id") or item.get("rule") or item.get("issue") or item.get("feature_id") or item) if isinstance(item, dict) else str(item)
        lowered = text.casefold()
        for alias, group in RULE_GROUPS.items():
            if alias.casefold() in lowered:
                result.add(group)
    return result


def decisions_from(path: Path) -> dict[str, set[str]]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("decisions", doc.get("per_sample", doc)) if isinstance(doc, dict) else doc
    out: dict[str, set[str]] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            sample = row.get("sample") or row.get("sample_id") or row.get("case_id")
            if not sample:
                continue
            ids = row.get("diagnosed_rule_ids", row.get("rule_ids", row.get("diagnosis", row.get("diagnosed_issues", [])))) or []
            # Feature IDs name the inspected mask/region, not the diagnosed fault.
            # Use them only when they are registered rule IDs; otherwise score the
            # agent's written visual evidence instead of guessing from a feature name.
            registered = {"GEOMETRY-001", "GEOMETRY-002", "COLOR-001", "COLOR-002", "SOLID-001", "SOLID-002", "TOPOLOGY-001", "CHARACTER-002", "SYMMETRY-001", "OVERLAP-001"}
            groups = normalized_groups(ids) if any(str(value) in registered for value in ids) else set()
            evidence = row.get("evidence") or row.get("reason") or row.get("notes") or ""
            evidence += " " + str(row.get("action") or "")
            if evidence:
                groups |= normalized_groups(str(evidence))
            out[str(sample)] = groups
    elif isinstance(rows, dict):
        for sample, row in rows.items():
            if isinstance(row, dict):
                ids = row.get("diagnosed_rule_ids", row.get("rule_ids", row.get("diagnosis", row.get("diagnosed_issues", [])))) or []
                registered = {"GEOMETRY-001", "GEOMETRY-002", "COLOR-001", "COLOR-002", "SOLID-001", "SOLID-002", "TOPOLOGY-001", "CHARACTER-002", "SYMMETRY-001", "OVERLAP-001"}
                groups = normalized_groups(ids) if any(str(value) in registered for value in ids) else set()
                evidence = row.get("evidence") or row.get("reason") or ""
                evidence += " " + str(row.get("action") or "")
                if evidence:
                    groups |= normalized_groups(str(evidence))
            else:
                groups = normalized_groups(row)
            out[str(sample)] = groups
    return out


def cli_review(manifest: Path, output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run([sys.executable, "-m", "i_mage_not_ai", "review", "--manifest", str(manifest), "--output", str(output)],
                         cwd=ROOT, capture_output=True, text=True)
    if run.returncode not in (0, 1, 2) or not output.is_file():
        raise RuntimeError(f"review failed: {manifest}: {run.stderr}")
    return json.loads(output.read_text(encoding="utf-8"))


def compare_pixels(actual: Path, reference: Path) -> tuple[float, int, bool]:
    with Image.open(actual) as image:
        a = image.convert("RGBA")
    with Image.open(reference) as image:
        b = image.convert("RGBA")
    if a.size != b.size:
        return 0.0, 0, False
    matching = sum(x == y for x, y in zip(a.getdata(), b.getdata()))
    return matching / (a.width * a.height), a.width * a.height - matching, True


def evaluate_arm(arm: str) -> dict:
    session = OUT / "sessions" / arm
    output_dir = session / "outputs"
    decisions = decisions_from(output_dir / "decisions.json")
    predicted: dict[str, set[str]] = {sid: set(groups) for sid, groups in decisions.items()}
    input_reports_validated = 0
    if arm == "agent-cli":
        report_dir = output_dir / "cli-reports"
        for sid, row in GROUND.items():
            path = report_dir / f"{sid}.json"
            if not path.is_file():
                continue
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("completeness") == "COMPLETE" and report.get("asset", {}).get("sha256") == row["sha256"]:
                input_reports_validated += 1
                found = set()
                for result in report.get("results", []):
                    if result.get("status") == "FAIL":
                        found |= normalized_groups([result.get("rule_id", ""), result.get("algorithm", "")])
                predicted[sid] = found

    tp = fp = fn = 0
    per_sample = []
    pixel_scores = []
    dimensions_ok = outputs_found = output_review_passes = 0
    closer_to_clean = unchanged_from_input = farther_from_clean = 0
    input_pixel_errors: list[int] = []
    output_review_reports = OUT / "evaluator" / f"repair-reviews-{arm}"
    for sid, row in GROUND.items():
        expected = {row["fault"]}
        got = predicted.get(sid, set())
        tp += len(expected & got); fp += len(got - expected); fn += len(expected - got)
        output = output_dir / f"{sid}.png"
        clean = DATA / row["clean_asset"]
        if not output.is_file():
            per_sample.append({"sample_id": sid, "expected": sorted(expected), "predicted": sorted(got),
                               "output_found": False})
            fn += 0
            continue
        outputs_found += 1
        pixel_ratio, changed, dims = compare_pixels(output, clean)
        pixel_scores.append(pixel_ratio); dimensions_ok += int(dims)
        _, input_changed, _ = compare_pixels(session / "inputs" / sid / "asset.png", clean)
        input_pixel_errors.append(input_changed)
        closer_to_clean += int(changed < input_changed)
        unchanged_from_input += int(changed == input_changed)
        farther_from_clean += int(changed > input_changed)

        case = CASE_DATA[row["case_id"]]
        kind = SHAPES[case["variant"]]
        clean_image, clean_masks = make_icon(kind, case["variant"])
        output_case = dict(case); output_case["input_sha256"] = sha(output)
        policy = make_policy(output_case, clean_image, clean_masks, clean_masks)
        eval_dir = output_review_reports / sid
        eval_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output, eval_dir / "asset.png")
        mask_dir = eval_dir / "masks"; mask_dir.mkdir(exist_ok=True)
        # Derive silhouette from the submitted output; the component-feature masks
        # use the renderer's clean feature masks as the target geometry.
        with Image.open(output) as image:
            output_silhouette = image.convert("RGBA").getchannel("A").point(lambda value: 255 if value else 0)
        clean_masks["silhouette"] = output_silhouette
        for name, mask in clean_masks.items():
            mask.save(mask_dir / f"{name}.png", optimize=False)
        policy["asset"]["sha256"] = sha(eval_dir / "asset.png")
        for feature in policy["features"]:
            feature["geometry"]["path"] = "masks/" + Path(feature["geometry"]["path"]).name
        manifest_path = eval_dir / "manifest.json"
        manifest_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
        report = cli_review(manifest_path, eval_dir / "report.json")
        failed = [item["rule_id"] for item in report.get("results", []) if item.get("status") == "FAIL"]
        complete = report.get("completeness") == "COMPLETE"
        all_pass = complete and not failed
        output_review_passes += int(all_pass)
        per_sample.append({"sample_id": sid, "expected": sorted(expected), "predicted": sorted(got),
                           "diagnosis_correct": bool(expected & got) and not bool(got - expected),
                           "output_found": True, "output_review_status": report.get("status"),
                           "output_review_failed_rules": failed, "all_output_checks_pass": all_pass,
                           "pixel_match_to_clean": pixel_ratio, "changed_pixels_from_clean": changed,
                           "input_changed_pixels_from_clean": input_changed,
                           "closer_to_clean_than_input": changed < input_changed,
                           "dimensions_preserved": dims})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "arm": arm,
        "diagnosis": {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1},
        "repairs": {"outputs_found": outputs_found, "dimensions_preserved": dimensions_ok,
                    "all_output_cli_checks_pass": output_review_passes,
                    "mean_exact_pixel_match_to_clean": sum(pixel_scores) / len(pixel_scores) if pixel_scores else 0.0,
                    "exact_pixel_matches": sum(score == 1.0 for score in pixel_scores),
                    "mean_changed_pixels_from_clean": sum(1.0 - score for score in pixel_scores) * SIZE * SIZE / len(pixel_scores) if pixel_scores else None,
                    "closer_to_clean_than_input": closer_to_clean,
                    "unchanged_from_input": unchanged_from_input,
                    "farther_from_clean_than_input": farther_from_clean,
                    "mean_input_changed_pixels_from_clean": sum(input_pixel_errors) / len(input_pixel_errors) if input_pixel_errors else None},
        "input_cli_reports_validated": input_reports_validated,
        "per_sample": per_sample,
    }


def main() -> None:
    arms = {arm: evaluate_arm(arm) for arm in ("agent-only", "agent-cli")}
    delta = {metric: arms["agent-cli"][family][metric] - arms["agent-only"][family][metric]
             for family, metrics in (("diagnosis", ("precision", "recall", "f1")),
                                     ("repairs", ("mean_exact_pixel_match_to_clean",)))
             for metric in metrics}
    report = {"status": "SCORED_MULTIMETRIC_SINGLE_LOOP",
              "dataset_version": "1.0.2", "case_count": len(GROUND),
              "preflight": json.loads((OUT / "evaluator/preflight-summary.json").read_text(encoding="utf-8")),
              "arms": arms, "agent_cli_minus_agent_only": delta,
              "limitations": [
                  "Single 24-case controlled synthetic loop; not a general image-quality study.",
                  "Agent Only uses visual reasoning; Agent + CLI uses saved i-mage-not-ai JSON. Conversations are separate, but local filesystem isolation is procedural, not OS-enforced.",
                  "Feature overlap and symmetry output rechecks use renderer-authored target masks; exact pixel agreement with the hidden clean reference is reported separately.",
                  "No human preference or AI-slop judgment is encoded by these metrics.",
              ]}
    path = OUT / "comparison.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "arms": {
        arm: {"diagnosis": value["diagnosis"], "repairs": value["repairs"],
              "input_cli_reports_validated": value["input_cli_reports_validated"]}
        for arm, value in arms.items()}, "delta": delta}, indent=2))


if __name__ == "__main__":
    main()
