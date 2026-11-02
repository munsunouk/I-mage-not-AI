"""Deterministic sprite, lighting, and extended render checks."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from i_mage_not_ai.render_evidence import analyze_render_evidence, load_render_evidence
from i_mage_not_ai.sprite_sheet import analyze_sprite_sheet
from i_mage_not_ai.lighting_policy import analyze_lighting
from i_mage_not_ai.typer_cli import app


def _strip(sheet_path: Path, frames: list[Image.Image]) -> None:
    width = sum(frame.width for frame in frames)
    height = max(frame.height for frame in frames)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = 0
    for frame in frames:
        canvas.paste(frame, (x, 0))
        x += frame.width
    canvas.save(sheet_path)


def test_sprite_sheet_baseline_and_palette_subset(tmp_path: Path) -> None:
    frames = []
    for index in range(3):
        img = Image.new("RGBA", (4, 8), (0, 0, 0, 0))
        for y in range(2 + index, 8):
            for x in range(4):
                img.putpixel((x, y), (255, 0, 0, 255))
        frames.append(img)
    sheet = tmp_path / "walk.png"
    _strip(sheet, frames)
    policy = {
        "layout": "horizontal_strip",
        "frame_width": 4,
        "frame_height": 8,
        "max_baseline_y_variance": 1.0,
        "require_palette_subset_of_first_frame": True,
    }
    report = analyze_sprite_sheet(sheet, policy)
    assert report["status"] == "PASS"
    assert any(row["algorithm"] == "sprite_baseline_y_variance" for row in report["results"])


def test_sprite_sheet_fails_palette_growth(tmp_path: Path) -> None:
    base = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    extra = Image.new("RGBA", (2, 2), (0, 255, 0, 255))
    sheet = tmp_path / "bad.png"
    _strip(sheet, [base, extra])
    report = analyze_sprite_sheet(
        sheet,
        {"layout": "horizontal_strip", "frame_width": 2, "frame_height": 2, "require_palette_subset_of_first_frame": True},
    )
    assert report["status"] == "FAIL"
    row = next(r for r in report["results"] if r["algorithm"] == "sprite_inter_frame_palette_subset")
    assert row["status"] == "FAIL"


def test_lighting_direction_on_synthetic_gradient(tmp_path: Path) -> None:
    rgb = np.zeros((32, 32, 3), dtype=np.uint8)
    for y in range(32):
        value = int(255 * y / 31)
        rgb[y, :, :] = (value, value, value)
    path = tmp_path / "grad.png"
    Image.fromarray(rgb, mode="RGB").save(path)
    policy = {
        "light_direction_xy": [0, 1],
        "max_direction_error_degrees": 25,
        "min_channel_direction_cosine": 0.99,
    }
    report = analyze_lighting(path, policy)
    assert report["status"] == "PASS"
    direction = next(r for r in report["results"] if r["algorithm"] == "lighting_declared_direction_alignment")
    assert direction["status"] == "PASS"


def test_render_roi_oracle_hash_match(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    ref = Image.new("RGB", (2, 2), (10, 20, 30))
    ref.save(frames / "0.png")
    ref.save(tmp_path / "ref.png")
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "format": "i_mage_not_ai.render-evidence/1",
                "capture_source": "engine_runtime",
                "engine": "godot",
                "engine_version": "4.6.3",
                "platform": "desktop",
                "scenario_id": "roi",
                "timebase": "seconds",
                "resolution": [2, 2],
                "import_settings": {"renderer": "vulkan"},
                "captures": [{"frame_index": 0, "timestamp": 0, "image": "frames/0.png", "event_ids": []}],
            }
        ),
        encoding="utf-8",
    )
    evidence, _ = load_render_evidence(evidence_path)
    policy = {
        "roi_oracles": {
            "hud": {
                "frame_index": 0,
                "region": [0, 0, 2, 2],
                "reference": "ref.png",
                "match_mode": "hash",
            }
        }
    }
    report = analyze_render_evidence(evidence, policy, policy_dir=tmp_path)
    row = next(r for r in report["results"] if r["algorithm"] == "render_roi_oracle")
    assert (report["status"], row["status"]) == ("PASS", "PASS")


def test_render_trace_motion_bound(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    left = Image.new("RGB", (8, 8), (0, 0, 0))
    for y in range(8):
        left.putpixel((1, y), (200, 200, 200))
    left.save(frames / "0.png")
    right = Image.new("RGB", (8, 8), (0, 0, 0))
    for y in range(8):
        right.putpixel((5, y), (200, 200, 200))
    right.save(frames / "1.png")
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "format": "i_mage_not_ai.render-evidence/1",
                "capture_source": "engine_runtime",
                "engine": "godot",
                "engine_version": "4.6.3",
                "platform": "desktop",
                "scenario_id": "motion",
                "timebase": "seconds",
                "resolution": [8, 8],
                "import_settings": {"renderer": "vulkan"},
                "captures": [
                    {"frame_index": 0, "timestamp": 0, "image": "frames/0.png", "event_ids": []},
                    {"frame_index": 1, "timestamp": 0.1, "image": "frames/1.png", "event_ids": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    trace = {
        "asset_type": "game_trace",
        "results": [{"algorithm": "velocity_magnitude", "measured": {"max": 10.0}}],
    }
    evidence, _ = load_render_evidence(evidence_path)
    report = analyze_render_evidence(
        evidence,
        {"trace_motion_bound": {"pixels_per_engine_unit": 1.0, "margin": 1.0}},
        trace_report=trace,
    )
    row = next(r for r in report["results"] if r["algorithm"] == "render_trace_motion_bound")
    assert row["status"] == "PASS"
    assert row["measured"]["max_centroid_step_px"] <= row["measured"]["bound_px"]


def test_cli_sprite_sheet_check(tmp_path: Path) -> None:
    frames = [Image.new("RGBA", (2, 2), (255, 0, 0, 255)), Image.new("RGBA", (2, 2), (255, 0, 0, 255))]
    sheet = tmp_path / "s.png"
    _strip(sheet, frames)
    policy = tmp_path / "p.json"
    policy.write_text(
        json.dumps(
            {
                "layout": "horizontal_strip",
                "frame_width": 2,
                "frame_height": 2,
                "max_bbox_height_variance": 0,
            }
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["sprite-sheet", "check", "--sheet", str(sheet), "--policy", str(policy)])
    assert result.exit_code == 0, result.output


def test_contract_schemas_load() -> None:
    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[1] / "schemas"
    for name in ("sprite-sheet-policy.schema.json", "lighting-policy.schema.json"):
        schema = json.loads((root / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
