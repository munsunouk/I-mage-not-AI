"""Skill / XAL fox trial checks — local only (opt-in via pytest marker local_skill)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
SKILL_TRIAL = ROOT / "artifacts" / "skill-segmentation-test"
XAL_CANDIDATES = ROOT / "artifacts" / "xal-fox-candidates-01"


@pytest.mark.local_skill
class SkillFlowLocalTest(unittest.TestCase):
    def test_skill_evidence_validation_script(self):
        script = SKILL_TRIAL / "validate_skill_evidence.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)

    def test_fox_manifest_v06_validates(self):
        manifest_schema = json.loads((SCHEMAS / "feature-manifest.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((SKILL_TRIAL / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "0.6")
        Draft202012Validator(manifest_schema).validate(manifest)

    def test_xal_candidate_export_present(self):
        self.assertTrue((XAL_CANDIDATES / "candidates" / "fox-forest.png.candidates.json").is_file())
        self.assertTrue((XAL_CANDIDATES / "masks" / "fox-forest.png" / "candidate-0001.png").is_file())

    def test_skill_cli_workflow_replay(self):
        script = SKILL_TRIAL / "run_cli_workflow.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
