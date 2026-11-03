"""Compare scale consistency across multiple sprite sheets (Ludo sprite compare-style)."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from .sprite_metrics import aggregate_sheet_draw_height
from .sprite_sheet import _load_rgba, extract_frames, validate_sheet_layout

COMPARE_POLICY_KEYS = frozenset(
    {
        "reference_height_m",
        "max_relative_bbox_height_spread",
        "max_relative_ppu_spread",
        "reference_sheet_id",
        "shared_layout",
        "sheets",
    }
)


def validate_compare_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ValueError("compare policy must be a JSON object")
    unknown = set(policy) - COMPARE_POLICY_KEYS
    if unknown:
        raise ValueError(f"unknown compare policy keys: {sorted(unknown)}")
    default_height = policy.get("reference_height_m")
    for entry in policy.get("sheets", []):
        if "reference_height_m" not in entry and default_height is None:
            raise ValueError("reference_height_m is required at top level or on every sheet entry")
    if "max_relative_bbox_height_spread" not in policy and "max_relative_ppu_spread" not in policy:
        raise ValueError("compare policy must set max_relative_bbox_height_spread and/or max_relative_ppu_spread")
    sheets = policy.get("sheets")
    if not isinstance(sheets, list) or len(sheets) < 2:
        raise ValueError("sheets must list at least two entries")
    for entry in sheets:
        if not isinstance(entry, dict) or "id" not in entry or "path" not in entry:
            raise ValueError("each sheet entry requires id and path")
        layout = {**(policy.get("shared_layout") or {}), **entry.get("layout", {})}
        validate_sheet_layout(layout)
    return policy


def _relative_spread(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 0.0
    return (max(values) - min(values)) / mean


def compare_sprite_sheets(policy: Any, *, policy_dir: Path | None = None) -> dict[str, Any]:
    validate_compare_policy(policy)
    base_dir = (policy_dir or Path(".")).resolve()
    shared = dict(policy.get("shared_layout") or {})
    default_height_m = policy.get("reference_height_m")
    rows: list[dict[str, Any]] = []
    for entry in policy["sheets"]:
        sheet_id = str(entry["id"])
        rel = Path(str(entry["path"]))
        sheet_path = rel if rel.is_absolute() else (base_dir / rel).resolve()
        layout = {**shared, **entry.get("layout", {})}
        alpha_threshold = int(layout.get("alpha_threshold", 128))
        if not 0 <= alpha_threshold <= 255:
            raise ValueError(f"alpha_threshold must be between 0 and 255 for sheet {sheet_id!r}")
        height_m = float(entry.get("reference_height_m", default_height_m))
        if not math.isfinite(height_m) or height_m <= 0:
            raise ValueError(f"reference_height_m must be positive for sheet {sheet_id!r}")
        sheet_rgba, _file_meta = _load_rgba(sheet_path, {})
        frames = extract_frames(sheet_rgba, layout)
        if not frames:
            raise ValueError(f"sheet {sheet_id!r} produced zero frames")
        bbox_h = aggregate_sheet_draw_height(frames, alpha_threshold=alpha_threshold)
        ppu = bbox_h / height_m if height_m > 0 else None
        rows.append(
            {
                "id": sheet_id,
                "path": str(sheet_path),
                "sha256": hashlib.sha256(sheet_path.read_bytes()).hexdigest(),
                "frame_count": len(frames),
                "reference_height_m": height_m,
                "bbox_height_px": bbox_h,
                "pixels_per_meter": ppu,
            }
        )

    bbox_heights = [float(row["bbox_height_px"]) for row in rows]
    ppus = [float(row["pixels_per_meter"]) for row in rows if row["pixels_per_meter"] is not None]
    bbox_spread = _relative_spread(bbox_heights)
    ppu_spread = _relative_spread(ppus) if ppus else 0.0

    ref_id = policy.get("reference_sheet_id")
    ref_row = next((r for r in rows if r["id"] == ref_id), rows[0] if ref_id is None else None)
    if ref_id is not None and ref_row is None:
        raise ValueError(f"reference_sheet_id {ref_id!r} not found in sheets")

    findings: list[dict[str, Any]] = []
    if "max_relative_bbox_height_spread" in policy:
        limit = float(policy["max_relative_bbox_height_spread"])
        status = "PASS" if bbox_spread <= limit else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-COMPARE-BBOX",
                "algorithm": "sprite_sheet_bbox_height_spread",
                "status": status,
                "measured": {"relative_spread": bbox_spread, "bbox_heights_px": bbox_heights, "sheets": rows},
                "threshold": {"max_relative_bbox_height_spread": limit},
                "formula": "(max-min)/mean of per-sheet max frame bbox height",
            }
        )
    if "max_relative_ppu_spread" in policy:
        limit = float(policy["max_relative_ppu_spread"])
        status = "PASS" if ppu_spread <= limit else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-COMPARE-PPU",
                "algorithm": "sprite_sheet_ppu_spread",
                "status": status,
                "measured": {"relative_spread": ppu_spread, "pixels_per_meter": ppus, "sheets": rows},
                "threshold": {"max_relative_ppu_spread": limit},
                "formula": "(max-min)/mean of bbox_height_px/reference_height_m across sheets",
            }
        )

    complete = bool(findings) and all(row["status"] in {"PASS", "FAIL"} for row in findings)
    status = "FAIL" if any(row["status"] == "FAIL" for row in findings) else ("PASS" if complete else "INCONCLUSIVE")
    return {
        "schema_version": "0.5",
        "asset_type": "sprite_sheet_compare",
        "status": status,
        "completeness": "COMPLETE" if complete else "INCOMPLETE",
        "reference_sheet_id": ref_row["id"] if ref_row else None,
        "coverage": {
            "required": len(findings),
            "completed": sum(row["status"] in {"PASS", "FAIL"} for row in findings),
            "missing": [row["rule_id"] for row in findings if row["status"] not in {"PASS", "FAIL"}],
        },
        "results": findings,
    }
