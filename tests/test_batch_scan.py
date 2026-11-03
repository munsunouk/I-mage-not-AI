"""Batch scan, CSV export, and threshold calibration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from i_mage_not_ai.batch_scan import scan_images, scan_rows_for_csv
from i_mage_not_ai.threshold_calibration import search_binary_threshold
from i_mage_not_ai.typer_cli import app


def test_scan_images_and_csv_rows(tmp_path: Path) -> None:
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(tmp_path / "a.png")
    nested = tmp_path / "nested"
    nested.mkdir()
    Image.new("RGBA", (2, 2), (0, 255, 0, 255)).save(nested / "b.png")
    report = scan_images(tmp_path, max_files=100, max_depth=8)
    assert report["status"] == "READY"
    assert len(report["rows"]) == 2
    csv_rows = scan_rows_for_csv(report)
    assert {row["path"] for row in csv_rows} == {"a.png", "nested/b.png"}
    assert all(row["inspect_status"] == "OK" for row in csv_rows)


def test_search_binary_threshold_prefers_high_scores_for_positives() -> None:
    scores = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]
    result = search_binary_threshold(scores, labels, optimize="f1")
    assert result["metrics_at_best"]["f1"] == 1.0
    assert result["best_threshold"] > 0.15


def test_cli_scan_and_calibrate(tmp_path: Path) -> None:
    Image.new("RGBA", (3, 3), (255, 255, 255, 255)).save(tmp_path / "one.png")
    runner = CliRunner()
    scan = runner.invoke(app, ["scan", "images", "--path", str(tmp_path)])
    assert scan.exit_code == 0, scan.output
    scores = tmp_path / "scores.json"
    scores.write_text(json.dumps([{"score": 0.2, "label": 0}, {"score": 0.9, "label": 1}]), encoding="utf-8")
    cal = runner.invoke(app, ["benchmark", "calibrate-binary", "--scores", str(scores)])
    assert cal.exit_code == 0, cal.output


def test_scan_directory_marks_inspect_errors_incomplete(tmp_path: Path) -> None:
    good = tmp_path / "good.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(good)
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-a-png")
    report = scan_images(tmp_path)
    assert report["status"] == "INCOMPLETE"
    assert report["coverage"]["error_count"] == 1


def test_http_api_health_and_inspect_route() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from i_mage_not_ai.http_api import create_app

    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}
    routes = {route.path for route in client.app.routes}
    assert "/inspect" in routes
    assert "/advisory/detect" not in routes
