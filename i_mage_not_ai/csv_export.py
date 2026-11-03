"""Write flat tabular exports for scan and discovery reports."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})


def flatten_preview_images(preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in preview.get("images", []):
        rows.append(
            {
                "project": item.get("project"),
                "path": item.get("path"),
                "format": item.get("format"),
                "width": item.get("width"),
                "height": item.get("height"),
                "sha256": item.get("sha256"),
                "transparent_ratio": item.get("transparent_ratio"),
                "inspection": item.get("inspection"),
            }
        )
    return rows


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".6g")
    return str(value)
