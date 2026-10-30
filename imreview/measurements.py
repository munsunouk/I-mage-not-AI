"""Threshold-free diagnostic measurements for approved raster feature masks."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

from .core import _delta_e_2000_array, _rgb_array_lab, load_manifest


def _bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def _mask_metrics(mask: np.ndarray, rgb: np.ndarray, luma_bin_width: int) -> dict[str, Any]:
    ys, xs = np.nonzero(mask)
    count = int(len(xs))
    if not count:
        return {"pixel_count": 0, "occupancy_ratio": 0.0, "bbox": None,
                "connected_components_8": 0, "symmetry_horizontal_iou_bbox_local": 1.0,
                "unique_rgb_colors": 0, "channel_range": None,
                "delta_e00_to_channel_median": None, "luma_levels": 0,
                "periodic_energy_ratio_top8": None, "rgb_plane_fit_r2": None}

    pixels = rgb[mask]
    unique = np.unique(pixels, axis=0)
    ranges = np.ptp(pixels, axis=0)
    lab = _rgb_array_lab(pixels)
    median_rgb = np.partition(pixels, len(pixels) // 2, axis=0)[len(pixels) // 2]
    median_lab = _rgb_array_lab(median_rgb.reshape(1, 3))[0]
    delta_e = _delta_e_2000_array(lab, median_lab)

    x1, y1, x2, y2 = _bbox(mask)
    local_mask = mask[y1:y2, x1:x2]
    reflected = np.fliplr(local_mask)
    intersection = int(np.count_nonzero(local_mask & reflected))
    union = int(np.count_nonzero(local_mask | reflected))
    components = int(ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))[1])

    # Linear-sRGB luminance, scaled to 0..255 before applying the fixed bin width.
    srgb = pixels.astype(np.float64) / 255.0
    linear = np.where(srgb > .04045, ((srgb + .055) / 1.055) ** 2.4, srgb / 12.92)
    luma = (linear @ np.array([.2126, .7152, .0722])) * 255.0
    luma_levels = int(np.unique(np.floor(luma / luma_bin_width)).size)

    gray = np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.float64)
    crop = gray[y1:y2, x1:x2]
    if crop.size < 4:
        periodic = None
    else:
        spectrum = np.abs(np.fft.fft2(crop)) ** 2
        spectrum[0, 0] = 0
        total = float(spectrum.sum())
        top8 = np.partition(spectrum.ravel(), max(0, spectrum.size - 8))[-8:]
        periodic = float(top8.sum() / total) if total else 0.0

    if count < 4:
        plane_r2 = None
    else:
        design = np.column_stack((xs, ys, np.ones(count)))
        observed = pixels.astype(np.float64)
        predicted = design @ np.linalg.lstsq(design, observed, rcond=None)[0]
        denominator = float(((observed - observed.mean(axis=0)) ** 2).sum())
        plane_r2 = float(1 - ((observed - predicted) ** 2).sum() / denominator) if denominator else 1.0

    return {
        "pixel_count": count,
        "occupancy_ratio": count / mask.size,
        "bbox": _bbox(mask),
        "connected_components_8": components,
        "symmetry_horizontal_iou_bbox_local": intersection / union if union else 1.0,
        "unique_rgb_colors": int(len(unique)),
        "lab_bin_count": None,
        "channel_range_rgb": {key: int(value) for key, value in zip(("r", "g", "b"), ranges)},
        "delta_e00_to_channel_median": {
            "reference_rgb": median_rgb.astype(int).tolist(),
            "max": float(delta_e.max()),
            "p50": float(np.percentile(delta_e, 50)),
            "p95": float(np.percentile(delta_e, 95)),
            "exceedance_ratio": None,
            "exceedance_ratio_reason": "No delta_e_tolerance is configured; no cutoff was invented.",
        },
        "luma_levels": {"method": "linear_srgb_luminance_scaled_0_255", "bin_width": luma_bin_width, "count": luma_levels},
        "periodic_energy_ratio_top8": periodic,
        "periodic_energy_bbox_crop": [x1, y1, x2, y2],
        "rgb_plane_fit_r2": {"value": plane_r2, "judgment": "INCONCLUSIVE_DIAGNOSTIC_ONLY"},
    }


def measure_manifest(path: Path) -> dict[str, Any]:
    """Measure raster asset and approved feature masks without PASS/FAIL thresholds."""
    manifest, root = load_manifest(path)
    asset_path = (root / manifest["asset"]["path"]).resolve()
    if asset_path.suffix.lower() == ".svg":
        return {"schema_version": "1", "mode": "diagnostic_only", "status": "UNSUPPORTED_ASSET_TYPE",
                "asset": str(asset_path), "reason": "This command currently measures raster image assets."}

    with Image.open(asset_path) as opened:
        opened.load()
        rgba = np.asarray(opened.convert("RGBA"), dtype=np.uint8)
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3]
        height, width = alpha.shape
        alpha_present = "A" in opened.getbands() or "transparency" in opened.info

    alpha_bbox = _bbox(alpha > 0)
    if np.any(alpha):
        weights = alpha.astype(np.float64)
        ys = np.arange(height, dtype=np.float64) + .5
        xs = np.arange(width, dtype=np.float64) + .5
        cx = float(np.dot(weights.sum(axis=0), xs) / weights.sum())
        cy = float(np.dot(weights.sum(axis=1), ys) / weights.sum())
        centroid = {"x": cx, "y": cy,
                    "normalized_distance_to_canvas_center": float(np.hypot((cx-width/2)/width, (cy-height/2)/height))}
        margins = {"left": alpha_bbox[0]/width, "top": alpha_bbox[1]/height,
                   "right": (width-alpha_bbox[2])/width, "bottom": (height-alpha_bbox[3])/height}
    else:
        centroid = None
        margins = None

    edge = np.concatenate((rgb[:, 0, :].astype(np.int16), rgb[:, -1, :].astype(np.int16)), axis=1)
    horizontal_edge_error = float(np.abs(edge[:, :3] - edge[:, 3:]).mean())
    edge = np.concatenate((rgb[0, :, :].astype(np.int16), rgb[-1, :, :].astype(np.int16)), axis=1)
    vertical_edge_error = float(np.abs(edge[:, :3] - edge[:, 3:]).mean())

    features: list[dict[str, Any]] = []
    masks: dict[str, np.ndarray] = {}
    for feature in manifest.get("features", []):
        geometry = feature.get("geometry", {})
        if geometry.get("type") != "mask":
            features.append({"id": feature["id"], "status": "SKIPPED", "reason": "Feature has no raster mask geometry."})
            continue
        mask_path = (root / geometry["path"]).resolve()
        if not mask_path.is_relative_to(root.resolve()):
            raise ValueError(f"feature mask escapes manifest directory: {geometry['path']}")
        with Image.open(mask_path) as opened:
            if opened.size != (width, height):
                raise ValueError(f"feature {feature['id']} mask dimensions do not match the asset")
            mask = np.asarray(opened.convert("L")) > 0
        masks[feature["id"]] = mask
        metrics = _mask_metrics(mask, rgb, int(feature.get("properties", {}).get("luma_bin_width", 32)))
        features.append({"id": feature["id"], "role": feature.get("role"), "metrics": metrics})

    pairs = []
    for id_a, id_b in combinations(masks, 2):
        a, b = masks[id_a], masks[id_b]
        smaller = min(int(a.sum()), int(b.sum()))
        intersection = int(np.count_nonzero(a & b))
        pairs.append({"feature_a": id_a, "feature_b": id_b, "intersection_pixels": intersection,
                      "overlap_ratio_of_smaller_mask": intersection / smaller if smaller else None})

    visible = alpha > 0
    unique_rgb = int(np.unique(rgb[visible], axis=0).shape[0]) if np.any(visible) else 0
    return {
        "schema_version": "1",
        "mode": "diagnostic_only",
        "status": "MEASURED_NO_QUALITY_VERDICT",
        "asset": {"path": str(asset_path), "sha256": manifest["asset"].get("sha256"),
                  "width": width, "height": height, "alpha_present": alpha_present,
                  "transparent_pixel_ratio": float(np.count_nonzero(alpha == 0) / alpha.size),
                  "alpha_bbox": alpha_bbox,
                  "alpha_values_source": "stored_channel" if alpha_present else "implicit_opaque_for_rgb_asset",
                  "alpha_weighted_centroid": centroid,
                  "normalized_alpha_bbox_margins": margins, "unique_visible_rgb_colors": unique_rgb},
        "global_measurements": {"tile_edge_mean_absolute_rgb_difference": {
            "horizontal_opposing_edges": horizontal_edge_error,
            "vertical_opposing_edges": vertical_edge_error,
            "max": max(horizontal_edge_error, vertical_edge_error),
            "judgment": "MEASURED_ONLY; seamless-tile intent was not declared."}},
        "features": features,
        "pairwise_overlaps": pairs,
        "unmeasured": {"lab_bin_count": "No Lab bin size was configured.",
                       "delta_e_exceedance_ratio": "No delta_e_tolerance was configured.",
                       "svg": "Not applicable to this raster asset.",
                       "game_trace": "No animation or runtime trace was supplied."},
        "policy": "No PASS/FAIL thresholds were added or inferred.",
    }


def compare_feature_context(path: Path, feature_id: str, boundary_radius: int = 8) -> dict[str, Any]:
    """Compare an approved foreground feature with the opaque pixels around it."""
    if boundary_radius < 1:
        raise ValueError("boundary_radius must be at least 1")
    manifest, root = load_manifest(path)
    asset_path = (root / manifest["asset"]["path"]).resolve()
    with Image.open(asset_path) as opened:
        opened.load()
        rgba = np.asarray(opened.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[:, :, :3]
    valid = rgba[:, :, 3] > 0
    feature = next((item for item in manifest.get("features", []) if item["id"] == feature_id), None)
    if feature is None:
        raise ValueError(f"unknown feature id: {feature_id}")
    geometry = feature.get("geometry", {})
    if geometry.get("type") != "mask":
        raise ValueError(f"feature {feature_id} must have mask geometry")
    mask_path = (root / geometry["path"]).resolve()
    if not mask_path.is_relative_to(root.resolve()):
        raise ValueError("feature mask escapes manifest directory")
    with Image.open(mask_path) as opened:
        if opened.size != (rgba.shape[1], rgba.shape[0]):
            raise ValueError(f"feature {feature_id} mask dimensions do not match the image")
        foreground = np.asarray(opened.convert("L")) > 0
    foreground &= valid
    context = valid & ~foreground
    if not np.any(foreground) or not np.any(context):
        raise ValueError("foreground and surrounding context must both contain visible pixels")

    def color_stats(selection: np.ndarray) -> dict[str, Any]:
        pixels = rgb[selection].astype(np.float64)
        median_rgb = np.median(pixels, axis=0)
        linear = np.where(pixels / 255.0 > .04045,
                          ((pixels / 255.0 + .055) / 1.055) ** 2.4,
                          (pixels / 255.0) / 12.92)
        luma = linear @ np.array([.2126, .7152, .0722])
        lab = _rgb_array_lab(pixels)
        return {"pixel_count": int(len(pixels)),
                "rgb_median": median_rgb.astype(int).tolist(),
                "rgb_channel_range": np.ptp(pixels, axis=0).astype(int).tolist(),
                "lab_median": _rgb_array_lab(median_rgb.reshape(1, 3))[0].tolist(),
                "linear_luma": {"mean": float(luma.mean()), "median": float(np.median(luma)),
                                "std": float(luma.std()), "p10": float(np.percentile(luma, 10)),
                                "p90": float(np.percentile(luma, 90))},
                "lab_samples": lab}

    fg_stats = color_stats(foreground)
    bg_stats = color_stats(context)
    fg_lab = fg_stats.pop("lab_samples")
    bg_lab = bg_stats.pop("lab_samples")
    fg_median_lab = np.asarray(fg_stats["lab_median"])
    bg_median_lab = np.asarray(bg_stats["lab_median"])
    fg_to_bg = _delta_e_2000_array(fg_lab, bg_median_lab)
    bg_to_fg = _delta_e_2000_array(bg_lab, fg_median_lab)
    median_delta = float(_delta_e_2000_array(fg_median_lab.reshape(1, 3), bg_median_lab)[0])

    bins = np.linspace(0.0, 1.0, 65)
    fg_luma = fg_stats["linear_luma"]
    bg_luma = bg_stats["linear_luma"]
    fg_values = np.where(rgb[foreground].astype(np.float64) / 255.0 > .04045,
                         ((rgb[foreground].astype(np.float64) / 255.0 + .055) / 1.055) ** 2.4,
                         (rgb[foreground].astype(np.float64) / 255.0) / 12.92) @ np.array([.2126, .7152, .0722])
    bg_values = np.where(rgb[context].astype(np.float64) / 255.0 > .04045,
                         ((rgb[context].astype(np.float64) / 255.0 + .055) / 1.055) ** 2.4,
                         (rgb[context].astype(np.float64) / 255.0) / 12.92) @ np.array([.2126, .7152, .0722])
    fg_hist = np.histogram(fg_values, bins=bins)[0].astype(np.float64); fg_hist /= fg_hist.sum()
    bg_hist = np.histogram(bg_values, bins=bins)[0].astype(np.float64); bg_hist /= bg_hist.sum()
    pooled_std = float(np.sqrt((fg_luma["std"] ** 2 + bg_luma["std"] ** 2) / 2))
    standardized_luma_gap = abs(fg_luma["mean"] - bg_luma["mean"]) / pooled_std if pooled_std else 0.0

    height, width = foreground.shape
    structure = np.ones((3, 3), dtype=bool)
    inner_boundary = foreground & ~ndimage.binary_erosion(foreground, structure=structure, border_value=0)
    dilated = ndimage.binary_dilation(foreground, structure=structure, iterations=boundary_radius)
    local_context = dilated & ~foreground & valid
    paired_fg: list[np.ndarray] = []
    paired_bg: list[np.ndarray] = []
    for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
        y0, y1 = max(0, -dy), min(height, height - dy)
        x0, x1 = max(0, -dx), min(width, width - dx)
        source = foreground[y0:y1, x0:x1]
        neighbor = context[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        touching = source & neighbor
        if np.any(touching):
            paired_fg.append(rgb[y0:y1, x0:x1][touching])
            paired_bg.append(rgb[y0 + dy:y1 + dy, x0 + dx:x1 + dx][touching])
    if paired_fg:
        lab_a = _rgb_array_lab(np.concatenate(paired_fg).astype(np.float64))
        lab_b = _rgb_array_lab(np.concatenate(paired_bg).astype(np.float64))
        edge_delta = _delta_e_2000_array(lab_a, lab_b)
        edge_metrics = {"paired_pixel_count": int(len(edge_delta)), "delta_e00_mean": float(edge_delta.mean()),
                        "delta_e00_median": float(np.median(edge_delta)), "delta_e00_p95": float(np.percentile(edge_delta, 95))}
    else:
        edge_metrics = {"paired_pixel_count": 0, "delta_e00_mean": None, "delta_e00_median": None, "delta_e00_p95": None}

    srgb = rgb.astype(np.float64) / 255.0
    linear_rgb = np.where(srgb > .04045, ((srgb + .055) / 1.055) ** 2.4, srgb / 12.92)
    linear_luma = linear_rgb @ np.array([.2126, .7152, .0722])
    gx = ndimage.sobel(linear_luma, axis=1, mode="nearest") / 8
    gy = ndimage.sobel(linear_luma, axis=0, mode="nearest") / 8
    gradient = np.hypot(gx, gy)
    gradient_stats = {"foreground_mean": float(gradient[foreground].mean()),
                      "context_mean": float(gradient[context].mean()),
                      "local_context_mean": float(gradient[local_context].mean()) if np.any(local_context) else None,
                      "foreground_to_local_context_ratio": float(gradient[foreground].mean() / gradient[local_context].mean()) if np.any(local_context) and gradient[local_context].mean() else None}

    def luma_plane(selection: np.ndarray) -> dict[str, Any]:
        ys, xs = np.nonzero(selection)
        if len(xs) < 4:
            return {"r2": None, "slope_xy": None}
        design = np.column_stack((xs, ys, np.ones(len(xs))))
        observed = linear_luma[ys, xs]
        coeffs = np.linalg.lstsq(design, observed, rcond=None)[0]
        predicted = design @ coeffs
        denom = float(((observed - observed.mean()) ** 2).sum())
        r2 = float(1 - ((observed - predicted) ** 2).sum() / denom) if denom else 1.0
        slope = coeffs[:2]
        norm = float(np.linalg.norm(slope))
        return {"r2": r2, "slope_xy": slope.tolist(), "slope_magnitude": norm,
                "direction_xy": (slope / norm).tolist() if norm else None}

    fg_plane, bg_plane = luma_plane(foreground), luma_plane(local_context)
    if fg_plane.get("direction_xy") and bg_plane.get("direction_xy"):
        light_direction_cosine = float(np.dot(fg_plane["direction_xy"], bg_plane["direction_xy"]))
    else:
        light_direction_cosine = None

    return {
        "schema_version": "1",
        "mode": "cross_feature_diagnostic_only",
        "status": "MEASURED_NO_COMPATIBILITY_VERDICT",
        "asset": {"path": str(asset_path), "sha256": manifest["asset"].get("sha256"), "width": width, "height": height},
        "foreground": {"feature_id": feature_id, "role": feature.get("role"), "bbox": _bbox(foreground), "occupancy_ratio": float(foreground.sum() / foreground.size), "color_and_luma": fg_stats},
        "context": {"definition": "all visible source pixels outside the foreground feature mask", "pixel_count": int(context.sum()), "color_and_luma": bg_stats},
        "color_relationship": {"median_to_median_delta_e00": median_delta,
                               "foreground_pixel_to_context_median_delta_e00": {"median": float(np.median(fg_to_bg)), "p95": float(np.percentile(fg_to_bg, 95))},
                               "context_pixel_to_foreground_median_delta_e00": {"median": float(np.median(bg_to_fg)), "p95": float(np.percentile(bg_to_fg, 95))},
                               "lab_bin_size": None},
        "luminance_relationship": {"mean_difference_foreground_minus_context": fg_luma["mean"] - bg_luma["mean"],
                                   "standardized_absolute_mean_gap": standardized_luma_gap,
                                   "64_bin_histogram_intersection": float(np.minimum(fg_hist, bg_hist).sum())},
        "boundary_relationship": {"method": "paired 8-neighbor pixels across the foreground/context mask boundary", **edge_metrics,
                                  "outer_context_band_pixels": int(local_context.sum()), "band_radius_pixels": boundary_radius},
        "texture_relationship": {"method": "Sobel gradient magnitude on linear-sRGB luminance", **gradient_stats},
        "lighting_diagnostic": {"method": "least-squares linear plane on linear luminance; diagnostic only", "foreground_plane": fg_plane,
                                "local_context_plane": bg_plane, "direction_cosine": light_direction_cosine,
                                "judgment": "INCONCLUSIVE_DIAGNOSTIC_ONLY"},
        "limitations": ["These deterministic descriptors do not prove aesthetic harmony or AI provenance.",
                        "No thresholds or combined compatibility score were inferred.",
                        "Context includes every visible non-fox pixel, including foreground plants and rocks."],
    }
