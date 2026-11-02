"""Deterministic sprite atlas / strip checks (no learned metrics)."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

SPRITE_SHEET_POLICY_KEYS = frozenset(
    {
        "layout",
        "frame_width",
        "frame_height",
        "columns",
        "frame_count",
        "alpha_threshold",
        "max_baseline_y_variance",
        "max_bbox_height_variance",
        "max_inter_frame_changed_pixel_ratio",
        "pixel_delta_threshold",
        "require_palette_subset_of_first_frame",
        "reference_frame_index",
        "max_reference_changed_pixel_ratio",
    }
)


def validate_sheet_layout(policy: dict[str, Any], *, layout_key: str = "layout") -> None:
    layout = policy.get(layout_key, "horizontal_strip")
    if layout not in {"horizontal_strip", "grid"}:
        raise ValueError(f"{layout_key} must be horizontal_strip or grid")
    for key in ("frame_width", "frame_height"):
        if key not in policy:
            raise ValueError(f"{key} is required")
        value = policy[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if layout == "grid":
        columns = policy.get("columns")
        if not isinstance(columns, int) or isinstance(columns, bool) or columns <= 0:
            raise ValueError("columns must be a positive integer when layout=grid")
    if "frame_count" in policy:
        count = policy["frame_count"]
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError("frame_count must be a positive integer")


def validate_sprite_sheet_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict) or not policy:
        raise ValueError("sprite sheet policy must define at least one explicit check")
    unknown = set(policy) - SPRITE_SHEET_POLICY_KEYS
    if unknown:
        raise ValueError(f"unknown sprite sheet policy keys: {sorted(unknown)}")
    validate_sheet_layout(policy)
    structural = {"layout", "frame_width", "frame_height", "columns", "frame_count", "alpha_threshold", "pixel_delta_threshold", "reference_frame_index"}
    if not set(policy) - structural:
        raise ValueError("sprite sheet policy must include at least one explicit check")
    return policy


def _load_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.format not in {"PNG", "WEBP"}:
            raise ValueError("sprite sheet must be PNG or WebP")
        return np.asarray(image.convert("RGBA"), dtype=np.uint8)


def extract_frames(sheet: np.ndarray, policy: dict[str, Any]) -> list[np.ndarray]:
    layout = policy.get("layout", "horizontal_strip")
    fw, fh = int(policy["frame_width"]), int(policy["frame_height"])
    height, width = sheet.shape[:2]
    if layout == "horizontal_strip":
        if width % fw != 0:
            raise ValueError("sheet width must be a multiple of frame_width")
        columns = width // fw
        rows = height // fh
        if height != fh:
            raise ValueError("horizontal_strip requires sheet height to equal frame_height")
    else:
        columns = int(policy["columns"])
        if width != columns * fw or height % fh != 0:
            raise ValueError("grid layout requires sheet dimensions to align with frame size and columns")
        rows = height // fh
    total = columns * rows
    if "frame_count" in policy:
        total = min(total, int(policy["frame_count"]))
    frames: list[np.ndarray] = []
    index = 0
    for row in range(rows):
        for col in range(columns):
            if index >= total:
                return frames
            x0, y0 = col * fw, row * fh
            frames.append(sheet[y0 : y0 + fh, x0 : x0 + fw].copy())
            index += 1
    return frames


def _alpha_mask(frame: np.ndarray, threshold: int) -> np.ndarray:
    return frame[:, :, 3] >= threshold


def _bbox_height(mask: np.ndarray) -> int:
    ys = np.where(mask.any(axis=1))[0]
    if len(ys) == 0:
        return 0
    return int(ys[-1] - ys[0] + 1)


def _baseline_y(mask: np.ndarray) -> float | None:
    rows = np.where(mask.any(axis=1))[0]
    if len(rows) == 0:
        return None
    return float(rows[-1])


def _palette(frame: np.ndarray, mask: np.ndarray) -> set[tuple[int, int, int]]:
    rgb = frame[mask][:, :3]
    if len(rgb) == 0:
        return set()
    return {tuple(int(v) for v in row) for row in rgb}


def _changed_pixel_ratio(left: np.ndarray, right: np.ndarray, threshold: int) -> float:
    delta = np.max(np.abs(right.astype(np.int16) - left.astype(np.int16)), axis=2)
    return float(np.mean(delta >= threshold))


def analyze_sprite_sheet(sheet_path: Path, policy: Any) -> dict[str, Any]:
    validate_sprite_sheet_policy(policy)
    sheet = _load_rgba(sheet_path.resolve())
    frames = extract_frames(sheet, policy)
    if len(frames) < 1:
        raise ValueError("sprite sheet produced zero frames")
    alpha_threshold = int(policy.get("alpha_threshold", 128))
    if not 0 <= alpha_threshold <= 255:
        raise ValueError("alpha_threshold must be between 0 and 255")
    findings: list[dict[str, Any]] = []

    if "max_baseline_y_variance" in policy or "max_bbox_height_variance" in policy:
        baselines: list[float] = []
        heights: list[int] = []
        for frame in frames:
            mask = _alpha_mask(frame, alpha_threshold)
            baseline = _baseline_y(mask)
            if baseline is not None:
                baselines.append(baseline)
            heights.append(_bbox_height(mask))
        if "max_baseline_y_variance" in policy:
            limit = policy["max_baseline_y_variance"]
            if not isinstance(limit, (int, float)) or isinstance(limit, bool) or not math.isfinite(limit) or limit < 0:
                raise ValueError("max_baseline_y_variance must be a non-negative finite number")
            if len(baselines) < 2:
                status, measured = "INCONCLUSIVE", {"baseline_y_values": baselines}
            else:
                variance = float(np.var(baselines))
                measured = {"baseline_y_values": baselines, "variance": variance}
                status = "PASS" if variance <= limit else "FAIL"
            findings.append(
                {
                    "rule_id": "SPRITE-BASELINE-Y",
                    "algorithm": "sprite_baseline_y_variance",
                    "status": status,
                    "measured": measured,
                    "threshold": {"max_variance": limit},
                    "formula": "variance of bottom opaque row index per frame",
                }
            )
        if "max_bbox_height_variance" in policy:
            limit = policy["max_bbox_height_variance"]
            if not isinstance(limit, (int, float)) or isinstance(limit, bool) or not math.isfinite(limit) or limit < 0:
                raise ValueError("max_bbox_height_variance must be a non-negative finite number")
            if len(heights) < 2:
                status, measured = "INCONCLUSIVE", {"bbox_heights": heights}
            else:
                variance = float(np.var(heights))
                measured = {"bbox_heights": heights, "variance": variance}
                status = "PASS" if variance <= limit else "FAIL"
            findings.append(
                {
                    "rule_id": "SPRITE-BBOX-HEIGHT",
                    "algorithm": "sprite_bbox_height_variance",
                    "status": status,
                    "measured": measured,
                    "threshold": {"max_variance": limit},
                    "formula": "variance of alpha bbox height per frame",
                }
            )

    if policy.get("require_palette_subset_of_first_frame"):
        first = _palette(frames[0], _alpha_mask(frames[0], alpha_threshold))
        violations = []
        for index, frame in enumerate(frames[1:], start=1):
            palette = _palette(frame, _alpha_mask(frame, alpha_threshold))
            extra = sorted(palette - first)
            if extra:
                violations.append({"frame_index": index, "extra_colors": extra[:8], "extra_count": len(extra)})
        status = "PASS" if not violations else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-PALETTE-SUBSET",
                "algorithm": "sprite_inter_frame_palette_subset",
                "status": status,
                "measured": {"first_frame_color_count": len(first), "violating_frames": violations},
                "threshold": {"require_subset": True},
                "formula": "each frame opaque RGB set must be subset of frame 0 palette",
            }
        )

    if "max_inter_frame_changed_pixel_ratio" in policy:
        maximum = policy["max_inter_frame_changed_pixel_ratio"]
        threshold = int(policy.get("pixel_delta_threshold", 1))
        if not isinstance(maximum, (int, float)) or isinstance(maximum, bool) or not math.isfinite(maximum) or not 0 <= maximum <= 1:
            raise ValueError("max_inter_frame_changed_pixel_ratio must be between 0 and 1")
        if not isinstance(threshold, int) or isinstance(threshold, bool) or not 1 <= threshold <= 255:
            raise ValueError("pixel_delta_threshold must be an integer from 1 to 255")
        if len(frames) < 2:
            status, measured = "INCONCLUSIVE", None
        else:
            ratios = [_changed_pixel_ratio(frames[i], frames[i + 1], threshold) for i in range(len(frames) - 1)]
            max_ratio = max(ratios)
            measured = {"max_ratio": max_ratio, "per_interval": ratios, "changed_pixel_threshold_rgba": threshold}
            status = "PASS" if max_ratio <= maximum else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-FRAME-DELTA",
                "algorithm": "sprite_inter_frame_changed_pixel_ratio",
                "status": status,
                "measured": measured,
                "threshold": {"max_ratio": maximum},
                "formula": "max channel abs delta across RGBA between adjacent frames / pixel count",
            }
        )

    ref_index = policy.get("reference_frame_index")
    if "max_reference_changed_pixel_ratio" in policy:
        maximum = policy["max_reference_changed_pixel_ratio"]
        threshold = int(policy.get("pixel_delta_threshold", 1))
        if ref_index is None:
            raise ValueError("reference_frame_index is required with max_reference_changed_pixel_ratio")
        if not isinstance(ref_index, int) or isinstance(ref_index, bool) or ref_index < 0:
            raise ValueError("reference_frame_index must be a non-negative integer")
        if ref_index >= len(frames):
            raise ValueError("reference_frame_index out of range")
        ratios = [_changed_pixel_ratio(frames[ref_index], frames[i], threshold) for i in range(len(frames)) if i != ref_index]
        max_ratio = max(ratios) if ratios else 0.0
        status = "PASS" if max_ratio <= maximum else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-REFERENCE-DELTA",
                "algorithm": "sprite_reference_frame_changed_pixel_ratio",
                "status": status,
                "measured": {"reference_frame_index": ref_index, "max_ratio": max_ratio, "per_frame": ratios},
                "threshold": {"max_ratio": maximum},
                "formula": "changed pixel ratio vs reference frame for every other frame",
            }
        )

    complete = bool(findings) and all(row["status"] in {"PASS", "FAIL"} for row in findings)
    status = "FAIL" if any(row["status"] == "FAIL" for row in findings) else ("PASS" if complete else "INCONCLUSIVE")
    digest = hashlib.sha256(sheet_path.read_bytes()).hexdigest()
    return {
        "schema_version": "0.5",
        "asset_type": "sprite_sheet",
        "status": status,
        "completeness": "COMPLETE" if complete else "INCOMPLETE",
        "sheet": {"path": str(sheet_path), "sha256": digest, "frame_count": len(frames)},
        "layout": {
            "mode": policy.get("layout", "horizontal_strip"),
            "frame_width": policy["frame_width"],
            "frame_height": policy["frame_height"],
            "columns": policy.get("columns"),
        },
        "coverage": {
            "required": len(findings),
            "completed": sum(row["status"] in {"PASS", "FAIL"} for row in findings),
            "missing": [row["rule_id"] for row in findings if row["status"] not in {"PASS", "FAIL"}],
        },
        "results": findings,
    }
