"""Deterministic sprite, lighting, and extended render checks."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from i_mage_not_ai.render_evidence import analyze_render_evidence, load_render_evidence
from i_mage_not_ai.project_asset_check import check_project_assets
from i_mage_not_ai.sprite_sheet import analyze_sprite_sheet
from i_mage_not_ai.sprite_sheet_compare import compare_sprite_sheets
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


def test_sprite_loop_proxy_pass_and_fail(tmp_path: Path) -> None:
    layout = {"layout": "horizontal_strip", "frame_width": 2, "frame_height": 4}
    same = Image.new("RGBA", (2, 4), (0, 0, 0, 0))
    for y in range(2, 4):
        same.putpixel((0, y), (255, 0, 0, 255))
    mid = same.copy()
    mid.putpixel((1, 3), (0, 255, 0, 255))
    sheet_ok = tmp_path / "loop_ok.png"
    _strip(sheet_ok, [same, mid, same])
    report = analyze_sprite_sheet(sheet_ok, {**layout, "max_loop_changed_pixel_ratio": 0.01})
    row = next(r for r in report["results"] if r["algorithm"] == "sprite_loop_changed_pixel_ratio")
    assert row["status"] == "PASS"

    sheet_bad = tmp_path / "loop_bad.png"
    end = same.copy()
    end.putpixel((1, 2), (0, 0, 255, 255))
    _strip(sheet_bad, [same, mid, end])
    report_bad = analyze_sprite_sheet(sheet_bad, {**layout, "max_loop_changed_pixel_ratio": 0.01})
    row_bad = next(r for r in report_bad["results"] if r["algorithm"] == "sprite_loop_changed_pixel_ratio")
    assert row_bad["status"] == "FAIL"


def test_sprite_foot_metrics_measure_only(tmp_path: Path) -> None:
    frames = []
    for _ in range(2):
        img = Image.new("RGBA", (4, 8), (0, 0, 0, 0))
        for y in range(4, 8):
            for x in range(1, 3):
                img.putpixel((x, y), (200, 100, 50, 255))
        frames.append(img)
    sheet = tmp_path / "feet.png"
    _strip(sheet, frames)
    report = analyze_sprite_sheet(
        sheet,
        {
            "layout": "horizontal_strip",
            "frame_width": 4,
            "frame_height": 8,
            "include_foot_metrics": True,
            "max_ground_line_y_variance": 0.0,
            "max_feet_center_x_variance": 0.0,
        },
    )
    row = next(r for r in report["results"] if r["algorithm"] == "sprite_foot_metrics")
    assert row["status"] == "PASS"
    assert len(row["measured"]["frames"]) == 2
    assert row["measured"]["frames"][0]["feet_pivot_xy"] is not None


def test_sprite_sheet_compare_ppu_spread(tmp_path: Path) -> None:
    layout = {"layout": "horizontal_strip", "frame_width": 4, "frame_height": 16}

    def single_frame_sheet(path: Path, draw_rows: int) -> None:
        img = Image.new("RGBA", (4, 16), (0, 0, 0, 0))
        for y in range(16 - draw_rows, 16):
            for x in range(4):
                img.putpixel((x, y), (255, 0, 0, 255))
        img.save(path)

    single_frame_sheet(tmp_path / "a.png", 16)
    single_frame_sheet(tmp_path / "b.png", 8)
    policy_path = tmp_path / "compare.json"
    policy_path.write_text(
        json.dumps(
            {
                "reference_height_m": 1.8,
                "max_relative_ppu_spread": 0.05,
                "shared_layout": layout,
                "sheets": [
                    {"id": "hero", "path": "a.png"},
                    {"id": "npc", "path": "b.png"},
                ],
            }
        ),
        encoding="utf-8",
    )
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    report = compare_sprite_sheets(policy, policy_dir=tmp_path)
    assert report["status"] == "FAIL"
    ppu = next(r for r in report["results"] if r["algorithm"] == "sprite_sheet_ppu_spread")
    assert ppu["status"] == "FAIL"


def test_project_asset_completeness(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
    policy = {
        "project_root": ".",
        "required_paths": ["assets/hero.png", "missing.json"],
        "required_globs": ["assets/*.png"],
    }
    report = check_project_assets(tmp_path, policy)
    assert report["status"] == "FAIL"
    paths_row = next(r for r in report["results"] if r["algorithm"] == "project_required_paths")
    assert "missing.json" in paths_row["measured"]["missing"]
    globs_row = next(r for r in report["results"] if r["algorithm"] == "project_required_globs")
    assert globs_row["status"] == "PASS"


def test_cli_sprite_sheet_compare_and_check_assets(tmp_path: Path) -> None:
    img = Image.new("RGBA", (2, 4), (255, 0, 0, 255))
    for name in ("s1.png", "s2.png"):
        img.save(tmp_path / name)
    compare_policy = tmp_path / "cmp.json"
    compare_policy.write_text(
        json.dumps(
            {
                "reference_height_m": 1.0,
                "max_relative_bbox_height_spread": 0.0,
                "shared_layout": {"layout": "horizontal_strip", "frame_width": 2, "frame_height": 4},
                "sheets": [{"id": "a", "path": "s1.png"}, {"id": "b", "path": "s2.png"}],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    assert runner.invoke(app, ["sprite-sheet", "compare", "--policy", str(compare_policy)]).exit_code == 0

    asset_policy = tmp_path / "assets.json"
    asset_policy.write_text(
        json.dumps({"project_root": ".", "required_paths": ["s1.png", "s2.png"]}),
        encoding="utf-8",
    )
    assert runner.invoke(app, ["project", "check-assets", "--path", str(tmp_path), "--policy", str(asset_policy)]).exit_code == 0


def test_contract_schemas_load() -> None:
    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[1] / "schemas"
    for name in (
        "sprite-sheet-policy.schema.json",
        "sprite-sheet-compare-policy.schema.json",
        "project-asset-policy.schema.json",
        "lighting-policy.schema.json",
    ):
        schema = json.loads((root / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
