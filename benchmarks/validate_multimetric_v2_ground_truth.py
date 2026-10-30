"""Independent pixel-level gold-label audit for v2; never imported by an arm."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "benchmarks/results/icon-multimetric-isolated-loop-05"


def load(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGBA"), dtype=np.uint8).copy()


def label_components(mask: np.ndarray) -> int:
    # Independent stack flood-fill implementation using 8-connectivity.
    seen = np.zeros(mask.shape, dtype=np.bool_)
    height, width = mask.shape
    total = 0
    for row in range(height):
        for col in range(width):
            if not mask[row, col] or seen[row, col]:
                continue
            total += 1
            seen[row, col] = True
            stack = [(row, col)]
            while stack:
                y, x = stack.pop()
                for ny in range(max(0, y - 1), min(height, y + 2)):
                    for nx in range(max(0, x - 1), min(width, x + 2)):
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
    return total


def measure(path: Path, limits: dict) -> dict:
    rgba = load(path)
    alpha = rgba[:, :, 3].astype(np.float64)
    h, w = alpha.shape
    ys, xs = np.nonzero(alpha)
    if len(xs):
        weights = alpha[ys, xs]
        xbar = float(np.dot(xs + 0.5, weights) / weights.sum())
        ybar = float(np.dot(ys + 0.5, weights) / weights.sum())
        offset = math.hypot((xbar - w / 2) / w, (ybar - h / 2) / h)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max() + 1), int(ys.min()), int(ys.max() + 1)
        margins = {"left": x0 / w, "top": y0 / h, "right": (w - x1) / w, "bottom": (h - y1) / h}
    else:
        offset, margins = None, {"left": None, "top": None, "right": None, "bottom": None}
    visible = alpha > 0
    palette = len(np.unique(rgba[:, :, :3][visible], axis=0)) if visible.any() else 0
    components = label_components(visible)
    fails = []
    if offset is not None and offset > limits["max_centroid"]:
        fails.append("GEOMETRY-001")
    if min(x for x in margins.values() if x is not None) < 0.03:
        fails.append("GEOMETRY-002")
    if palette > limits["max_palette"]:
        fails.append("COLOR-001")
    if components > limits["components"]:
        fails.extend(("TOPOLOGY-001", "CHARACTER-002"))
    return {"centroid_offset": offset, "margins": margins, "palette_colors": palette,
            "components_8_connected": components, "expected_rules": sorted(fails)}


def main() -> None:
    ds = json.loads((ROOT / "benchmarks/datasets/icon-multimetric-v2/dataset.json").read_text(encoding="utf-8"))
    truth_map = json.loads((RUN / "evaluator/ground-truth-map.json").read_text(encoding="utf-8"))
    expected_by_sid = {}
    rows = []
    cli_exact = 0
    for sid, hidden in sorted(truth_map["samples"].items()):
        manifest = RUN / "sessions/agent-only/inputs" / sid / "manifest.json"
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        limits = {"max_centroid": meta["constraints"]["max_normalized_centroid_offset"],
                  "max_palette": meta["constraints"]["max_palette_colors"],
                  "components": meta["features"][0]["properties"]["max_connected_components"]}
        image = RUN / "sessions/agent-only/inputs" / sid / "asset.png"
        result = measure(image, limits)
        expected_by_sid[sid] = result["expected_rules"]
        cli_report = json.loads((RUN / "sessions/agent-cli/outputs/cli-reports" / f"{sid}.json").read_text(encoding="utf-8"))
        cli_rules = sorted({x["rule_id"] for x in cli_report["results"] if x.get("status") == "FAIL"})
        cli_exact += cli_rules == result["expected_rules"]
        rows.append({"sample_id": sid, "case_id": hidden["case_id"], "declared_rules": hidden["expected_rules"],
                     "cli_rules": cli_rules, **result})
    mismatches = [r for r in rows if sorted(r["declared_rules"]) != r["expected_rules"]]
    if mismatches:
        raise RuntimeError("independent pixel gold disagrees with intended fault labels: " + json.dumps(mismatches))
    for sid, rules in expected_by_sid.items():
        truth_map["samples"][sid]["expected_rules"] = rules
    (RUN / "evaluator/ground-truth-map.json").write_text(json.dumps(truth_map, indent=2) + "\n", encoding="utf-8")
    out = {"method": "separate NumPy/8-neighbor flood-fill recomputation from input pixels and clean-derived limits; CLI report statuses are compared only after gold calculation",
           "samples": len(rows), "declared_label_mismatches": len(mismatches), "gold_matches_intended_mutations": True,
           "cli_exact_rule_set_matches_independent_gold": cli_exact, "cli_preflight_conformance_rate": cli_exact / len(rows),
           "measurements": rows}
    (RUN / "evaluator/independent-ground-truth-audit.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "measurements"}, indent=2))


if __name__ == "__main__":
    main()
