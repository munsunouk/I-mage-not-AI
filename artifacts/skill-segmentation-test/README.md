# Skill segmentation trial (partial end-to-end)

This folder demonstrates the **agent-approved mask path** of the i-mage-not-ai Skill. X-AnyLabeling candidates for the same source image live under `artifacts/xal-fox-candidates-01/` (23 shapes, still **unreviewed** in that export).

## Regenerate masks and manifest

```sh
python artifacts/skill-segmentation-test/segment_features.py
python artifacts/skill-segmentation-test/evaluate_masks.py
```

Manifest schema **0.6** includes `feature_inventory` entries that map each approved feature to a manual polygon trace and record the XAL batch as rejected (not used for measurement).

## Run the Skill CLI sequence

Matches `.agents/skills/i-mage-not-ai/SKILL.md` steps 9–9: `plan` → fill `review_intent` → `review --plan`.

```sh
python artifacts/skill-segmentation-test/run_cli_workflow.py
```

Requires an editable install: `python -m pip install -e .`

## Limits

See `evaluation.md`. PASS here means declared pixel constraints passed with complete coverage; it does not prove segmentation accuracy against hidden labels.
