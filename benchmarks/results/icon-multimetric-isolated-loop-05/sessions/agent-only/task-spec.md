# Icon audit repair task v2

You have 24 randomized 128x128 RGBA icons. They include clean examples, single faults and compound faults; some are AI-generated game icons. For each: inspect image and manifest, identify every registered failure, return rule IDs with concise evidence, and make one repair attempt only when a defect is supported. Leave clean icons untouched. Save one PNG per case and structured decisions.json with sample ID, diagnosed rule IDs, evidence and action. Keep edits targeted. Do not inspect clean references, evaluator files, or the other arm folder. Thresholds are shared by clean/single/compound variants of each source design.

The supplied mask is for the visible silhouette only; there are no semantic part masks. For the generated icons, only alpha centroid/margins, whole-image exact palette and silhouette connectivity/occupancy/bounds are available. Do not claim a semantic, symmetry, overlap, masked color, aesthetic or prompt-faithfulness check without evidence for it.

Condition: visual reasoning only. Do not run CLI, scripts, numerical measurement or another diagnostic tool.
