"""Local-only cross-checks for fox Skill evidence (opt-in pytest marker)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
TRIAL = Path(__file__).parent
SCHEMAS = ROOT / "schemas"

sys.path.insert(0, str(ROOT))
from i_mage_not_ai.doctor import validate_overlay_inventory_alignment  # noqa: E402


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def main() -> None:
    manifest = json.loads((TRIAL / "manifest.json").read_text(encoding="utf-8"))
    overlay = json.loads((TRIAL / "overlay-review.json").read_text(encoding="utf-8"))
    intent_doc = json.loads((TRIAL / "review_intent_fox.json").read_text(encoding="utf-8"))
    weights = json.loads(
        (ROOT / "artifacts/xal-fox-candidates-01/inference-weights-revision.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(load_schema("overlay-review.schema.json")).validate(overlay)
    Draft202012Validator(load_schema("xal-weights-revision.schema.json")).validate(weights)
    Draft202012Validator(load_schema("review-intent-fox-trial.schema.json")).validate(intent_doc)

    errors = validate_overlay_inventory_alignment(manifest, overlay)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps({"status": "OK", "checks": ["schemas", "overlay_inventory_alignment"]}, indent=2))


if __name__ == "__main__":
    main()
