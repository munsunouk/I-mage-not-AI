"""Deterministic foot-line and bbox metrics for sprite frames (no collider export)."""
from __future__ import annotations

from typing import Any

import numpy as np


def alpha_mask(frame: np.ndarray, threshold: int) -> np.ndarray:
    return frame[:, :, 3] >= threshold


def alpha_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    if len(ys) == 0 or len(xs) == 0:
        return None
    return int(xs[0]), int(ys[0]), int(xs[-1]), int(ys[-1])


def bbox_height_px(mask: np.ndarray) -> int:
    box = alpha_bbox(mask)
    if box is None:
        return 0
    _, y0, _, y1 = box
    return int(y1 - y0 + 1)


def ground_line_y(mask: np.ndarray) -> float | None:
    rows = np.where(mask.any(axis=1))[0]
    if len(rows) == 0:
        return None
    return float(rows[-1])


def feet_center_x(mask: np.ndarray, *, ground_y: int | None = None) -> float | None:
    gy = int(ground_y) if ground_y is not None else None
    if gy is None:
        row = ground_line_y(mask)
        if row is None:
            return None
        gy = int(row)
    if gy < 0 or gy >= mask.shape[0]:
        return None
    xs = np.where(mask[gy])[0]
    if len(xs) == 0:
        rows = np.where(mask.any(axis=1))[0]
        if len(rows) == 0:
            return None
        gy = int(rows[-1])
        xs = np.where(mask[gy])[0]
        if len(xs) == 0:
            return None
    return float((int(xs[0]) + int(xs[-1])) / 2.0)


def center_of_mass_xy(mask: np.ndarray) -> tuple[float, float] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return float(xs.mean()), float(ys.mean())


def measure_frame(frame: np.ndarray, *, alpha_threshold: int, frame_index: int) -> dict[str, Any]:
    mask = alpha_mask(frame, alpha_threshold)
    box = alpha_bbox(mask)
    gy = ground_line_y(mask)
    pivot_x = feet_center_x(mask, ground_y=int(gy) if gy is not None else None)
    com = center_of_mass_xy(mask)
    height = bbox_height_px(mask)
    return {
        "frame_index": frame_index,
        "bbox": list(box) if box is not None else None,
        "bbox_height_px": height,
        "ground_line_y": gy,
        "feet_center_x": pivot_x,
        "feet_pivot_xy": [pivot_x, gy] if pivot_x is not None and gy is not None else None,
        "center_of_mass_xy": list(com) if com is not None else None,
        "occupied_pixels": int(mask.sum()),
    }


def aggregate_sheet_draw_height(frames: list[np.ndarray], *, alpha_threshold: int) -> int:
    heights = [measure_frame(frame, alpha_threshold=alpha_threshold, frame_index=i)["bbox_height_px"] for i, frame in enumerate(frames)]
    return int(max(heights)) if heights else 0
