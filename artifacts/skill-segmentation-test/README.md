# Skill segmentation trial (XAL → manifest → CLI)

End-to-end reference for `.agents/skills/i-mage-not-ai/SKILL.md` **steps 2–9** on `fox-forest.png`.

1. **XAL candidates (step 2):** Install XAL [PR #1485 `codex/headless-cli-inference`](../../docs/x-anylabeling-integration.md#headless-cli-install-skill-step-2), then run `xanylabeling segment`. Committed exports: `artifacts/xal-fox-candidates-01/` — GroundingSAM2 batch (23 shapes). Review overlays: `contact-sheet-*.jpg`.
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

| Folder | Role |
|--------|------|
| `artifacts/skill-segmentation-test/` | 8-feature CLI replay (v0.6, steps 8–9) |
| `artifacts/xal-fox-candidates-01/` | XAL step-2 exports |
| `artifacts/xal-fox-review-01/` | 12-feature overlay audit (reference) |

Replay locally (opt-in; not part of the default pytest run):

```sh
bash scripts/run_local_skill_flow.sh
# or: python3 -m pytest -q -m local_skill
```

## Limits

See `evaluation.md`. PASS means declared pixel constraints passed with complete coverage; it does not prove segmentation matches hidden labels.
