"""Read saved benchmark artifacts and reproduce the evaluation audit findings.

Run from the checkout: .venv/Scripts/python.exe artifacts/metric-audit-2026-10-31/reproduce_audit.py
Only audit-evidence.json beside this script is written. Inputs and source stay untouched.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-04"
DATA = ROOT / "benchmarks/datasets/icon-multimetric-v1"
GROUND = json.loads((RUN / "evaluator/ground-truth-map.json").read_text(encoding="utf-8"))["samples"]


def rgba(path):
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"))


def selected_results(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    return [{"rule": r["rule_id"], "value": r.get("measured"), "status": r["status"]}
            for r in report["results"] if r["rule_id"] in {"SYMMETRY-001", "OVERLAP-001"}]


def main():
    evidence = {"scope": "loop04; current source and saved reports; no new A/B run"}
    evidence["source_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("benchmarks/prepare_multimetric_icon_dataset.py", "benchmarks/prepare_multimetric_ab.py",
                     "benchmarks/score_multimetric_ab.py", "imreview/core.py", "imreview/measurements.py")}
    evidence["unique_clean_image_hashes"] = len({r["clean_sha256"] for r in GROUND.values()})
    evidence["unchanged_pixel_counterexamples"] = []
    for sid in ("sample-02", "sample-09"):
        source = RUN / "sessions/agent-only/inputs" / sid / "asset.png"
        output = RUN / "sessions/agent-only/outputs" / (sid + ".png")
        evidence["unchanged_pixel_counterexamples"].append({
            "sample": sid, "fault": GROUND[sid]["fault"],
            "rgba_identical": bool(np.array_equal(rgba(source), rgba(output))),
            "input_checks": selected_results(RUN / "evaluator/preflight-cli" / sid / "report.json"),
            "output_checks": selected_results(RUN / "evaluator/repair-reviews-agent-only" / sid / "report.json"),
        })
    evidence["threshold_only_predictions"] = []
    blank_scores = []
    evidence["margin_inverse_shift"] = []
    for sid, truth in GROUND.items():
        manifest = json.loads((RUN / "sessions/agent-cli/inputs" / sid / "manifest.json").read_text(encoding="utf-8"))
        center = manifest["constraints"]["max_normalized_centroid_offset"]
        symmetry = next(f for f in manifest["features"] if f["id"] == "gem-pair")["properties"]["min_symmetry_iou"]
        predicted = "center" if center < .1 else "symmetry" if symmetry > .9 else None
        if predicted:
            evidence["threshold_only_predictions"].append({"sample": sid, "predicted": predicted,
                "expected": truth["fault"], "correct": predicted == truth["fault"]})
        reference = rgba(DATA / truth["clean_asset"])
        blank_scores.append(float(np.all(reference == 0, axis=2).mean()))
        if truth["fault"] == "margin":
            with Image.open(RUN / "sessions/agent-cli/inputs" / sid / "asset.png") as image:
                original = image.convert("RGBA")
                restored = Image.new("RGBA", original.size)
                restored.paste(original, (-14, 0))
                evidence["margin_inverse_shift"].append({"sample": sid,
                    "original_alpha_bbox": original.getbbox(), "inverse_shift_x": -14,
                    "exact_clean_match": bool(np.array_equal(np.asarray(restored), reference))})
    evidence["blank_output_pixel_match"] = {"mean": float(np.mean(blank_scores)),
        "min": min(blank_scores), "max": max(blank_scores)}
    sys.path.insert(0, str(ROOT / "benchmarks"))
    from score_multimetric_ab import normalized_groups
    evidence["negative_statement_parser"] = {text: sorted(normalized_groups(text)) for text in (
        "No color defect was found.", "There is no overlap.", "No detached components.")}
    # Hypothetical independent Bernoulli success-rate intervals, NOT F1 intervals.
    evidence["hypothetical_iid_exact_95_intervals"] = {
        f"{k}/{n}": [float(beta.ppf(.025, k, n-k+1)),
                      1.0 if k == n else float(beta.ppf(.975, k+1, n-k))]
        for k, n in ((24, 24), (4, 4), (20, 24), (11, 24))}
    evidence["interval_warning"] = "These are success-rate intervals under an iid binomial model, not F1 intervals or generalization guarantees; this selected four-source dataset violates the intended sampling model."
    target = Path(__file__).with_name("audit-evidence.json")
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
