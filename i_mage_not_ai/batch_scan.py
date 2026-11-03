"""Bounded image inventory with deterministic inspect metadata."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import ManifestError, inspect_image
from .project_discovery import SUPPORTED_ASSETS, _relative, _walk


def scan_images(
    path: Path,
    *,
    max_files: int = 20_000,
    max_depth: int = 16,
) -> dict[str, Any]:
    root = path.expanduser().resolve(strict=True)
    if root.is_file():
        return _scan_single_file(root, scan_root=root.parent)
    if not root.is_dir():
        raise ValueError(f"scan path is not a file or directory: {root}")

    files, _, traversal = _walk(root, max_files, max_depth)
    image_files = sorted(
        (file for file in files if file.suffix.lower() in SUPPORTED_ASSETS),
        key=lambda item: str(item).casefold(),
    )
    rows = [_inspect_row(file_path, scan_root=root) for file_path in image_files]
    has_errors = any(row.get("inspect_status") == "ERROR" for row in rows)
    if not traversal["complete"] or has_errors:
        status = "INCOMPLETE"
    elif rows:
        status = "READY"
    else:
        status = "NO_IMAGES"
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
        "rows": rows,
    }


def scan_rows_for_csv(report: dict[str, Any]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in report.get("rows", []):
        inspect_data = row.get("inspect") or {}
        flat.append(
            {
                "path": row.get("path"),
                "inspect_status": row.get("inspect_status"),
                "format": inspect_data.get("format"),
                "width": inspect_data.get("width"),
                "height": inspect_data.get("height"),
                "sha256": inspect_data.get("sha256"),
                "transparent_ratio": inspect_data.get("transparent_ratio"),
            }
        )
    return flat


def _scan_single_file(file_path: Path, *, scan_root: Path) -> dict[str, Any]:
    row = _inspect_row(file_path, scan_root=scan_root)
    return {
        "schema_version": "i-mage-not-ai/image-scan/1",
        "status": "READY" if row.get("inspect_status") == "OK" else "INCOMPLETE",
        "scan_root": str(scan_root),
        "limits": {"max_files": 1, "max_depth": 0},
        "coverage": {
            "scan_complete": True,
            "files_seen": 1,
            "image_count": 1,
            "error_count": 0 if row.get("inspect_status") == "OK" else 1,
        },
        "rows": [row],
    }


def _inspect_row(file_path: Path, *, scan_root: Path) -> dict[str, Any]:
    rel = _relative(file_path, scan_root) if file_path.is_relative_to(scan_root) else str(file_path)
    row: dict[str, Any] = {"path": rel, "absolute_path": str(file_path)}
    try:
        row["inspect"] = inspect_image(file_path, report_path=rel)
        row["inspect_status"] = "OK"
    except (ManifestError, ValueError, OSError) as exc:
        row["inspect_status"] = "ERROR"
        row["inspect_error"] = str(exc)
    return row
