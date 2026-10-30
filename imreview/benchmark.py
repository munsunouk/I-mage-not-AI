"""Deterministic scoring helpers for labeled benchmark runs.

This module deliberately scores rule-level findings against explicit ground
truth. It does not infer visual quality or combine unrelated dataset versions.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable
import json
from pathlib import Path
import hashlib
import html
import os


def score_findings(expected: Iterable[dict[str, Any]], observed: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Score observed FAIL findings against labeled violations.

    Finding identity is the pair (case_id, rule_id); duplicate identities are
    rejected so accidental duplicate output cannot inflate benchmark scores.
    """
    def keyed(rows: Iterable[dict[str, Any]], label: str) -> set[tuple[str, str]]:
        keys = []
        for row in rows:
            case_id, rule_id = row.get("case_id"), row.get("rule_id")
            if not isinstance(case_id, str) or not case_id or not isinstance(rule_id, str) or not rule_id:
                raise ValueError(f"{label} entries require non-empty case_id and rule_id")
            keys.append((case_id, rule_id))
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicate {label} finding identity: {duplicates[0]}")
        return set(keys)

    truth = keyed(expected, "expected")
    predictions = keyed((row for row in observed if row.get("status") == "FAIL"), "observed")
    tp = len(truth & predictions)
    fp = len(predictions - truth)
    fn = len(truth - predictions)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else (0.0 if precision is not None and recall is not None else None)
    return {
        "cases": len({case for case, _ in truth | predictions}),
        "ground_truth_violations": len(truth),
        "predicted_violations": len(predictions),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "status": "SCORED",
    }


def score_files(ground_truth_path: Path, predictions_path: Path) -> dict[str, Any]:
    """Score a versioned ground-truth file and a predictions file."""
    truth_doc = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    prediction_doc = json.loads(predictions_path.read_text(encoding="utf-8"))
    if not isinstance(truth_doc, dict) or truth_doc.get("schema_version") != "1":
        raise ValueError("ground truth schema_version must be '1'")
    if not isinstance(truth_doc.get("dataset_id"), str) or not truth_doc["dataset_id"]:
        raise ValueError("ground truth requires dataset_id")
    if not isinstance(truth_doc.get("dataset_version"), str) or not truth_doc["dataset_version"]:
        raise ValueError("ground truth requires dataset_version")
    expected, observed = truth_doc.get("findings"), prediction_doc.get("findings") if isinstance(prediction_doc, dict) else None
    if not isinstance(expected, list) or not isinstance(observed, list):
        raise ValueError("ground truth and predictions require findings arrays")
    result = score_findings(expected, observed)
    result.update({"dataset_id": truth_doc["dataset_id"], "dataset_version": truth_doc["dataset_version"]})
    return result


def generate_synthetic_dataset(destination: Path, count: int = 20) -> dict[str, Any]:
    """Create reproducible flat-icon fixtures with one injected palette defect each."""
    if count < 1 or count > 1000:
        raise ValueError("count must be between 1 and 1000")
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise ValueError("Pillow is required to generate image fixtures") from exc
    destination.mkdir(parents=True, exist_ok=True)
    cases = []
    findings = []
    for index in range(count):
        case_id = f"icon-{index + 1:04d}"
        clean = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(clean)
        color = ((index * 47) % 200 + 30, (index * 71) % 200 + 30, (index * 89) % 200 + 30)
        draw.rectangle((8, 8, 23, 23), fill=color)
        original_path = destination / f"{case_id}.png"
        faulty_path = destination / f"{case_id}-faulty.png"
        clean.save(original_path, format="PNG", optimize=False)
        faulty = clean.copy()
        if index % 2 == 0:
            rule = "COLOR-001"
            x, y = index % 16 + 8, index % 16 + 8
            faulty.putpixel((x, y), (255, 0, 255, 255))
            allowed_regions = [[x, y, x + 1, y + 1]]
        else:
            rule = "GEOMETRY-002"
            ImageDraw.Draw(faulty).rectangle((1, 8, 30, 23), fill=color + (255,))
            allowed_regions = [[1, 8, 8, 24], [24, 8, 31, 24]]
        faulty.save(faulty_path, format="PNG", optimize=False)
        findings.append({"case_id": case_id, "rule_id": rule})
        cases.append({
            "case_id": case_id,
            "clean_asset": original_path.name,
            "faulty_asset": faulty_path.name,
            "injected_rule": rule,
            "allowed_regions": allowed_regions,
            "sha256": hashlib.sha256(faulty_path.read_bytes()).hexdigest(),
        })
    manifest = {"schema_version": "1", "dataset_id": "imreview-synthetic-flat-icons", "dataset_version": "0.2.0",
                "kind": "synthetic", "generator_version": "1", "cases": cases, "findings": findings}
    (destination / "dataset.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def create_submission_template(dataset_path: Path, output_path: Path) -> dict[str, Any]:
    """Create a comparison submission skeleton with every case enumerated."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != "1" or not isinstance(dataset.get("cases"), list):
        raise ValueError("invalid benchmark dataset")
    cases = [case.get("case_id") for case in dataset["cases"]]
    if not cases or any(not isinstance(case, str) or not case for case in cases) or len(cases) != len(set(cases)):
        raise ValueError("dataset must contain unique non-empty case IDs")
    blank_meta = {"agent": "", "model": "", "prompt_version": "", "environment": ""}
    submission = {
        "schema_version": "1",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "protocol": {"prompt_sha256": "", "attempt_limit": 3, "environment_image": "", "seed": 0},
        "tracks": {
            "original": {"metadata": dict(blank_meta)},
            "agent_only": {"metadata": dict(blank_meta), "assets": {case: "" for case in cases}},
            "agent_plus_tool": {"metadata": dict(blank_meta), "assets": {case: "" for case in cases}},
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")
    return submission


def validate_submission(dataset: dict[str, Any], submission: dict[str, Any]) -> dict[str, Any]:
    """Score one disclosed comparison run; incomplete or mismatched runs cannot qualify."""
    if submission.get("schema_version") != "1" or submission.get("dataset_id") != dataset.get("dataset_id") or submission.get("dataset_version") != dataset.get("dataset_version"):
        raise ValueError("submission dataset identity/version does not match the selected dataset")
    tracks = submission.get("tracks")
    required = {"original", "agent_only", "agent_plus_tool"}
    if not isinstance(tracks, dict) or set(tracks) != required:
        raise ValueError("submission must contain exactly original, agent_only, and agent_plus_tool tracks")
    expected_cases = {case["case_id"] for case in dataset.get("cases", [])}
    scored = {}
    for name, track in tracks.items():
        metadata = track.get("metadata", {})
        if not isinstance(metadata, dict) or not all(metadata.get(key) for key in ("agent", "model", "prompt_version", "environment")):
            raise ValueError(f"track {name} requires agent, model, prompt_version, and environment metadata")
        before = track.get("before_findings", [])
        after = track.get("after_findings", [])
        if name == "original":
            after = before
        observed_cases = {item.get("case_id") for item in after}
        if observed_cases != expected_cases:
            raise ValueError(f"track {name} must report every dataset case exactly through after_findings")
        metrics = score_findings(dataset["findings"], after)
        before_fails = {(item.get("case_id"), item.get("rule_id")) for item in before if item.get("status") == "FAIL"}
        after_fails = {(item.get("case_id"), item.get("rule_id")) for item in after if item.get("status") == "FAIL"}
        fixed = len(before_fails - after_fails)
        metrics["fix_success_rate"] = fixed / len(before_fails) if before_fails else None
        preservation = track.get("preservation")
        if name != "original" and (not isinstance(preservation, dict) or not isinstance(preservation.get("changed_pixels"), int) or not isinstance(preservation.get("allowed_pixels"), int) or preservation["allowed_pixels"] < 0 or preservation["changed_pixels"] < 0):
            raise ValueError(f"track {name} requires measured changed_pixels and allowed_pixels preservation data")
        if name != "original":
            metrics["preservation_rate"] = max(0.0, 1.0 - max(0, preservation["changed_pixels"] - preservation["allowed_pixels"]) / max(1, preservation["changed_pixels"]))
        scored[name] = {**metrics, "metadata": metadata}
    return {"schema_version": "1", "dataset_id": dataset["dataset_id"], "dataset_version": dataset["dataset_version"],
            "status": "SCORED_UNVERIFIED", "tracks": scored}


def verify_synthetic_submission(dataset_path: Path, submission_path: Path) -> dict[str, Any]:
    """Independently measure submitted assets against generated ground truth."""
    from PIL import Image, ImageChops
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != "1" or dataset.get("kind") != "synthetic":
        raise ValueError("only schema 1 synthetic datasets can be independently verified")
    if submission.get("schema_version") != "1" or any(submission.get(k) != dataset.get(k) for k in ("dataset_id", "dataset_version")):
        raise ValueError("submission dataset identity/version mismatch")
    tracks = submission.get("tracks")
    names = {"original", "agent_only", "agent_plus_tool"}
    if not isinstance(tracks, dict) or set(tracks) != names:
        raise ValueError("submission must contain original, agent_only, and agent_plus_tool tracks")
    track_meta = [tracks[name].get("metadata", {}) for name in ("agent_only", "agent_plus_tool")]
    for key in ("agent", "model", "prompt_version", "environment"):
        if not track_meta[0].get(key) or track_meta[0].get(key) != track_meta[1].get(key):
            raise ValueError(f"agent_only and agent_plus_tool must use the same declared {key}")
    protocol = submission.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError("submission requires a protocol object")
    digest = protocol.get("prompt_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
        raise ValueError("protocol.prompt_sha256 must be a SHA-256 hex digest")
    if not isinstance(protocol.get("attempt_limit"), int) or protocol["attempt_limit"] < 1:
        raise ValueError("protocol.attempt_limit must be a positive integer")
    if not protocol.get("environment_image") or not isinstance(protocol.get("seed"), int):
        raise ValueError("protocol requires environment_image and integer seed")
    root = dataset_path.resolve().parent
    findings = dataset.get("findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError("dataset has no ground-truth findings")
    cases = dataset.get("cases")
    ids = [c.get("case_id") for c in cases] if isinstance(cases, list) else []
    if len(ids) != len(set(ids)) or set(ids) != {x.get("case_id") for x in findings}:
        raise ValueError("dataset case and ground-truth IDs do not match")
    result_tracks = {}
    for name, track in tracks.items():
        metadata = track.get("metadata", {})
        if not isinstance(metadata, dict) or not all(metadata.get(k) for k in ("agent", "model", "prompt_version", "environment")):
            raise ValueError(f"track {name} requires agent, model, prompt_version, environment")
        outputs = track.get("assets", {})
        if name != "original" and set(outputs) != set(ids):
            raise ValueError(f"track {name} must provide exactly one output asset for each case")
        observed, fixed = [], 0
        changed_total = allowed_total = outside_changed_total = 0
        for case in cases:
            case_id = case["case_id"]
            faulty = (root / case["faulty_asset"]).resolve()
            if root not in faulty.parents or hashlib.sha256(faulty.read_bytes()).hexdigest() != case.get("sha256"):
                raise ValueError(f"dataset source integrity check failed for {case_id}")
            output_ref = None if name == "original" else outputs.get(case_id)
            if name != "original" and not isinstance(output_ref, str):
                raise ValueError(f"track {name} must provide output asset for {case_id}")
            output_path = faulty if name == "original" else (submission_path.resolve().parent / output_ref).resolve()
            if name != "original" and submission_path.resolve().parent not in output_path.parents:
                raise ValueError(f"output asset escapes submission directory for {case_id}")
            if not output_path.is_file():
                raise ValueError(f"missing output asset for track {name}, case {case_id}")
            if name == "original" and output_path != faulty:
                raise ValueError("original track must use the generated faulty assets")
            with Image.open(faulty) as im:
                before = im.convert("RGBA")
            with Image.open(output_path) as im:
                after = im.convert("RGBA")
            if before.size != after.size:
                raise ValueError(f"output dimensions changed for {case_id}")
            rgba = after.tobytes()
            visible = {(rgba[i], rgba[i + 1], rgba[i + 2]) for i in range(0, len(rgba), 4) if rgba[i + 3] > 0}
            rule = case["injected_rule"]
            if rule == "COLOR-001":
                measured = len(visible)
                failed = measured > 1
            elif rule == "GEOMETRY-002":
                alpha = after.getchannel("A")
                bbox = alpha.getbbox()
                if not bbox:
                    failed = True
                else:
                    width, height = after.size
                    margins = (bbox[0] / width, bbox[1] / height, (width - bbox[2]) / width, (height - bbox[3]) / height)
                    measured = min(margins)
                    failed = measured < 0.1
            else:
                raise ValueError(f"unsupported synthetic rule: {rule}")
            status = "FAIL" if failed else "PASS"
            observed.append({"case_id": case_id, "rule_id": rule, "status": status})
            if status == "PASS": fixed += 1
            if name != "original":
                allowed_regions = case["allowed_regions"]
                diff = ImageChops.difference(before, after).convert("RGB")
                for y in range(before.height):
                    for x in range(before.width):
                        changed = diff.getpixel((x, y)) != (0, 0, 0)
                        is_allowed = any(x1 <= x < x2 and y1 <= y < y2 for x1, y1, x2, y2 in allowed_regions)
                        if changed:
                            changed_total += 1
                            if not is_allowed: outside_changed_total += 1
                        if is_allowed: allowed_total += 1
            
        metrics = score_findings(findings, observed)
        metrics["fix_success_rate"] = fixed / len(cases) if name != "original" else 0.0
        if name != "original":
            metrics["preservation_rate"] = 1.0 - outside_changed_total / max(1, len(cases) * (32 * 32 - 1))
            metrics["changed_pixels"] = changed_total
            metrics["changes_outside_allowed_region"] = outside_changed_total
        result_tracks[name] = {**metrics, "metadata": metadata}
    return {"schema_version":"1", "dataset_id":dataset["dataset_id"], "dataset_version":dataset["dataset_version"],
            "status":"VERIFIED_SYNTHETIC", "validation":"assets re-measured locally against generator labels and source hashes",
            "tracks":result_tracks}


def update_leaderboard(leaderboard_path: Path, result: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Append only independently verified synthetic results and rank by F1."""
    if result.get("status") != "VERIFIED_SYNTHETIC" or result.get("schema_version") != "1":
        raise ValueError("only independently verified synthetic results may enter this leaderboard")
    if not run_id:
        raise ValueError("run_id is required")
    if leaderboard_path.exists():
        board = json.loads(leaderboard_path.read_text(encoding="utf-8"))
        if (board.get("dataset_id"), board.get("dataset_version")) != (result.get("dataset_id"), result.get("dataset_version")):
            raise ValueError("leaderboard dataset version mismatch; use a separate leaderboard")
    else:
        board = {"schema_version":"1", "dataset_id":result["dataset_id"], "dataset_version":result["dataset_version"], "entries":[]}
    if any(entry.get("run_id") == run_id for entry in board["entries"]):
        raise ValueError("run_id already exists on leaderboard")
    board["entries"].append({"run_id":run_id, "tracks":result["tracks"], "validation":result["validation"]})
    board["entries"].sort(key=lambda entry: (entry["tracks"]["agent_plus_tool"].get("f1") or 0,
                                               entry["tracks"]["agent_plus_tool"].get("fix_success_rate") or 0,
                                               entry["tracks"]["agent_plus_tool"].get("preservation_rate") or 0), reverse=True)
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    leaderboard_path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    return board


def render_gallery(dataset_path: Path, submission_path: Path, result_path: Path, output_path: Path) -> Path:
    """Write a self-contained static HTML report with local before/after images."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "VERIFIED_SYNTHETIC" or any(result.get(k) != dataset.get(k) for k in ("dataset_id", "dataset_version")):
        raise ValueError("gallery requires a verified result for this exact dataset version")
    if submission.get("dataset_id") != dataset.get("dataset_id") or submission.get("dataset_version") != dataset.get("dataset_version"):
        raise ValueError("submission dataset identity/version mismatch")
    checked = verify_synthetic_submission(dataset_path, submission_path)
    if checked != result:
        raise ValueError("result file does not match the independently re-measured submission")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base = output_path.resolve().parent

    def image_ref(path: Path) -> str:
        resolved = path.resolve()
        return html.escape(Path(os.path.relpath(resolved, base)).as_posix(), quote=True)

    rows = []
    for case in dataset["cases"]:
        images = []
        source = dataset_path.parent / case["faulty_asset"]
        images.append(("Original (faulty)", source))
        for track_name, label in (("agent_only", "Agent only"), ("agent_plus_tool", "Agent + I-mage-not-AI")):
            asset = submission["tracks"][track_name]["assets"][case["case_id"]]
            images.append((label, submission_path.parent / asset))
        figures = "".join(f'<figure><img src="{image_ref(path)}" alt="{html.escape(label)}: {html.escape(case["case_id"])}"><figcaption>{html.escape(label)}</figcaption></figure>' for label, path in images)
        rows.append(f'<article><h2>{html.escape(case["case_id"])} · {html.escape(case["injected_rule"])}</h2><div class="images">{figures}</div></article>')
    metric_rows = []
    for name, metrics in result["tracks"].items():
        metric_rows.append("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in (name, metrics.get("precision"), metrics.get("recall"), metrics.get("f1"), metrics.get("fix_success_rate"), metrics.get("preservation_rate", "—"))) + "</tr>")
    content = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>I-mage-not-AI benchmark</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#20242a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd;padding:.55rem;text-align:left}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}figure{margin:0}img{width:100%;image-rendering:pixelated;background:repeating-conic-gradient(#eee 0 25%,white 0 50%) 50%/16px 16px;border:1px solid #ccd}figcaption{padding:.4rem}article{margin:2rem 0;border-top:1px solid #ddd}small{color:#555}</style><body>""" + f"<h1>Synthetic benchmark · {html.escape(dataset['dataset_id'])} {html.escape(dataset['dataset_version'])}</h1><p><strong>Independently verified synthetic results.</strong> This report covers the dataset's injected constraints only.</p><table><thead><tr><th>Track</th><th>Precision</th><th>Recall</th><th>F1</th><th>Fix success</th><th>Preservation</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table>{''.join(rows)}<small>Generated from local benchmark artifacts; image paths are relative to this HTML file.</small></body></html>"
    output_path.write_text(content, encoding="utf-8")
    return output_path
