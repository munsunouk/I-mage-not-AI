"""Bounded image inventory with deterministic inspect metadata and optional advisory."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .advisory_provenance import detect_advisory_image
from .core import ManifestError, inspect_image
from .project_discovery import SUPPORTED_ASSETS, _relative, _walk


def scan_images(
    path: Path,
    *,
    max_files: int = 20_000,
    max_depth: int = 16,
    advisory_backend: str | None = None,
    advisory_threshold: float = 0.5,
) -> dict[str, Any]:
    root = path.expanduser().resolve(strict=True)
    if root.is_file():
        return _scan_single_file(
            root,
            scan_root=root.parent,
            advisory_backend=advisory_backend,
            advisory_threshold=advisory_threshold,
        )
    if not root.is_dir():
        raise ValueError(f"scan path is not a file or directory: {root}")

    files, _, traversal = _walk(root, max_files, max_depth)
    image_files = sorted(
        (file for file in files if file.suffix.lower() in SUPPORTED_ASSETS),
        key=lambda item: str(item).casefold(),
    )
    rows: list[dict[str, Any]] = []
    for file_path in image_files:
        rows.append(
            _inspect_row(
                file_path,
                scan_root=root,
                advisory_backend=advisory_backend,
                advisory_threshold=advisory_threshold,
            )
        )
    status = "INCOMPLETE" if not traversal["complete"] else ("READY" if rows else "NO_IMAGES")
    return {
        "schema_version": "i-mage-not-ai/image-scan/1",
        "status": status,
        "scan_root": str(root),
        "limits": {"max_files": max_files, "max_depth": max_depth},
        "coverage": {
            "scan_complete": traversal["complete"],
            "files_seen": len(files),
            "image_count": len(rows),
            "error_count": sum(1 for row in rows if row.get("inspect_status") == "ERROR"),
        },
        "advisory_enabled": advisory_backend is not None,
        "rows": rows,
    }


def scan_rows_for_csv(report: dict[str, Any]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in report.get("rows", []):
        inspect_data = row.get("inspect") or {}
        advisory = row.get("advisory") or {}
        measured = {}
        if advisory.get("results"):
            measured = advisory["results"][0].get("measured") or {}
        flat.append(
            {
                "path": row.get("path"),
                "inspect_status": row.get("inspect_status"),
                "format": inspect_data.get("format"),
                "width": inspect_data.get("width"),
                "height": inspect_data.get("height"),
                "sha256": inspect_data.get("sha256"),
                "transparent_ratio": inspect_data.get("transparent_ratio"),
                "advisory_status": advisory.get("status"),
                "probability_ai": measured.get("probability_ai"),
                "advisory_label": measured.get("label"),
            }
        )
    return flat


def _scan_single_file(
    file_path: Path,
    *,
    scan_root: Path,
    advisory_backend: str | None,
    advisory_threshold: float,
) -> dict[str, Any]:
    row = _inspect_row(
        file_path,
        scan_root=scan_root,
        advisory_backend=advisory_backend,
        advisory_threshold=advisory_threshold,
    )
    return {
        "schema_version": "i-mage-not-ai/image-scan/1",
        "status": "READY" if row.get("inspect_status") == "OK" else "INCOMPLETE",
        "scan_root": str(scan_root),
        "limits": {"max_files": 1, "max_depth": 0},
        "coverage": {"scan_complete": True, "files_seen": 1, "image_count": 1, "error_count": 0 if row.get("inspect_status") == "OK" else 1},
        "advisory_enabled": advisory_backend is not None,
        "rows": [row],
    }


def _inspect_row(
    file_path: Path,
    *,
    scan_root: Path,
    advisory_backend: str | None,
    advisory_threshold: float,
) -> dict[str, Any]:
    rel = _relative(file_path, scan_root) if file_path.is_relative_to(scan_root) else str(file_path)
    row: dict[str, Any] = {"path": rel, "absolute_path": str(file_path)}
    try:
        row["inspect"] = inspect_image(file_path, report_path=rel)
        row["inspect_status"] = "OK"
    except (ManifestError, ValueError, OSError) as exc:
        row["inspect_status"] = "ERROR"
        row["inspect_error"] = str(exc)
    if advisory_backend is not None and file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        row["advisory"] = detect_advisory_image(
            file_path,
            backend=advisory_backend,
            threshold=advisory_threshold,
        )
    return row
