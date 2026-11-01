"""Run and capture the commands specified by the i-mage-not-ai Skill."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
CLI = REPO / ".venv" / "Scripts" / "i-mage-not-ai.exe"
MANIFEST = Path("artifacts/skill-segmentation-test/manifest.json")
SOURCE = Path("artifacts/skill-segmentation-test/fox-forest.png")
REPORT = Path("artifacts/skill-segmentation-test/review.json")

steps = [
    ("inspect", ["inspect", str(SOURCE)]),
    ("manifest_validate", ["manifest", "validate", str(MANIFEST)]),
    ("delegate_preview", ["delegate", "preview", "--manifest", str(MANIFEST)]),
    ("delegate_rules", ["delegate", "rules", "--manifest", str(MANIFEST)]),
    ("plan", ["plan", "--manifest", str(MANIFEST)]),
    ("review", ["review", "--manifest", str(MANIFEST), "--output", str(REPORT)]),
    ("coverage", ["coverage", "--report", str(REPORT)]),
    ("explain", ["explain", str(REPORT)]),
]

results = []
for name, args in steps:
    completed = subprocess.run([str(CLI), *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    (OUT / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (OUT / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    results.append({"step": name, "argv": [str(CLI), *args], "exit_code": completed.returncode})

(OUT / "cli-run.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
