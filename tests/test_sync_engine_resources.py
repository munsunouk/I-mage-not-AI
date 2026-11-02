from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_engine_resources as sync


class SyncEngineResourcesTests(unittest.TestCase):
    def test_check_reports_stale_packaged_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_godot = root / "engine" / "godot"
            source_unity = root / "engine" / "unity"
            target_godot = root / "pkg" / "godot"
            source_godot.mkdir(parents=True)
            source_unity.mkdir(parents=True)
            target_godot.mkdir(parents=True)
            (source_godot / "keep.gd").write_text("extends Node\n", encoding="utf-8")
            (target_godot / "keep.gd").write_text("extends Node\n", encoding="utf-8")
            (target_godot / "orphan.gd").write_text("extends Node\n", encoding="utf-8")

            original_source = sync.SOURCE
            original_target = sync.TARGET
            try:
                sync.SOURCE = root / "engine"
                sync.TARGET = root / "pkg"
                self.assertEqual(sync.check(), 1)
            finally:
                sync.SOURCE = original_source
                sync.TARGET = original_target


if __name__ == "__main__":
    unittest.main()
