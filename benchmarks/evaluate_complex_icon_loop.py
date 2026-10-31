"""Blind-session evaluator for the complex fantasy icon repair loop."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

from PIL import Image


ALIASES = {
    "COLOR-001": "COLOR-001", "exact_palette_count": "COLOR-001",
    "single_visible_rgb_color": "COLOR-001", "palette": "COLOR-001",
    "color limit": "COLOR-001", "palette limit": "COLOR-001",
    "color fleck": "COLOR-001", "visible palette": "COLOR-001",
    "exceeded by one color": "COLOR-001",
    "GEOMETRY-002": "GEOMETRY-002", "alpha_margin_ratio": "GEOMETRY-002",
    "transparent_margin": "GEOMETRY-002", "margin": "GEOMETRY-002",
    "displacement": "GEOMETRY-002", "edge margin": "GEOMETRY-002",
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(path: Path, limits: dict[str, Any]) -> dict[str, Any]:
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
    pixels = list(image.getdata())
    palette = len({pixel[:3] for pixel in pixels if pixel[3] > 0})
    bbox = image.getchannel("A").getbbox()
    margins = None if bbox is None else [bbox[0] / width, bbox[1] / height,
                                           (width - bbox[2]) / width, (height - bbox[3]) / height]
    min_margin = min(margins) if margins else 0.0
    return {
        "width": width, "height": height, "visible_palette_colors": palette,
        "max_palette_colors": limits["max_palette_colors"],
        "palette_pass": 0 < palette <= limits["max_palette_colors"],
        "edge_margins": margins, "minimum_edge_margin": min_margin,
        "required_min_margin_ratio": limits["min_margin_ratio"],
        "margin_pass": margins is not None and min_margin >= limits["min_margin_ratio"],
    }


def predicted_rules(decisions: Any) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if isinstance(decisions, dict):
        for sample_id, row in decisions.items():
            items = (row.get("diagnosis") or row.get("diagnosed_issue") or
                     row.get("diagnosed_issues") or row.get("issue") or []) if isinstance(row, dict) else row
            if isinstance(items, str):
                items = [items]
            found: set[str] = set()
            for item in items or []:
                if isinstance(item, dict):
                    item = item.get("rule_id") or item.get("rule") or item.get("issue") or ""
                val = str(item)
                for alias, rule in ALIASES.items():
                    if alias.lower() in val.lower():
                        found.add(rule)
            result[sample_id] = found
    return result


def score_diagnosis(expected: dict[str, str], predicted: dict[str, set[str]]) -> dict[str, Any]:
    truth = {(sample, rule) for sample, rule in expected.items()}
    guesses = {(sample, rule) for sample, rules in predicted.items() for rule in rules}
    tp, fp, fn = len(truth & guesses), len(guesses - truth), len(truth - guesses)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    root = repo / "benchmarks/results/complex-icon-isolated-loop-02"
    dataset_dir = repo / "benchmarks/datasets/complex-icon-v1"
    dataset = read(dataset_dir / "dataset.json")
    mapping = read(root / "evaluator/ground-truth-map.json")["samples"]
    case_by_id = {case["case_id"]: case for case in dataset["cases"]}
    by_sample = {row["sample_id"]: case_by_id[row["case_id"]] for row in mapping}
    expected = {row["sample_id"]: row["injected_rule"] for row in mapping}
    tracks: dict[str, Any] = {}
    all_rows = []

    for track, folder in (("agent_only", "agent-only"), ("agent_plus_cli", "agent-cli")):
        decisions_file = root / folder / "decisions.json"
        decisions = read(decisions_file)
        diag = score_diagnosis(expected, predicted_rules(decisions))
        repair_counts = {"palette_pass": 0, "margin_pass": 0, "both_pass": 0,
                         "dimensions_preserved": 0, "pixel_match_to_clean_total": 0,
                         "clean_pixel_total": 0}
        per_sample = []
        for sample_id, case in by_sample.items():
            output_path = root / folder / f"{sample_id}.png"
            clean_path = dataset_dir / case["clean_asset"]
            limits = case["requirements"]
            m = measure(output_path, limits)
            with Image.open(output_path) as im:
                after = im.convert("RGBA")
            with Image.open(clean_path) as im:
                clean = im.convert("RGBA")
            dims_ok = after.size == (128, 128)
            exact = sum(a == b for a, b in zip(after.getdata(), clean.getdata())) if after.size == clean.size else 0
            clean_total = clean.width * clean.height
            repair_pass = dims_ok and m["palette_pass"] and m["margin_pass"]
            repair_counts["palette_pass"] += m["palette_pass"]
            repair_counts["margin_pass"] += m["margin_pass"]
            repair_counts["both_pass"] += repair_pass
            repair_counts["dimensions_preserved"] += dims_ok
            repair_counts["pixel_match_to_clean_total"] += exact
            repair_counts["clean_pixel_total"] += clean_total
            row = {"sample_id": sample_id, "case_id": case["case_id"],
                   "injected_rule": expected[sample_id], "output": f"{folder}/{sample_id}.png",
                   "measurements": m, "repair_pass": repair_pass,
                   "exact_pixels_matching_clean": exact, "pixel_match_ratio": exact / clean_total}
            per_sample.append(row)
            all_rows.append(row)
        n = len(per_sample)
        tracks[track] = {
            "diagnosis": diag,
            "repair": {
                "palette_limit_pass_rate": repair_counts["palette_pass"] / n,
                "margin_limit_pass_rate": repair_counts["margin_pass"] / n,
                "both_limits_pass_rate": repair_counts["both_pass"] / n,
                "dimension_preservation_rate": repair_counts["dimensions_preserved"] / n,
                "mean_exact_pixel_match_to_clean": repair_counts["pixel_match_to_clean_total"] / repair_counts["clean_pixel_total"],
                "cases_passing_both": repair_counts["both_pass"], "cases": n,
            },
            "per_sample": per_sample,
        }

    cli_rows = []
    for item in mapping:
        report_path = root / "agent-cli/reports" / item["sample_id"] / "report.json"
        source_path = root / "inputs" / f"{item['sample_id']}.png"
        report = read(report_path)
        if report.get("completeness") != "COMPLETE" or report.get("asset", {}).get("sha256") != item["asset_sha256"]:
            raise ValueError(f"incomplete or wrong-asset CLI report: {item['sample_id']}")
        statuses = {row["rule_id"]: row["status"] for row in report.get("results", [])}
        rule = item["injected_rule"]
        cli_rows.append({"sample_id": item["sample_id"], "expected_rule": rule,
                         "expected_rule_failed": statuses.get(rule) == "FAIL",
                         "other_rule_passed": statuses.get("GEOMETRY-002" if rule == "COLOR-001" else "COLOR-001") == "PASS",
                         "asset_sha256": report["asset"]["sha256"], "input_sha256": sha256(source_path),
                         "completeness": report["completeness"]})
    if len(cli_rows) != len(mapping) or not all(r["expected_rule_failed"] and r["other_rule_passed"] for r in cli_rows):
        raise ValueError("Agent + CLI reports failed the dataset preflight contract")

    output = {
        "status": "ISOLATED_SINGLE_LOOP_EXPLORATORY",
        "dataset_id": dataset["dataset_id"], "dataset_version": dataset["dataset_version"],
        "complex_icon_cases": len(mapping), "cli_reports_validated": len(cli_rows),
        "session_isolation": {
            "agent_only_thread_id": "01a18d10-dd8b-7541-8236-fd9bbc713e34",
            "agent_plus_cli_thread_id": "01a18d10-e264-7b33-bf05-02d649572db6",
            "separate_projectless_threads": True,
            "ground_truth_mapping_exposed": False,
            "filesystem_isolation": "procedural, not OS-enforced",
        },
        "tracks": tracks,
        "agent_plus_cli_minus_agent_only": {
            metric: tracks["agent_plus_cli"][family][metric] - tracks["agent_only"][family][metric]
            for family, metrics in (("diagnosis", ("precision", "recall", "f1")),
                                    ("repair", ("both_limits_pass_rate", "mean_exact_pixel_match_to_clean")))
            for metric in metrics
        },
        "cli_report_validation": {"all_expected_findings_fail": True,
                                  "all_other_rule_findings_pass": True, "reports": cli_rows},
        "limitations": [
            "One exploratory run on 20 generated RPG inventory icons; it does not establish general image quality.",
            "Both sessions were projectless with independent conversation histories; filesystem isolation was procedural, not OS-enforced.",
            "The dataset is synthetic and its palette and margin rules are explicit; semantic quality and human preference were not scored.",
            "Exact model snapshot, token usage, and API cost were unavailable.",
        ],
    }
    (root / "comparison.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "tracks": {
        key: {"diagnosis": value["diagnosis"], "repair": value["repair"]}
        for key, value in tracks.items()}, "delta": output["agent_plus_cli_minus_agent_only"]}, indent=2))

    # Contact sheet and static gallery use the verified evaluator outputs.
    from PIL import ImageDraw
    cell_w, cell_h = 440, 190
    sheet = Image.new("RGB", (cell_w * 3, cell_h * 7), "#ededed")
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(all_rows[:20]):
        x, y = (idx % 3) * cell_w, (idx // 3) * cell_h
        draw.rectangle((x + 2, y + 2, x + cell_w - 3, y + cell_h - 3), fill="white", outline="#888")
        draw.text((x + 8, y + 6), f"{row['sample_id']} · {row['injected_rule']}", fill="#111")
        for col, (label, path) in enumerate((
            ("Before", root / "inputs" / f"{row['sample_id']}.png"),
            ("Agent Only", root / "agent-only" / f"{row['sample_id']}.png"),
            ("Agent + CLI", root / "agent-cli" / f"{row['sample_id']}.png"),
        )):
            with Image.open(path) as src:
                icon = src.convert("RGBA").resize((120, 120), Image.Resampling.NEAREST)
            bg = Image.new("RGBA", icon.size, "#d8d8d8"); bg.alpha_composite(icon)
            px, py = x + 8 + col * 140, y + 25
            sheet.paste(bg.convert("RGB"), (px, py)); draw.text((px, py + 122), label, fill="#111")
    sheet.save(root / "comparison-contact-sheet.png")

    rows_html = []
    for row in all_rows[:20]:
        sid = row["sample_id"]
        figures = "".join(f'<figure><img src="{html.escape(path)}"><figcaption>{label}</figcaption></figure>'
                          for path, label in ((f"inputs/{sid}.png", "Before"),
                                              (f"agent-only/{sid}.png", "Agent Only"),
                                              (f"agent-cli/{sid}.png", "Agent + CLI")))
        rows_html.append(f'<article><h2>{sid} · {row["injected_rule"]}</h2><div class="images">{figures}</div></article>')
    table_rows = "".join(
        f'<tr><th>{label}</th><td>{value["diagnosis"]["precision"]:.0%} / {value["diagnosis"]["recall"]:.0%} / {value["diagnosis"]["f1"]:.0%}</td>'
        f'<td>{value["repair"]["cases_passing_both"]}/20</td><td>{value["repair"]["mean_exact_pixel_match_to_clean"]:.1%}</td></tr>'
        for label, value in (("Agent Only", tracks["agent_only"]), ("Agent + CLI", tracks["agent_plus_cli"]))
    )
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Complex icon isolated benchmark</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#20242a}table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #ccd;padding:.55rem;text-align:left}article{margin:2rem 0;border-top:1px solid #ddd;padding-top:1rem}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}figure{margin:0}img{width:100%;image-rendering:pixelated;background:repeating-conic-gradient(#eee 0 25%,white 0 50%) 50%/16px 16px;border:1px solid #ccd}figcaption{padding:.4rem}</style><body>'
            '<h1>Complex fantasy inventory icons · isolated single loop</h1><p>Diagnosis P/R/F1; repairs pass if both measurable image limits are met. Pixel match compares the repaired raster with the evaluator-only clean source.</p>'
            '<table><thead><tr><th>Condition</th><th>Diagnosis P / R / F1</th><th>Both limits pass</th><th>Exact pixels matching clean source</th></tr></thead><tbody>'
            + table_rows + '</tbody></table><p>One synthetic loop; semantic fidelity and preference were not evaluated. Projectless conversation histories were separate; filesystem isolation was procedural.</p>'
            + ''.join(rows_html) + '</body></html>')
    (root / "comparison.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
