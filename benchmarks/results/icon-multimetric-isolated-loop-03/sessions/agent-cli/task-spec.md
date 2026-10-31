# Blind icon repair task

Repair the 24 supplied 128x128 RGBA fantasy inventory icons. Use one repair attempt per image. Preserve the intended icon artwork and all pixels that do not need correction.

Every input includes an image, a v0.5 manifest, and source-authored binary feature masks. The masks are aligned to that input: `silhouette` is the visible icon, `gem-pair` is its mirrored gem detail, and the two `gem` masks isolate uniform gem cores. Use the declared limits and findings supported by these inputs: palette (whole icon and masked gem), D65 CIELAB CIEDE2000, alpha-weighted centroid offset, four alpha-bbox margins, masked channel range, 8-connected components, silhouette component count/occupancy/bbox, horizontal reflection IoU, and the declared gem overlap constraint.

Save one corrected PNG per input under `outputs/sample-NN.png`, plus `decisions.json` with each sample's diagnosed rule IDs and concise evidence. Record every action. Keep the 128x128 canvas and transparent background. Do not look for evaluator labels or clean reference images.

Condition: before editing each image, run `i-mage-not-ai review --manifest <sample manifest> --output <report.json>`. Base the diagnosis and correction on the saved CLI JSON findings, then visually check the image. Save one report per sample under `cli-reports/sample-NN.json`.
