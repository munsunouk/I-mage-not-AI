# Optional image review extensions

Use only when the user or project explicitly requests these measurements. They are **not** part of the default Skill steps 7–9 `review --plan` path unless the manifest declares matching properties and the plan includes the corresponding rules.

## Character anatomy (OpenPose BODY_25)

Save OpenPose BODY_25 JSON separately, then:

```text
i-mage-not-ai character anatomy --image <image> --openpose-json <keypoints.json> --policy <anatomy-policy.json> --output <anatomy-report.json>
```

Configure species/style/pose-specific bone ratios and joint-angle limits from an approved source. OpenPose is not bundled; its license restricts noncommercial research use. Detections are estimates; BODY_25 is not for non-human skeletons.

## Mask geometry extensions

When declared on feature `properties` in the manifest, raster review can include:

- `max_holes` — enclosed holes in the mask
- `min_width_px` — minimum local thickness
- `reference_mask` with `max_boundary_distance_px`, `min_iou`, and/or `min_dice`
- `max_skeleton_endpoints` / `max_skeleton_branches` — morphological skeleton graph
- `max_hu_shape_distance` — Hu moments vs a same-size reference mask
- `min_tenengrad` / `min_boundary_gradient` — Sobel energy inside the mask

Empty masks or missing reference evidence → INCONCLUSIVE.

## Perceptual similarity (optional dependency)

Requires `pip install -e ".[perceptual]"` and locally cached weights (no CLI download):

```text
i-mage-not-ai similarity --metric lpips --reference <reference> --candidate <image> --max-distance <limit>
i-mage-not-ai similarity --metric dinov2 --reference <reference> --candidate <image> --model-dir <local-model> --min-similarity <limit>
```

Scores are model/config-specific diagnostics, not identity or overall quality proof.

## Batch inventory and project assets

When the user needs a file list or completeness gate—not feature masks:

```text
i-mage-not-ai scan images --path <dir-or-file> --csv scan.csv
i-mage-not-ai project preview --path <root> --csv images.csv
i-mage-not-ai project check-assets --path <scan-root> --policy <project-asset-policy.json>
```

See [supplementary-skill-flows.md](supplementary-skill-flows.md) and [project-discovery.md](../../../docs/project-discovery.md).

## Sprite sheet and lighting (policy JSON)

Deterministic checks without manifest masks when the user supplies frame geometry and thresholds:

```text
i-mage-not-ai sprite-sheet check --sheet <png> --policy <sprite-sheet-policy.json>
i-mage-not-ai sprite-sheet compare --policy <sprite-sheet-compare-policy.json>
i-mage-not-ai lighting check --image <png> --policy <lighting-policy.json>
```

See [sprite-lighting-policy.md](../../../docs/sprite-lighting-policy.md).
