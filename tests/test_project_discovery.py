from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from i_mage_not_ai.models import FeatureManifest
from i_mage_not_ai.engine_export import run_engine_export
from i_mage_not_ai.project_discovery import create_project_manifest, discover_projects, install_unity_exporter


class ProjectDiscoveryTest(unittest.TestCase):
    def test_godot_preview_finds_image_reference_without_running_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "sample-godot"
            (project / "art").mkdir(parents=True)
            (project / "scenes").mkdir()
            (project / ".godot" / "imported").mkdir(parents=True)
            (project / "project.godot").write_text(
                '[application]\nconfig/name="Sample Game"\nrun/main_scene="res://scenes/main.tscn"\n', encoding="utf-8")
            Image.new("RGBA", (8, 6), (20, 30, 40, 255)).save(project / "art" / "icon.png")
            Image.new("RGBA", (8, 6), (255, 0, 0, 255)).save(project / ".godot" / "imported" / "cached.png")
            (project / "scenes" / "main.tscn").write_text(
                '[gd_scene load_steps=2 format=3]\n[ext_resource type="Texture2D" path="res://art/icon.png" id="1"]\n', encoding="utf-8")
            (project / "scripts").mkdir()
            (project / "scripts" / "unsafe.gd").write_text('FileAccess.open("side-effect", FileAccess.WRITE)', encoding="utf-8")

            result = discover_projects(root)

            self.assertEqual(result["status"], "READY")
            self.assertTrue(result["read_only"])
            self.assertFalse(result["executed_project_code"])
            self.assertEqual(len(result["projects"]), 1)
            project_row = result["projects"][0]
            self.assertEqual(project_row["engine"], "godot")
            self.assertEqual(project_row["metadata"]["name"], "Sample Game")
            self.assertEqual(project_row["metadata"]["main_scene"], "scenes/main.tscn")
            self.assertEqual(project_row["asset_count"], 1)
            asset = project_row["assets"][0]
            self.assertEqual(asset["path"], "art/icon.png")
            self.assertEqual(asset["referenced_by"], ["scenes/main.tscn"])
            self.assertEqual(result["coverage"]["ignored_counts"]["generated_or_dependency_directory"], 1)
            self.assertFalse((project / "side-effect").exists())

    def test_unity_preview_resolves_texture_guid_and_sprite_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "sample-unity"
            assets = project / "Assets"
            settings = project / "ProjectSettings"
            (assets / "Sprites").mkdir(parents=True)
            settings.mkdir()
            (settings / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.3.25f1\n", encoding="utf-8")
            texture = assets / "Sprites" / "hero.png"
            Image.new("RGBA", (12, 10), (1, 2, 3, 255)).save(texture)
            guid = "1234567890abcdef1234567890abcdef"
            Path(f"{texture}.meta").write_text(
                f"fileFormatVersion: 2\nguid: {guid}\nTextureImporter:\n  spriteMode: 2\n", encoding="utf-8")
            (assets / "Main.unity").write_text(
                f"--- !u!213 &1\nSprite: {{fileID: 21300000, guid: {guid}, type: 3}}\n", encoding="utf-8")

            result = discover_projects(root)

            self.assertEqual(result["status"], "READY")
            project_row = result["projects"][0]
            self.assertEqual(project_row["engine"], "unity")
            self.assertEqual(project_row["metadata"]["editor_version"], "6000.3.25f1")
            asset = project_row["assets"][0]
            self.assertEqual(asset["referenced_by"], ["Assets/Main.unity"])
            self.assertEqual(asset["import_settings"]["sprite_mode"], 2)

    def test_manifest_draft_is_hash_pinned_and_contains_no_guessed_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            Image.new("RGB", (3, 2), (10, 20, 30)).save(root / "icon.jpg")
            manifest = create_project_manifest(root, "icon.jpg")
            output = root / "draft.json"
            output.write_text(json.dumps(manifest), encoding="utf-8")

            FeatureManifest.model_validate(manifest)

            self.assertEqual(manifest["asset"]["path"], "icon.jpg")
            self.assertEqual(len(manifest["asset"]["sha256"]), 64)
            self.assertEqual(manifest["features"], [])
            self.assertEqual(manifest["constraints"], {})
            self.assertFalse(manifest["discovery"]["thresholds_inferred"])

    def test_scan_limit_is_reported_as_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            (root / "one.txt").write_text("one", encoding="utf-8")
            (root / "two.txt").write_text("two", encoding="utf-8")

            result = discover_projects(root, max_files=1)

            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertFalse(result["coverage"]["complete"])
            self.assertIn("max_files_reached", result["coverage"]["ignored_counts"])

    def test_unity_exporter_install_is_explicit_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Assets").mkdir()
            (root / "ProjectSettings").mkdir()
            (root / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 1.0\n", encoding="utf-8")
            installed = install_unity_exporter(root)
            self.assertTrue(installed.is_file())
            self.assertIn("ExportFromCommandLine", installed.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                install_unity_exporter(root)

    def test_engine_execution_is_blocked_without_explicit_acknowledgment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "pass --allow-project-code"):
                run_engine_export(engine="godot", project_root=root / "missing", engine_executable=root / "missing.exe",
                                  selection="main.tscn", output=root / "trace.json", allow_project_code=False)


if __name__ == "__main__":
    unittest.main()
