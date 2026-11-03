"""Deterministic sprite atlas / strip checks (no learned metrics)."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
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
        "pixel_delta_threshold",
        "reference_frame_index",
        "margin_left",
        "margin_top",
        "margin_right",
        "margin_bottom",
        "gap_x",
        "gap_y",
        "forbid_empty_cells",
        "forbid_duplicate_cells",
        "min_transparent_inner_border_px",
        "min_occupied_pixels",
        "include_cell_metadata",
        "max_file_bytes",
        "max_pixel_count",
        "max_cell_count",
        "required_bit_depth",
        "max_baseline_y_variance",
        "max_bbox_height_variance",
        "max_inter_frame_changed_pixel_ratio",
        "require_palette_subset_of_first_frame",
        "max_reference_changed_pixel_ratio",
    }
)

STRUCTURAL_POLICY_KEYS = frozenset(
    {
        "layout",
        "frame_width",
        "frame_height",
        "columns",
        "frame_count",
        "alpha_threshold",
        "pixel_delta_threshold",
        "reference_frame_index",
        "margin_left",
        "margin_top",
        "margin_right",
        "margin_bottom",
        "gap_x",
        "gap_y",
        "include_cell_metadata",
    }
)

FILE_LIMIT_POLICY_KEYS = frozenset({"max_file_bytes", "max_pixel_count", "max_cell_count", "required_bit_depth"})

CELL_LEVEL_POLICY_KEYS = frozenset(
    {
        "forbid_empty_cells",
        "forbid_duplicate_cells",
        "min_transparent_inner_border_px",
        "min_occupied_pixels",
    }
)


@dataclass(frozen=True)
class SheetCell:
    index: int
    row: int
    col: int
    x0: int
    y0: int
    frame: np.ndarray


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
    for key in ("margin_left", "margin_top", "margin_right", "margin_bottom", "gap_x", "gap_y"):
        if key not in policy:
            continue
        value = policy[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")


def validate_sprite_sheet_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict) or not policy:
        raise ValueError("sprite sheet policy must define at least one explicit check")
    unknown = set(policy) - SPRITE_SHEET_POLICY_KEYS
    if unknown:
        raise ValueError(f"unknown sprite sheet policy keys: {sorted(unknown)}")
    validate_sheet_layout(policy)
    explicit = set(policy) - STRUCTURAL_POLICY_KEYS
    if not explicit:
        raise ValueError("sprite sheet policy must include at least one explicit check")
    return policy


def _margins(policy: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(policy.get("margin_left", 0)),
        int(policy.get("margin_top", 0)),
        int(policy.get("margin_right", 0)),
        int(policy.get("margin_bottom", 0)),
    )


def _gaps(policy: dict[str, Any]) -> tuple[int, int]:
    return (int(policy.get("gap_x", 0)), int(policy.get("gap_y", 0)))


def _validate_sheet_file(path: Path, policy: dict[str, Any]) -> None:
    if "max_file_bytes" in policy:
        limit = policy["max_file_bytes"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("max_file_bytes must be a positive integer")
        size = path.stat().st_size
        if size > limit:
            raise ValueError(f"sprite sheet file size {size} exceeds max_file_bytes {limit}")


def _load_rgba(path: Path, policy: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    _validate_sheet_file(path, policy)
    with Image.open(path) as image:
        if image.format not in {"PNG", "WEBP"}:
            raise ValueError("sprite sheet must be PNG or WebP")
        width, height = image.size
        pixels = width * height
        if "max_pixel_count" in policy:
            limit = policy["max_pixel_count"]
            if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
                raise ValueError("max_pixel_count must be a positive integer")
            if pixels > limit:
                raise ValueError(f"sprite sheet pixel count {pixels} exceeds max_pixel_count {limit}")
        if policy.get("required_bit_depth") == 8:
            depth = policy["required_bit_depth"]
            if depth != 8:
                raise ValueError("required_bit_depth must be 8 when set")
            mode = image.mode
            if mode not in {"RGBA", "RGB", "P", "LA", "L"}:
                raise ValueError(f"required_bit_depth 8 but image mode is {mode!r}")
        rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        meta = {
            "format": image.format,
            "width": width,
            "height": height,
            "pixel_count": pixels,
            "mode_before_convert": image.mode,
        }
        return rgba, meta


def _grid_dimensions(sheet: np.ndarray, policy: dict[str, Any]) -> tuple[int, int, int]:
    """Return (columns, rows, total_cells_before_frame_count_cap)."""
    layout = policy.get("layout", "horizontal_strip")
    fw, fh = int(policy["frame_width"]), int(policy["frame_height"])
    ml, mt, mr, mb = _margins(policy)
    gap_x, gap_y = _gaps(policy)
    height, width = sheet.shape[:2]
    inner_w = width - ml - mr
    if inner_w < 0:
        raise ValueError("horizontal margins exceed sheet width")
    if layout == "horizontal_strip":
        expected_h = mt + fh + mb
        if height != expected_h:
            raise ValueError(
                f"sheet height {height} must equal margin_top + frame_height + margin_bottom ({expected_h})"
            )
        if gap_x == 0:
            if inner_w % fw != 0:
                raise ValueError("inner width must be a multiple of frame_width when gap_x=0")
            columns = inner_w // fw
        else:
            if (inner_w + gap_x) % (fw + gap_x) != 0:
                raise ValueError("inner width must align with frame_width and gap_x")
            columns = (inner_w + gap_x) // (fw + gap_x)
        rows = 1
        expected_w = ml + columns * fw + max(0, columns - 1) * gap_x + mr
        if expected_w != width:
            raise ValueError(f"sheet width {width} does not match margin/frame/gap layout ({expected_w})")
        return columns, rows, columns
    columns = int(policy["columns"])
    inner_h = height - mt - mb
    if inner_h < 0:
        raise ValueError("vertical margins exceed sheet height")
    if gap_y == 0:
        if inner_h % fh != 0:
            raise ValueError("inner height must be a multiple of frame_height when gap_y=0")
        rows = inner_h // fh
    else:
        if (inner_h + gap_y) % (fh + gap_y) != 0:
            raise ValueError("inner height must align with frame_height and gap_y")
        rows = (inner_h + gap_y) // (fh + gap_y)
    expected_w = ml + columns * fw + max(0, columns - 1) * gap_x + mr
    expected_h = mt + rows * fh + max(0, rows - 1) * gap_y + mb
    if expected_w != width or expected_h != height:
        raise ValueError(
            f"sheet size {width}x{height} does not match grid margins, gaps, and frame size ({expected_w}x{expected_h})"
        )
    return columns, rows, columns * rows


def layout_sheet_cells(sheet: np.ndarray, policy: dict[str, Any]) -> list[SheetCell]:
    columns, rows, total = _grid_dimensions(sheet, policy)
    if "max_cell_count" in policy:
        limit = policy["max_cell_count"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("max_cell_count must be a positive integer")
        if total > limit:
            raise ValueError(f"sheet defines {total} cells which exceeds max_cell_count {limit}")
    fw, fh = int(policy["frame_width"]), int(policy["frame_height"])
    ml, mt, _, _ = _margins(policy)
    gap_x, gap_y = _gaps(policy)
    if "frame_count" in policy:
        total = min(total, int(policy["frame_count"]))
    cells: list[SheetCell] = []
    index = 0
    for row in range(rows):
        for col in range(columns):
            if index >= total:
                return cells
            x0 = ml + col * (fw + gap_x)
            y0 = mt + row * (fh + gap_y)
            frame = sheet[y0 : y0 + fh, x0 : x0 + fw].copy()
            cells.append(SheetCell(index=index, row=row, col=col, x0=x0, y0=y0, frame=frame))
            index += 1
    return cells


def extract_frames(sheet: np.ndarray, policy: dict[str, Any]) -> list[np.ndarray]:
    return [cell.frame for cell in layout_sheet_cells(sheet, policy)]


def _alpha_mask(frame: np.ndarray, threshold: int) -> np.ndarray:
    return frame[:, :, 3] >= threshold


def _occupied_count(mask: np.ndarray) -> int:
    return int(mask.sum())


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    if len(ys) == 0 or len(xs) == 0:
        return None
    return int(xs[0]), int(ys[0]), int(xs[-1]), int(ys[-1])


def _bbox_height(mask: np.ndarray) -> int:
    box = _bbox(mask)
    if box is None:
        return 0
    _, y0, _, y1 = box
    return int(y1 - y0 + 1)


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


def _frame_rgba_digest(frame: np.ndarray) -> str:
    return hashlib.sha256(frame.tobytes()).hexdigest()


def _min_opaque_to_cell_edge_px(mask: np.ndarray) -> int | None:
    if not mask.any():
        return None
    h, w = mask.shape
    ys, xs = np.where(mask)
    distances = np.minimum.reduce([xs, ys, w - 1 - xs, h - 1 - ys])
    return int(distances.min())


def _alpha_coverage_ratio(mask: np.ndarray) -> float:
    return float(mask.mean())


def _build_cell_metadata(cells: list[SheetCell], alpha_threshold: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        mask = _alpha_mask(cell.frame, alpha_threshold)
        occupied = _occupied_count(mask)
        box = _bbox(mask)
        rows.append(
            {
                "index": cell.index,
                "row": cell.row,
                "col": cell.col,
                "x0": cell.x0,
                "y0": cell.y0,
                "width": cell.frame.shape[1],
                "height": cell.frame.shape[0],
                "occupied_pixels": occupied,
                "alpha_coverage_ratio": _alpha_coverage_ratio(mask),
                "bbox": list(box) if box is not None else None,
                "rgba_sha256": _frame_rgba_digest(cell.frame),
                "min_opaque_to_edge_px": _min_opaque_to_cell_edge_px(mask),
            }
        )
    return rows


def _margin_gap_contamination(sheet: np.ndarray, policy: dict[str, Any], alpha_threshold: int) -> dict[str, Any]:
    height, width = sheet.shape[:2]
    fw, fh = int(policy["frame_width"]), int(policy["frame_height"])
    ml, mt, mr, mb = _margins(policy)
    gap_x, gap_y = _gaps(policy)
    columns, rows, _ = _grid_dimensions(sheet, policy)
    forbidden = np.zeros((height, width), dtype=bool)
    if ml:
        forbidden[:, :ml] = True
    if mr:
        forbidden[:, width - mr :] = True
    if mt:
        forbidden[:mt, :] = True
    if mb:
        forbidden[height - mb :, :] = True
    for row in range(rows):
        for col in range(columns):
            x0 = ml + col * (fw + gap_x)
            y0 = mt + row * (fh + gap_y)
            if gap_x and col < columns - 1:
                gx0 = x0 + fw
                forbidden[y0 : y0 + fh, gx0 : gx0 + gap_x] = True
            if gap_y and row < rows - 1:
                gy0 = y0 + fh
                forbidden[gy0 : gy0 + gap_y, x0 : x0 + fw] = True
    alpha = sheet[:, :, 3] >= alpha_threshold
    contaminated = forbidden & alpha
    count = int(contaminated.sum())
    return {
        "contaminated_pixels": count,
        "forbidden_region_pixels": int(forbidden.sum()),
        "sample_coordinates": _sample_coords(contaminated, limit=8),
    }


def _sample_coords(mask: np.ndarray, *, limit: int) -> list[list[int]]:
    ys, xs = np.where(mask)
    samples: list[list[int]] = []
    for i in range(min(limit, len(xs))):
        samples.append([int(xs[i]), int(ys[i])])
    return samples


def analyze_sprite_sheet(sheet_path: Path, policy: Any) -> dict[str, Any]:
    validate_sprite_sheet_policy(policy)
    sheet, file_meta = _load_rgba(sheet_path.resolve(), policy)
    cells = layout_sheet_cells(sheet, policy)
    if len(cells) < 1:
        raise ValueError("sprite sheet produced zero frames")
    frames = [cell.frame for cell in cells]
    alpha_threshold = int(policy.get("alpha_threshold", 128))
    if not 0 <= alpha_threshold <= 255:
        raise ValueError("alpha_threshold must be between 0 and 255")
    findings: list[dict[str, Any]] = []
    cell_meta: list[dict[str, Any]] | None = None

    wants_cell_meta = policy.get("include_cell_metadata", True)
    if wants_cell_meta and (CELL_LEVEL_POLICY_KEYS & set(policy) or wants_cell_meta):
        cell_meta = _build_cell_metadata(cells, alpha_threshold)

    if any(_margins(policy)) or any(_gaps(policy)):
        measured = _margin_gap_contamination(sheet, policy, alpha_threshold)
        status = "PASS" if measured["contaminated_pixels"] == 0 else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-MARGIN-GAP",
                "algorithm": "sprite_margin_gap_contamination",
                "status": status,
                "measured": measured,
                "threshold": {"max_contaminated_pixels": 0},
                "formula": "no opaque pixels in declared outer margins or inter-cell gaps",
            }
        )

    if policy.get("forbid_empty_cells"):
        empty = [row["index"] for row in (cell_meta or _build_cell_metadata(cells, alpha_threshold)) if row["occupied_pixels"] == 0]
        status = "PASS" if not empty else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-EMPTY-CELL",
                "algorithm": "sprite_cell_empty_forbidden",
                "status": status,
                "measured": {"empty_cell_indices": empty, "empty_count": len(empty)},
                "threshold": {"forbid_empty": True},
                "formula": "every cell must contain at least one opaque pixel at alpha_threshold",
            }
        )

    if "min_occupied_pixels" in policy:
        minimum = policy["min_occupied_pixels"]
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            raise ValueError("min_occupied_pixels must be a positive integer")
        meta = cell_meta or _build_cell_metadata(cells, alpha_threshold)
        violations = [
            {"index": row["index"], "occupied_pixels": row["occupied_pixels"]}
            for row in meta
            if row["occupied_pixels"] < minimum
        ]
        near_empty = [v for v in violations if v["occupied_pixels"] > 0]
        status = "PASS" if not violations else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-NEAR-EMPTY",
                "algorithm": "sprite_cell_near_empty",
                "status": status,
                "measured": {
                    "violating_cells": violations[:32],
                    "violation_count": len(violations),
                    "near_empty_count": len(near_empty),
                    "fully_empty_count": len(violations) - len(near_empty),
                },
                "threshold": {"min_occupied_pixels": minimum},
                "formula": "occupied pixel count per cell must be >= min_occupied_pixels",
            }
        )

    if policy.get("forbid_duplicate_cells"):
        meta = cell_meta or _build_cell_metadata(cells, alpha_threshold)
        by_hash: dict[str, list[int]] = {}
        for row in meta:
            by_hash.setdefault(row["rgba_sha256"], []).append(row["index"])
        duplicate_groups = [indices for indices in by_hash.values() if len(indices) > 1]
        status = "PASS" if not duplicate_groups else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-DUPLICATE-CELL",
                "algorithm": "sprite_cell_duplicate_forbidden",
                "status": status,
                "measured": {"duplicate_groups": duplicate_groups[:16], "group_count": len(duplicate_groups)},
                "threshold": {"forbid_duplicates": True},
                "formula": "full RGBA cell payloads must be unique",
            }
        )

    if "min_transparent_inner_border_px" in policy:
        minimum = policy["min_transparent_inner_border_px"]
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
            raise ValueError("min_transparent_inner_border_px must be a non-negative integer")
        meta = cell_meta or _build_cell_metadata(cells, alpha_threshold)
        violations = []
        for row in meta:
            if row["occupied_pixels"] == 0:
                continue
            edge = row["min_opaque_to_edge_px"]
            if edge is None or edge < minimum:
                violations.append({"index": row["index"], "min_opaque_to_edge_px": edge})
        status = "PASS" if not violations else "FAIL"
        findings.append(
            {
                "rule_id": "SPRITE-INNER-BORDER",
                "algorithm": "sprite_cell_min_inner_border",
                "status": status,
                "measured": {"violating_cells": violations[:32], "violation_count": len(violations)},
                "threshold": {"min_transparent_inner_border_px": minimum},
                "formula": "minimum distance from opaque pixels to cell edge",
            }
        )

    if "max_file_bytes" in policy or "max_pixel_count" in policy or policy.get("required_bit_depth") == 8:
        findings.append(
            {
                "rule_id": "SPRITE-FILE-LIMITS",
                "algorithm": "sprite_sheet_file_limits",
                "status": "PASS",
                "measured": {
                    "file_bytes": sheet_path.stat().st_size,
                    **file_meta,
                },
                "threshold": {
                    key: policy[key]
                    for key in ("max_file_bytes", "max_pixel_count", "required_bit_depth")
                    if key in policy
                },
                "formula": "PNG/WebP size, pixel count, and bit-depth constraints enforced at load",
            }
        )

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
    ml, mt, mr, mb = _margins(policy)
    gap_x, gap_y = _gaps(policy)
    columns, rows, _ = _grid_dimensions(sheet, policy)
    payload: dict[str, Any] = {
        "schema_version": "0.5",
        "asset_type": "sprite_sheet",
        "status": status,
        "completeness": "COMPLETE" if complete else "INCOMPLETE",
        "sheet": {"path": str(sheet_path), "sha256": digest, "frame_count": len(frames), "file": file_meta},
        "layout": {
            "mode": policy.get("layout", "horizontal_strip"),
            "frame_width": policy["frame_width"],
            "frame_height": policy["frame_height"],
            "columns": policy.get("columns") if policy.get("layout") == "grid" else columns,
            "rows": rows,
            "margin_left": ml,
            "margin_top": mt,
            "margin_right": mr,
            "margin_bottom": mb,
            "gap_x": gap_x,
            "gap_y": gap_y,
        },
        "coverage": {
            "required": len(findings),
            "completed": sum(row["status"] in {"PASS", "FAIL"} for row in findings),
            "missing": [row["rule_id"] for row in findings if row["status"] not in {"PASS", "FAIL"}],
        },
        "results": findings,
    }
    if cell_meta is not None and wants_cell_meta:
        payload["cells"] = cell_meta
    return payload
