# i-mage-not-ai skill segmentation trial

## Scope

- **Input:** `fox-forest.png` (1448×1086).
- **Segmentation source:** X-AnyLabeling headless `segment` output in `artifacts/xal-fox-candidates-01/` (model `groundingdino_swint_sam2_large-r20240806`). **XAL is required** for this trial; masks are not regenerated from hand-drawn polygons when XAL exports are absent.
- **Review:** Codex overlay review (`overlay-review.json`, contact sheets, `inspection-overlays/`); per-candidate detail in `xal-review-decisions.json`; 12-feature audit under `artifacts/xal-fox-review-01/`.
- **XAL weights:** `artifacts/xal-fox-candidates-01/inference-weights-revision.json` (refresh via `sync_xal_weight_revision.py`).
- **Review intent:** `review_intent_fox.json` (merged into `review-plan.json` by `run_cli_workflow.py`).
- **No hidden segmentation labels** — IoU/precision/recall against truth cannot be computed here.

## Skill CLI alignment

The trial follows `.agents/skills/i-mage-not-ai/SKILL.md` through:

1. v0.6 manifest with `feature_inventory` tied to XAL `candidate-*` IDs.
2. `plan` → programmatic `review_intent` → `review --plan --rules-file rules.yaml`.
3. `coverage` and `explain`.

Regenerate and rerun:

```sh
python3 artifacts/skill-segmentation-test/segment_features.py
python3 artifacts/skill-segmentation-test/run_cli_workflow.py
```

## What the latest review measures

After manifest v0.6 (occupancy, topology, silhouette, overlap, inventory completeness), a successful run exercises **20 planned checks**. Example rule families: `TOPOLOGY-001`, `CHARACTER-002`, `BACKGROUND-003`, `OVERLAP-001`, `FEATURE-COVERAGE-001`, plus metadata.

PASS/COMPLETE means those **declared pixel constraints** passed with full coverage. It still does **not** validate that mask boundaries match semantic part names.

## Visual assessment

- **Flower and mushroom:** XAL candidates align with visible props; boundaries remain coarse.
- **Fox parts:** Derived from whole-fox and part prompts; scarf/body/tail subtraction leaves approximate attachment edges.
- **Sky/mountain:** Union of two XAL prompts — coarse background, not separate sky vs mountain semantics.

## Result

The folder shows the Skill pipeline with mandatory XAL candidate provenance, v0.6 inventory, and multi-check CLI review. Boundary quality remains a **human/agent overlay review** problem until independent ground-truth masks exist.
