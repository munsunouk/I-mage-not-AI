"""Optional, non-gating AI-generation likelihood signals (external detector adapters)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ADVISORY_DISCLAIMER = (
    "Advisory only: probability_ai is not AI provenance proof and must not gate manifest review PASS/FAIL."
)

INSPECTABLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def iter_raster_paths(path: Path, *, recursive: bool) -> list[Path]:
    resolved = path.expanduser().resolve(strict=True)
    if resolved.is_file():
        if resolved.suffix.lower() not in INSPECTABLE_SUFFIXES:
            raise ValueError(f"unsupported image extension for advisory detect: {resolved.suffix}")
        return [resolved]
    if not resolved.is_dir():
        raise ValueError(f"path is not a file or directory: {resolved}")
    iterator = resolved.rglob("*") if recursive else resolved.glob("*")
    paths = sorted(
        (item for item in iterator if item.is_file() and item.suffix.lower() in INSPECTABLE_SUFFIXES),
        key=lambda item: str(item).casefold(),
    )
    if not paths:
        raise ValueError(f"no supported raster images found under {resolved}")
    return paths


def detect_advisory_image(
    image_path: Path,
    *,
    backend: str = "univfd",
    threshold: float = 0.5,
    device: str | None = None,
) -> dict[str, Any]:
    """Run optional external detector; never returns review-gate FAIL for provenance."""
    path = image_path.expanduser().resolve(strict=True)
    measured, backend_used, error = _run_detector(path, backend=backend, threshold=threshold, device=device)
    complete = measured is not None
    row_status = "ADVISORY" if complete else "INCONCLUSIVE"
    report_status = "INCONCLUSIVE" if not complete else "ADVISORY"
    finding: dict[str, Any] = {
        "rule_id": "ADVISORY-AI-PROVENANCE",
        "algorithm": "advisory_ai_generated_likelihood",
        "status": row_status,
        "measured": measured,
        "threshold": {"probability_ai_threshold": threshold, "backend": backend, "backend_used": backend_used},
        "formula": "external whole-image synthetic likelihood (non-gating)",
    }
    if error:
        finding["error"] = error
    return {
        "schema_version": "i-mage-not-ai/advisory-provenance/1",
        "asset_type": "advisory_provenance",
        "mode": "advisory_only",
        "status": report_status,
        "completeness": "COMPLETE" if complete else "INCOMPLETE",
        "disclaimer": ADVISORY_DISCLAIMER,
        "path": str(path),
        "results": [finding],
    }


def detect_advisory_batch(
    paths: list[Path],
    *,
    backend: str = "univfd",
    threshold: float = 0.5,
    device: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    any_complete = False
    for path in paths:
        single = detect_advisory_image(
            path,
            backend=backend,
            threshold=threshold,
            device=device,
        )
        rows.append({"path": str(path), **single})
        any_complete = any_complete or single["completeness"] == "COMPLETE"
    return {
        "schema_version": "i-mage-not-ai/advisory-provenance/1",
        "asset_type": "advisory_provenance_batch",
        "mode": "advisory_only",
        "status": "ADVISORY" if any_complete else "INCONCLUSIVE",
        "completeness": "COMPLETE" if any_complete else "INCOMPLETE",
        "disclaimer": ADVISORY_DISCLAIMER,
        "count": len(rows),
        "items": rows,
    }


def benchmark_labeled_folder(
    root: Path,
    *,
    real_dir: str = "real",
    fake_dir: str = "ai",
    backend: str = "univfd",
    threshold: float = 0.5,
    optimize: str = "f1",
) -> dict[str, Any]:
    """Score advisory detector on real/fake subfolders; diagnostic benchmark only."""
    from .threshold_calibration import search_binary_threshold

    base = root.expanduser().resolve(strict=True)
    real_root = base / real_dir
    fake_root = base / fake_dir
    if not real_root.is_dir() or not fake_root.is_dir():
        raise ValueError(f"expected {real_dir}/ and {fake_dir}/ directories under {base}")
    samples: list[tuple[Path, int]] = []
    for path in iter_raster_paths(real_root, recursive=True):
        samples.append((path, 0))
    for path in iter_raster_paths(fake_root, recursive=True):
        samples.append((path, 1))
    scores: list[float] = []
    labels: list[int] = []
    predictions: list[dict[str, Any]] = []
    errors = 0
    for path, label in samples:
        single = detect_advisory_image(path, backend=backend, threshold=threshold)
        measured = (single["results"][0].get("measured") or {}) if single["results"] else {}
        prob = measured.get("probability_ai")
        if prob is None:
            errors += 1
            predictions.append({"path": str(path), "label": label, "error": single["results"][0].get("error")})
            continue
        scores.append(float(prob))
        labels.append(label)
        predictions.append({"path": str(path), "label": label, "probability_ai": prob, "predicted": 1 if prob >= threshold else 0})
    calibration = search_binary_threshold(scores, labels, optimize=optimize) if scores else None
    return {
        "schema_version": "i-mage-not-ai/advisory-benchmark/1",
        "mode": "advisory_only",
        "disclaimer": ADVISORY_DISCLAIMER,
        "dataset_root": str(base),
        "backend": backend,
        "n_samples": len(samples),
        "n_scored": len(scores),
        "n_errors": errors,
        "default_threshold": threshold,
        "calibration": calibration,
        "predictions": predictions,
    }


def _run_detector(
    path: Path,
    *,
    backend: str,
    threshold: float,
    device: str | None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    library_error: str | None = None
    try:
        from aidetector.model import create_detector  # type: ignore[import-not-found]
    except ImportError:
        library_error = "aidetector package is not installed"
    else:
        try:
            detector = create_detector(backend, device=device or "auto", threshold=threshold)
            result = detector.predict_path(path)
            payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
            measured = {
                "label": payload.get("label"),
                "probability_ai": payload.get("probability_ai"),
                "probability_real": payload.get("probability_real"),
                "confidence": payload.get("confidence"),
                "raw_score": payload.get("raw_score"),
            }
            return measured, str(payload.get("backend") or backend), None
        except Exception as exc:
            library_error = f"{type(exc).__name__}: {exc}"

    cli_result = _detect_via_cli(path, backend=backend, threshold=threshold, device=device)
    if cli_result[0] is not None:
        return cli_result
    fallback = (
        "optional detector unavailable: install `aidetector` "
        "(e.g. pip install git+https://github.com/lynote-ai/ai-image-detector) or put `aidetect` on PATH"
    )
    detail = cli_result[2] or library_error or fallback
    return None, backend, detail


def _detect_via_cli(
    path: Path,
    *,
    backend: str,
    threshold: float,
    device: str | None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    executable = shutil.which("aidetect")
    if not executable:
        return None, backend, None
    command = [executable, "detect", str(path), "--no-recursive", "--json", "--backend", backend, "--threshold", str(threshold)]
    if device:
        command.extend(["--device", device])
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, backend, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        return None, backend, (completed.stderr or completed.stdout or "aidetect failed").strip()
    line = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    if not line:
        return None, backend, "aidetect produced no JSON output"
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, backend, f"invalid aidetect JSON: {exc}"
    measured = {
        "label": payload.get("label"),
        "probability_ai": payload.get("probability_ai"),
        "probability_real": payload.get("probability_real"),
        "confidence": payload.get("confidence"),
        "raw_score": payload.get("raw_score"),
    }
    return measured, str(payload.get("backend") or backend), None
