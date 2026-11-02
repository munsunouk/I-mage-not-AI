# Skill segmentation trial (XAL → manifest → CLI)

End-to-end reference for `.agents/skills/i-mage-not-ai/SKILL.md` **steps 2–9** on `fox-forest.png`.

1. **XAL candidates (step 2):** `artifacts/xal-fox-candidates-01/` — GroundingSAM2 batch (`segment`, 23 shapes). Review overlays: `contact-sheet-*.jpg`.
2. **Codex review (steps 3–4):** Approve/reject/refine candidates using contact sheets and `inspection-overlays/`; structured log in `overlay-review.json`, detail in `xal-review-decisions.json`.
3. **Manifest v0.6 (step 5):** `segment_features.py` materializes approved masks from XAL PNGs (no hand-traced substitute for missing XAL).
4. **CLI (steps 8–9):** `run_cli_workflow.py` runs `plan` → merges `review_intent_fox.json` → `review --plan` (manifest-relative paths in `review.json`).

## Regenerate

```sh
python3 artifacts/skill-segmentation-test/segment_features.py
python3 artifacts/skill-segmentation-test/evaluate_masks.py
python3 artifacts/skill-segmentation-test/run_cli_workflow.py
```

Requires editable install: `python3 -m pip install -e .`

## Limits

See `evaluation.md`. PASS means declared pixel constraints passed with complete coverage; it does not prove segmentation matches hidden labels.
