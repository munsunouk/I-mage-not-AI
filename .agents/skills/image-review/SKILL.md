---
name: image-review
description: Inspect and validate generated or edited images with deterministic imreview rules.
---

# Image review workflow

Use the existing checkout for this task; do not create a Git worktree.

For game evidence, use a canonical JSON trace or a versioned Godot/Unity export wrapper as described in `docs/game-engine-export.md`. Never execute a project or import scripts during review. Set manifest `intent.kind` to `game_trace`, point `asset.path` to the trace, and declare explicit thresholds in `game_policy`; run `manifest validate`, `plan`, `review`, and `coverage` as below. Use `imreview game analyze --trace <trace> --policy <policy.json>` for direct trace analysis.

1. Identify the target PNG, JPEG, WebP, or SVG and the user's explicit design constraints. Do not infer a desired constraint and present it as user intent.
2. Run `imreview inspect <image>` and create a v0.5 manifest following `schemas/feature-manifest.schema.json`. Use relative asset and mask paths and include the actual SHA-256. Record provenance (`user_spec`, `project_config`, `source_native`, or `agent_inferred`). Never invent measured values. The CLI verifies mask geometry, not semantic mask correctness.
3. Run `imreview manifest validate <manifest>`, `imreview delegate preview --manifest <manifest>`, `imreview delegate rules --manifest <manifest>`, and `imreview plan --manifest <manifest>`.
4. Run `imreview review --manifest <manifest> --output review.json`, then `imreview coverage --report review.json` and `imreview explain review.json`. Explain each measured result and its rule. Distinguish FAIL, INCONCLUSIVE, and INCOMPLETE; do not report any as PASS.
5. Only edit when the user intent authorizes a repair. After a targeted edit, run `imreview verify --before <original> --after <edited> --report review.json`; declare `regression.allowed_mask` for pixel-accurate edit regions or `regression.allowed_region` for a rectangle. Regenerate the asset hash and rerun every manifest rule.

The CLI is offline and deterministic for a fixed image, manifest, Python/dependency environment, and rule version. It performs no model inference and does not judge aesthetics or semantic correctness. Palette counts use exact RGB values unless fixed Lab bin sizes are explicitly given. SVG stroke-width checks read explicit values only. No automatic hook is assumed; run this Skill explicitly when generation has finished.
