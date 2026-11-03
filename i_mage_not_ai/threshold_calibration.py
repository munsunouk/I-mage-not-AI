"""Deterministic threshold search for binary labels (diagnostic / optional metrics)."""
from __future__ import annotations

import math
from typing import Any, Iterable, Literal


OptimizeMetric = Literal["balanced_accuracy", "f1", "precision", "recall"]


def search_binary_threshold(
    scores: list[float],
    labels: list[int],
    *,
    optimize: OptimizeMetric = "f1",
    thresholds: Iterable[float] | None = None,
) -> dict[str, Any]:
    """Pick a threshold on scores where label 1 means positive (e.g. AI-likely)."""
    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must be the same non-empty length")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("labels must be 0 or 1")
    grid = list(thresholds) if thresholds is not None else [i / 100 for i in range(101)]
    best: dict[str, Any] | None = None
    for threshold in grid:
        metrics = _metrics_at_threshold(scores, labels, threshold)
        score = _objective(metrics, optimize)
        if best is None or score > best["objective"]:
            best = {"threshold": threshold, "objective": score, **metrics}
    assert best is not None
    return {
        "optimize": optimize,
        "best_threshold": best["threshold"],
        "best_objective": best["objective"],
        "metrics_at_best": {k: best[k] for k in ("accuracy", "balanced_accuracy", "precision", "recall", "f1")},
        "n_samples": len(scores),
    }


def _metrics_at_threshold(scores: list[float], labels: list[int], threshold: float) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels, strict=True):
        predicted = 1 if score >= threshold else 0
        if predicted == 1 and label == 1:
            tp += 1
        elif predicted == 1 and label == 0:
            fp += 1
        elif predicted == 0 and label == 0:
            tn += 1
        else:
            fn += 1
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    balanced_accuracy = (tpr + tnr) / 2.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tpr
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _objective(metrics: dict[str, float], optimize: OptimizeMetric) -> float:
    value = metrics[optimize if optimize != "balanced_accuracy" else "balanced_accuracy"]
    if not math.isfinite(value):
        return float("-inf")
    return value
