"""Shared linear plane fits on raster channels (deterministic, no ML)."""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    srgb = rgb.astype(np.float64) / 255.0
    return np.where(srgb > 0.04045, ((srgb + 0.055) / 1.055) ** 2.4, srgb / 12.92)


def linear_luma_from_rgb(rgb: np.ndarray) -> np.ndarray:
    linear = srgb_to_linear(rgb)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def fit_plane(values: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> dict[str, Any]:
    if len(xs) < 4:
        return {"r2": None, "slope_xy": None, "slope_magnitude": None, "direction_xy": None}
    design = np.column_stack((xs.astype(np.float64), ys.astype(np.float64), np.ones(len(xs))))
    observed = values.astype(np.float64)
    coeffs = np.linalg.lstsq(design, observed, rcond=None)[0]
    predicted = design @ coeffs
    denom = float(((observed - observed.mean()) ** 2).sum())
    r2 = float(1 - ((observed - predicted) ** 2).sum() / denom) if denom else 1.0
    slope = coeffs[:2]
    norm = float(np.linalg.norm(slope))
    direction = (slope / norm).tolist() if norm else None
    return {"r2": r2, "slope_xy": slope.tolist(), "slope_magnitude": norm, "direction_xy": direction}


def plane_on_channel(channel: np.ndarray, selection: np.ndarray) -> dict[str, Any]:
    ys, xs = np.nonzero(selection)
    if len(xs) == 0:
        return {"r2": None, "slope_xy": None, "slope_magnitude": None, "direction_xy": None}
    return fit_plane(channel[ys, xs], xs, ys)


def angle_between_directions(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    va, vb = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return None
    cosine = float(np.clip(np.dot(va / na, vb / nb), -1.0, 1.0))
    return float(math.degrees(math.acos(cosine)))


def direction_cosine(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    va, vb = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return None
    return float(np.dot(va / na, vb / nb))
