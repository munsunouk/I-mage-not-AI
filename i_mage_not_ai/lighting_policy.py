"""Deterministic lighting / shading checks from declared light direction and RGB plane alignment."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .image_planes import angle_between_directions, direction_cosine, linear_luma_from_rgb, plane_on_channel, srgb_to_linear
from .sprite_sheet import extract_frames, validate_sheet_layout

LIGHTING_POLICY_KEYS = frozenset(
    {
        "light_direction_xy",
        "max_direction_error_degrees",
        "min_channel_direction_cosine",
        "min_luma_plane_r2",
        "max_cross_frame_direction_variance",
        "selection",
        "sheet_layout",
        "frame_width",
        "frame_height",
        "columns",
        "frame_count",
        "alpha_threshold",
    }
)


def validate_lighting_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict) or not policy:
        raise ValueError("lighting policy must define at least one explicit check")
    unknown = set(policy) - LIGHTING_POLICY_KEYS
    if unknown:
        raise ValueError(f"unknown lighting policy keys: {sorted(unknown)}")
    if "light_direction_xy" in policy:
        direction = policy["light_direction_xy"]
        if not isinstance(direction, list) or len(direction) != 2 or any(
            not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in direction
        ):
            raise ValueError("light_direction_xy must be a finite [x, y] pair in image coordinates")
    if "sheet_layout" in policy:
        layout_policy: dict[str, Any] = {
            "layout": policy["sheet_layout"],
            "frame_width": policy["frame_width"],
            "frame_height": policy["frame_height"],
        }
        if "columns" in policy:
            layout_policy["columns"] = policy["columns"]
        if "frame_count" in policy:
            layout_policy["frame_count"] = policy["frame_count"]
        validate_sheet_layout(layout_policy)
    structural = {
        "selection",
        "sheet_layout",
        "frame_width",
        "frame_height",
        "columns",
        "frame_count",
        "alpha_threshold",
    }
    if not set(policy) - structural:
        raise ValueError("lighting policy must include at least one explicit check")
    return policy


def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _selection_mask(rgb: np.ndarray, policy: dict[str, Any], rgba: np.ndarray | None) -> np.ndarray:
    selection = policy.get("selection")
    height, width = rgb.shape[:2]
    if selection is None:
        if rgba is not None:
            threshold = int(policy.get("alpha_threshold", 128))
            return rgba[:, :, 3] >= threshold
        return np.ones((height, width), dtype=bool)
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    kind = selection.get("kind", "full_frame")
    if kind == "full_frame":
        return np.ones((height, width), dtype=bool)
    if kind == "rect":
        region = selection.get("region")
        if not isinstance(region, list) or len(region) != 4:
            raise ValueError("selection.region must be [x, y, width, height]")
        x, y, w, h = (int(v) for v in region)
        mask = np.zeros((height, width), dtype=bool)
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(width, x + w), min(height, y + h)
        mask[y1:y2, x1:x2] = True
        return mask
    raise ValueError("selection.kind must be full_frame or rect")


def _luma_plane_direction(rgb: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    linear = srgb_to_linear(rgb)
    luma = linear_luma_from_rgb(rgb)
    plane = plane_on_channel(luma, mask)
    return plane


def _channel_directions(rgb: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    linear = srgb_to_linear(rgb)
    return {channel: plane_on_channel(linear[:, :, index], mask) for index, channel in enumerate("rgb")}


def analyze_lighting_image(rgb: np.ndarray, policy: dict[str, Any], *, rgba: np.ndarray | None = None) -> list[dict[str, Any]]:
    mask = _selection_mask(rgb, policy, rgba)
    if not np.any(mask):
        return [
            {
                "rule_id": "LIGHT-SELECTION",
                "algorithm": "lighting_plane_direction",
                "status": "INCONCLUSIVE",
                "measured": None,
                "threshold": policy.get("light_direction_xy"),
                "formula": "non-empty pixel selection required",
            }
        ]
    findings: list[dict[str, Any]] = []
    luma_plane = _luma_plane_direction(rgb, mask)
    if "min_luma_plane_r2" in policy:
        limit = policy["min_luma_plane_r2"]
        r2 = luma_plane.get("r2")
        if r2 is None:
            status = "INCONCLUSIVE"
        else:
            status = "PASS" if r2 >= limit else "FAIL"
        findings.append(
            {
                "rule_id": "LIGHT-LUMA-PLANE-R2",
                "algorithm": "lighting_luma_plane_fit",
                "status": status,
                "measured": {"r2": r2, "plane": luma_plane},
                "threshold": {"min_r2": limit},
                "formula": "least-squares linear plane R² on linear luminance over selection",
            }
        )
    if "light_direction_xy" in policy and "max_direction_error_degrees" in policy:
        expected = policy["light_direction_xy"]
        observed = luma_plane.get("direction_xy")
        error = angle_between_directions(observed, expected)
        limit = policy["max_direction_error_degrees"]
        if error is None:
            status = "INCONCLUSIVE"
        else:
            status = "PASS" if error <= limit else "FAIL"
        findings.append(
            {
                "rule_id": "LIGHT-DIRECTION",
                "algorithm": "lighting_declared_direction_alignment",
                "status": status,
                "measured": {"observed_direction_xy": observed, "expected_direction_xy": expected, "error_degrees": error, "plane": luma_plane},
                "threshold": {"max_error_degrees": limit},
                "formula": "angle between luma gradient plane direction and declared light_direction_xy",
            }
        )
    if "min_channel_direction_cosine" in policy:
        channels = _channel_directions(rgb, mask)
        dirs = [channels[c]["direction_xy"] for c in "rgb"]
        cos_rg = direction_cosine(dirs[0], dirs[1])
        cos_rb = direction_cosine(dirs[0], dirs[2])
        cos_gb = direction_cosine(dirs[1], dirs[2])
        cosines = [value for value in (cos_rg, cos_rb, cos_gb) if value is not None]
        minimum = min(cosines) if cosines else None
        limit = policy["min_channel_direction_cosine"]
        if minimum is None:
            status = "INCONCLUSIVE"
        else:
            status = "PASS" if minimum >= limit else "FAIL"
        findings.append(
            {
                "rule_id": "LIGHT-CHROMATIC-SHADING",
                "algorithm": "lighting_chromatic_shading_direction_cosine",
                "status": status,
                "measured": {"channel_planes": channels, "min_pairwise_direction_cosine": minimum, "pairwise": {"rg": cos_rg, "rb": cos_rb, "gb": cos_gb}},
                "threshold": {"min_cosine": limit},
                "formula": "minimum pairwise cosine between R/G/B linear plane slope directions (Barron-style chromatic shading)",
            }
        )
    return findings


def analyze_lighting(path: Path, policy: Any) -> dict[str, Any]:
    validate_lighting_policy(policy)
    path = path.resolve()
    findings: list[dict[str, Any]] = []
    if policy.get("sheet_layout"):
        with Image.open(path) as image:
            rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        layout = {
            "layout": policy["sheet_layout"],
            "frame_width": policy["frame_width"],
            "frame_height": policy["frame_height"],
        }
        if "columns" in policy:
            layout["columns"] = policy["columns"]
        if "frame_count" in policy:
            layout["frame_count"] = policy["frame_count"]
        frames_rgba = extract_frames(rgba, layout)
        directions: list[list[float] | None] = []
        for index, frame in enumerate(frames_rgba):
            rgb = frame[:, :, :3]
            for row in analyze_lighting_image(rgb, policy, rgba=frame):
                findings.append({**row, "frame_index": index})
            luma = _luma_plane_direction(rgb, _selection_mask(rgb, policy, frame))
            directions.append(luma.get("direction_xy"))
        if "max_cross_frame_direction_variance" in policy:
            limit = policy["max_cross_frame_direction_variance"]
            vectors = [d for d in directions if d]
            if len(vectors) < 2:
                status, measured = "INCONCLUSIVE", {"directions": directions}
            else:
                arr = np.array(vectors, dtype=np.float64)
                measured = {"directions": directions, "variance_x": float(np.var(arr[:, 0])), "variance_y": float(np.var(arr[:, 1]))}
                total_var = measured["variance_x"] + measured["variance_y"]
                status = "PASS" if total_var <= limit else "FAIL"
            findings.append(
                {
                    "rule_id": "LIGHT-CROSS-FRAME",
                    "algorithm": "lighting_cross_frame_direction_variance",
                    "status": status,
                    "measured": measured,
                    "threshold": {"max_sum_variance": limit},
                    "formula": "variance of luma plane direction components across sheet frames",
                }
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        asset = {"path": str(path), "sha256": digest, "frame_count": len(frames_rgba)}
    else:
        rgb = _load_rgb(path)
        findings = analyze_lighting_image(rgb, policy)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        asset = {"path": str(path), "sha256": digest}

    complete = bool(findings) and all(row["status"] in {"PASS", "FAIL"} for row in findings)
    status = "FAIL" if any(row["status"] == "FAIL" for row in findings) else ("PASS" if complete else "INCONCLUSIVE")
    return {
        "schema_version": "0.5",
        "asset_type": "lighting_evidence",
        "status": status,
        "completeness": "COMPLETE" if complete else "INCOMPLETE",
        "asset": asset,
        "coverage": {
            "required": len(findings),
            "completed": sum(row["status"] in {"PASS", "FAIL"} for row in findings),
            "missing": [row["rule_id"] for row in findings if row["status"] not in {"PASS", "FAIL"}],
        },
        "results": findings,
    }
