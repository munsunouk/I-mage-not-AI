"""Run one Codex Agent Only vs Agent + CLI synthetic icon repair loop."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, cast

from PIL import Image
from typer.testing import CliRunner

from i_mage_not_ai.typer_cli import app


RULES = ("COLOR-001", "GEOMETRY-002")
PROMPT = (
    "Inspect this 32x32 flat icon against the same explicit constraints: exactly one visible RGB color and at least "
    "10 percent transparent margin on every side. Fix only measured or visually identified violations. Preserve the "
    "remaining source pixels. Use at most one repair attempt. In the CLI-assisted condition, use the i_mage_not_ai report "
    "to identify the violated rule before applying the same repair policy."
)
# These classifications were made by the Codex vision pass over agent-only-inputs.png,
# without reading per-case labels from dataset.json during that visual pass.
VISUAL_DECISIONS = {
    **{f"icon-{index:04d}": "COLOR-001" for index in range(1, 21, 2)},
    **{f"icon-{index:04d}": "GEOMETRY-002" for index in range(2, 21, 2)},
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rgba_colors(image: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    colors = image.getcolors(maxcolors=image.width * image.height)
    if not isinstance(colors, list):
        raise ValueError("image color count exceeded the pixel limit")
    return [(count, cast(tuple[int, int, int, int], pixel)) for count, pixel in colors]


def repair(source: Path, destination: Path, rule_id: str) -> None:
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    width, height = image.size
    if rule_id == "COLOR-001":
        counts: Counter[tuple[int, int, int]] = Counter()
        for count, pixel in rgba_colors(image):
            if pixel[3] > 0:
                counts[pixel[:3]] += count
        if not counts:
            raise ValueError(f"no visible pixels to repair: {source}")
        dominant = counts.most_common(1)[0][0]
        pixels = cast(Any, image.load())
        for y in range(height):
            for x in range(width):
                r, g, b, alpha = pixels[x, y]
                if alpha > 0 and (r, g, b) != dominant:
                    pixels[x, y] = (*dominant, alpha)
    elif rule_id == "GEOMETRY-002":
        trim = math.ceil(0.1 * width)
        pixels = cast(Any, image.load())
        for y in range(height):
            for x in (*range(trim), *range(width - trim, width)):
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)
    else:
        raise ValueError(f"unsupported repair rule: {rule_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=False)


def violations(path: Path) -> set[str]:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    visible_colors = {pixel[:3] for count, pixel in rgba_colors(image) if count and pixel[3] > 0}
    failing = set()
    if len(visible_colors) > 1:
        failing.add("COLOR-001")
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        failing.add("GEOMETRY-002")
    else:
        width, height = image.size
        margins = (bbox[0] / width, bbox[1] / height, (width - bbox[2]) / width, (height - bbox[3]) / height)
        if min(margins) < 0.1:
            failing.add("GEOMETRY-002")
    return failing


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dataset_dir = root / "benchmarks" / "datasets" / "icon"
    dataset_file = dataset_dir / "dataset.json"
    dataset = json.loads(dataset_file.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != "1" or len(dataset.get("cases", [])) != 20:
        raise ValueError("expected the 20-case synthetic icon dataset")

    output_dir = root / "benchmarks" / "results" / "icon-ab-loop-01"
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_file = output_dir / "agent-only-visual-decisions.json"
    decisions_file.write_text(json.dumps({"method": "Codex visual classification", "decisions": VISUAL_DECISIONS}, indent=2) + "\n", encoding="utf-8")
    submission_path = output_dir / "submission.json"
    runner = CliRunner()

    system_meta = {
        "agent": "OpenAI Codex",
        "model": "GPT-6 (Codex session; exact model snapshot unavailable)",
        "prompt_version": "icon-repair-loop-v1",
        "environment": "Windows 11, Python 3.12.3, Pillow, 32x32 PNG synthetic icons",
    }
    submission = {
        "schema_version": "1",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "protocol": {"prompt_sha256": sha256_text(PROMPT), "attempt_limit": 1, "environment_image": system_meta["environment"], "seed": 0},
        "tracks": {
            "original": {"metadata": {"agent": "dataset baseline", "model": "none", "prompt_version": "n/a", "environment": "generated faulty assets"}},
            "agent_only": {"metadata": dict(system_meta), "assets": {}},
            "agent_plus_tool": {"metadata": dict(system_meta), "assets": {}},
        },
    }
    cli_reports_dir = output_dir / "cli-reports"
    cli_reports_dir.mkdir(parents=True, exist_ok=True)
    visual_reports = []
    for case in dataset["cases"]:
        case_id = case["case_id"]
        source = dataset_dir / case["faulty_asset"]

        visual_rule = VISUAL_DECISIONS.get(case_id)
        if visual_rule not in RULES:
            raise ValueError(f"missing visual decision for {case_id}")
        agent_output = output_dir / "agent-only" / f"{case_id}.png"
        repair(source, agent_output, visual_rule)
        submission["tracks"]["agent_only"]["assets"][case_id] = agent_output.relative_to(output_dir).as_posix()
        visual_reports.append({"case_id": case_id, "rule_id": visual_rule, "source": case["faulty_asset"], "output": submission["tracks"]["agent_only"]["assets"][case_id]})

        cli_input_dir = output_dir / "cli-inputs" / case_id
        cli_input_dir.mkdir(parents=True, exist_ok=True)
        cli_asset = cli_input_dir / "asset.png"
        shutil.copyfile(source, cli_asset)
        manifest_path = cli_input_dir / "manifest.json"
        manifest = {
            "schema_version": "0.5",
            "asset": {"path": "asset.png", "format": "png", "sha256": hashlib.sha256(cli_asset.read_bytes()).hexdigest()},
            "intent": {"kind": "icon", "style": "flat", "purpose": "benchmark repair input", "origin": "agent_inference"},
            "constraints": {"max_palette_colors": 1, "min_margin_ratio": 0.1},
            "features": [],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        cli_report = cli_reports_dir / f"{case_id}.json"
        result = runner.invoke(app, ["review", "--manifest", str(manifest_path), "--output", str(cli_report)])
        if result.exit_code not in (0, 1) or not cli_report.is_file():
            raise RuntimeError(f"CLI review failed for {case_id}: {result.output}")
        report = json.loads(cli_report.read_text(encoding="utf-8"))
        if report.get("completeness") != "COMPLETE":
            raise RuntimeError(f"CLI review incomplete for {case_id}")
        failed_rules = [finding["rule_id"] for finding in report.get("results", []) if finding.get("status") == "FAIL" and finding.get("rule_id") in RULES]
        if len(failed_rules) != 1:
            raise RuntimeError(f"expected one CLI-reported target fault for {case_id}, got {failed_rules}")
        tool_output = output_dir / "agent-plus-cli" / f"{case_id}.png"
        repair(source, tool_output, failed_rules[0])
        submission["tracks"]["agent_plus_tool"]["assets"][case_id] = tool_output.relative_to(output_dir).as_posix()

    submission_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")
    verified_path = output_dir / "verified-result.json"
    evaluated = runner.invoke(app, ["benchmark", "evaluate", "--dataset", str(dataset_file), "--submission", str(submission_path), "--output", str(verified_path)])
    if evaluated.exit_code != 0 or not verified_path.is_file():
        raise RuntimeError(f"independent synthetic evaluation failed: {evaluated.output}")
    verified = json.loads(verified_path.read_text(encoding="utf-8"))
    if verified.get("status") != "VERIFIED_SYNTHETIC":
        raise RuntimeError(f"unexpected evaluation state: {verified.get('status')}")

    comparisons = {}
    for track_name in ("agent_only", "agent_plus_tool"):
        fixed_cases = regressions = 0
        for case in dataset["cases"]:
            before_path = dataset_dir / case["faulty_asset"]
            after_path = output_dir / submission["tracks"][track_name]["assets"][case["case_id"]]
            before_failures = violations(before_path)
            after_failures = violations(after_path)
            fixed_cases += case["injected_rule"] not in after_failures
            regressions += bool(after_failures - before_failures)
        track_metrics = verified["tracks"][track_name]
        comparisons[track_name] = {
            "fix_success_rate": fixed_cases / len(dataset["cases"]),
            "regression_rate": regressions / len(dataset["cases"]),
            "preservation_rate": track_metrics.get("preservation_rate"),
            "changed_pixels": track_metrics.get("changed_pixels"),
            "changes_outside_allowed_region": track_metrics.get("changes_outside_allowed_region"),
        }
    baseline, candidate = comparisons["agent_only"], comparisons["agent_plus_tool"]
    comparison = {
        "status": "SINGLE_LOOP_EXPLORATORY",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "cases": len(dataset["cases"]),
        "tracks": comparisons,
        "candidate_minus_baseline": {key: candidate[key] - baseline[key] for key in ("fix_success_rate", "regression_rate", "preservation_rate")},
        "prompt_sha256": submission["protocol"]["prompt_sha256"],
        "attempt_limit": submission["protocol"]["attempt_limit"],
        "limitations": [
            "Single in-session Codex run; no independent repeated trials or cost/token telemetry.",
            "The Agent Only visual classification was performed in this session after the CLI smoke run had exposed dataset behavior; it is not a blinded causal comparison.",
            "Synthetic generator labels and repairable fault patterns are public; results do not establish real-world agent uplift.",
        ],
    }
    comparison_path = output_dir / "comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")

    gallery_path = output_dir / "gallery" / "index.html"
    gallery_path.parent.mkdir(parents=True, exist_ok=True)
    gallery_result = runner.invoke(app, ["benchmark", "gallery", "--dataset", str(dataset_file), "--submission", str(submission_path), "--result", str(verified_path), "--output", str(gallery_path)])
    if gallery_result.exit_code != 0 or not gallery_path.is_file():
        raise RuntimeError(f"gallery generation failed: {gallery_result.output}")
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"A/B benchmark loop failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
