# i-mage-not-ai skill segmentation trial

## Scope

- **Input:** `fox-forest.png` (1448×1086).
- **Approved masks:** agent manual polygons via `segment_features.py` (visible-pixel clipping for occlusion).
- **XAL branch:** `artifacts/xal-fox-candidates-01/` holds 23 GroundingSAM2 candidates for the same image; inventory records that batch as **rejected** in favor of the manual trace. Overlay review of XAL shapes is still outstanding in that export.
- **No hidden segmentation labels** — IoU/precision/recall against truth cannot be computed here.

## Skill CLI alignment

The trial follows `.agents/skills/i-mage-not-ai/SKILL.md` through:

1. v0.6 manifest with `feature_inventory` and declared feature properties.
2. `plan` → programmatic `review_intent` → `review --plan --rules-file rules.yaml`.
3. `coverage` and `explain`.

Regenerate and rerun:

```sh
python artifacts/skill-segmentation-test/segment_features.py
python artifacts/skill-segmentation-test/run_cli_workflow.py
```

## What the latest review measures

After manifest v0.6 (occupancy, topology, silhouette, overlap, inventory completeness), a successful run exercises **20 planned checks** (not IMAGE-001 alone). Example rule families: `TOPOLOGY-001`, `CHARACTER-002`, `BACKGROUND-003`, `OVERLAP-001`, `FEATURE-COVERAGE-001`, plus metadata.

PASS/COMPLETE means those **declared pixel constraints** passed with full coverage. It still does **not** validate that mask boundaries match semantic part names.

## Visual assessment

- **Flower and mushroom:** recognizable extents; coarse boundaries.
- **Fox parts:** useful coarse regions; fur-level precision is not claimed.
- **Distant sky/mountain:** intentional coarse background patch — not separate sky vs mountain semantics.

## Result

The folder shows the Skill can produce aligned masks, inventory provenance, and a multi-check CLI review. Segmentation quality remains a **human/agent review** problem until independent ground-truth masks exist.
