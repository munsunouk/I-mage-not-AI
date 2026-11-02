#!/usr/bin/env bash
# Local-only Skill fox trial: XAL artifact replay + CLI workflow + pytest local_skill.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 artifacts/skill-segmentation-test/segment_features.py
python3 artifacts/skill-segmentation-test/run_cli_workflow.py
python3 -m pytest -q -m local_skill
