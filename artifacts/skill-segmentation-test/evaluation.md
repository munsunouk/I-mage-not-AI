# i-mage-not-ai skill segmentation trial

## Input and method

- Input: `fox-forest.png`, generated for this trial at 1448×1086.
- Agent-authored visual feature traces: fox character/head/body/tail/scarf, pink flower, blue mushroom, and a coarse distant sky/mountain region.
- Masks are manually traced polygons with visible occluded pixels clipped for scarf/body/tail/mushroom. `segment_features.py` recreates them and the overlay.
- The image has no ground-truth segmentation labels. Pixel precision, recall, IoU against truth, and a defensible overall accuracy score cannot be computed from this trial.

## Checks that passed

- All 8 masks are 1448×1086 and binary (0/255).
- All 8 masks have one 8-connected foreground component.
- `manifest validate` returned `VALID`.
- The required Skill CLI sequence (`inspect`, `manifest validate`, `delegate preview`, `delegate rules`, `plan`, `review`, `coverage`, `explain`) returned exit code 0 at every step.
- The saved review has `PASS` / `COMPLETE`, but it contains only `IMAGE-001`: source readability and SHA-256 equality. It does **not** measure mask-to-feature accuracy.

## Visual assessment

- **Flower and mushroom:** recognizable object extents; boundaries are coarse around petals, cap, and stem.
- **Fox head:** identifies ears and face as one feature, suitable for broad checks; fur tufts and cheek edge are simplified.
- **Fox scarf:** separated from the torso and head in the visible-pixel masks; the neck/chest boundary remains approximate.
- **Fox body and tail:** useful coarse parts, but the polygon edges do not follow fur contours closely and their attachment boundary is uncertain.
- **Distant sky/mountain:** intentionally a coarse background region, not separate sky and mountain masks. Do not use it for precise region-level checks.

## Result

This trial shows that the Skill workflow can produce organized, aligned masks and reproducible metadata for several general feature types. It does not demonstrate high-accuracy segmentation: the contours are hand-traced approximations, and the CLI has no semantic mask verifier. Treat the masks as a reviewable draft that needs human correction before precise per-feature measurements. To measure segmentation quality quantitatively, add independently authored ground-truth masks and compute per-feature IoU/precision/recall; that evaluation is outside the current CLI review report.
