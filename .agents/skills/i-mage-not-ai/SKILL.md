---
name: i-mage-not-ai
description: Use X-AnyLabeling to propose image feature masks, review and approve them in Codex, then run deterministic i-mage-not-ai checks. Use for generated or existing image assets; this does not classify AI provenance or make subjective aesthetic judgments.
---

# I-mage-not-AI asset review

Use the existing checkout for this task; do not create a Git worktree.

## Project setup and policy profiles

- For a new project, establish its conventions once: color interpretation, coordinate system, units, timebase, and any documented asset specs. Keep these in project documentation/configuration with their source. Do not derive mandatory thresholds from visual inspection.
- Store reusable deterministic thresholds in one project rules file (prefer `<project>/.i_mage_not_ai/rules.yaml`). Build selector-based profiles with `asset_type`, `style`, and `feature_role`; reserve `feature_id` rules for documented asset-specific exceptions. Use increasing priorities for narrower rules. Keep measurement formulas/algorithm versions stable across profiles.
- For each asset, identify its actual class/style, select its approved masks/features or trace anchors, and pass the shared rules file to `delegate rules`, `plan`, and `review`. Before review, inspect the resolved rules so a broad default and a narrower override do not collide. Same-target, same-algorithm rules must either resolve by priority or fail as a configuration conflict; never rely on property overwrite order.
- An exception needs a short reason and a user/project source. Do not loosen a threshold just to make a failing asset pass. If a profile is missing a user requirement, report it as needing a threshold or implementation; do not invent a value.
- Treat only registered algorithms as executable. OpenPose, LPIPS, DINO embeddings/cosine similarity, learned anatomy checks, sprite direction/playback-contract checks, and any other unregistered measurement are unsupported until the CLI advertises them. State that they were not run; do not simulate them with unrelated metrics.
- If project conventions or profile thresholds already exist, reuse them instead of asking the user to repeat setup. If they do not, prepare a policy draft from known specifications and clearly mark missing decisions before using it for PASS/FAIL review.

## Roles and evidence

- X-AnyLabeling (XAL) produces first-pass candidate features/masks using a selected annotation model. Codex reviews those candidates against the unchanged source image, corrects the feature decomposition, and marks the final feature set. Do not treat raw model output as approved ground truth.
- `i-mage-not-ai` measures only registered algorithms against explicit manifest or project-policy thresholds. It does not infer semantics, evaluate taste, or decide whether an image is AI-generated or “AI slop.”
- Keep XAL candidate output, agent-approved feature metadata/masks, and CLI measurements as separate evidence stages. Every reported CLI result must come from the saved JSON report. Do not turn an agent-inferred feature or visual impression into a mandatory PASS/FAIL threshold.
- Use evidence-oriented findings: identify the final feature and affected region, report the measured value and threshold, state the rule and status, then give a concrete next step when action is needed. State coverage gaps and limitations; unknown or unmeasured is not PASS.

## Image workflow

1. Identify the target PNG, JPEG, WebP, or SVG, the user's explicit design constraints, relevant generation prompt, and any project policy or reference assets. Use the prompt/context to draft a feature inventory before segmentation; do not infer a universal list of features. Do not invent design intent or thresholds. Keep the source image unchanged and record its actual SHA-256.
2. **Generate X-AnyLabeling candidates through its headless inference CLI.** First verify the selected XAL build exposes `models` and `segment`; the upstream CLI may not include the local headless-inference extension. From the extended X-AnyLabeling checkout and its Python environment, discover available models and capabilities, then check the chosen model before inference:

   Run these from the extended XAL checkout root with its compatible Python environment. Put `--work-dir` before the subcommand when model data should live in a chosen directory:

   ```text
   python -m anylabeling.app --work-dir <model-data-dir> models list --task segmentation --json
   python -m anylabeling.app --work-dir <model-data-dir> models info <model-id> --json
   python -m anylabeling.app --work-dir <model-data-dir> models check <model-id> --device cpu --json
   python -m anylabeling.app --work-dir <model-data-dir> segment --input <image> --model <model-id> --prompt <feature> --output <candidate-dir> --json
   ```

   Use `segment --input <image> --model <model-id> --prompt <feature>` for promptable models. Repeat `--prompt` for each feature query, such as `character`, `hair`, or `leaf`. Image-only inference does not mean “find every feature”: GroundingSAM2 requires text prompts, SAM-style models may require point/rectangle marks, and class-based segmenters return only their learned classes. Select modes from reported model capabilities. `models check` does not download missing weights; model loading during `segment` can download configured weights, so make the target data directory and download behavior clear before starting. Do not install dependencies or switch to a remote model silently.

   `models check` is non-downloading. If it reports missing weights, `segment` can download the model files through XAL; state this before starting and use the chosen model-data directory. Proceed when the user requested or authorized that inference/download; otherwise ask before initiating a potentially large download. Save the native annotation, candidate metadata JSON, and one candidate mask per shape under a dedicated candidate directory. Preserve the exact source image and hash. Record XAL version, model/config, actual provider when exposed, prompts/marks, confidence settings, and every CLI result. If this extended CLI or a usable model/runtime is unavailable, stop this stage and report the blocker; do not substitute hand-traced masks or claim that the upstream release has the local inference extension.
3. **Review and finalize candidates in Codex.** Inspect the unchanged source image alongside an overlay/contact sheet of all candidate masks; do not approve candidates by reading labels or scores alone. Compare each mask to the source. Accept, reject, split, merge, rename, and refine candidates; identify important missing features. Use general visual features, not a human-only ontology: objects, object parts, materials, symbols, foreground/background regions, or lighting/shadow regions. Examples include an animal's eye, fur, tail, or horn; a plant's leaf, stem, flower, or fruit; and a scene's sky, ground, building, or vegetation. Avoid splitting unrelated pixels into meaningless regions. Preserve the mapping from each approved feature to its XAL candidate shape/mask where applicable. Record unresolved boundaries and review decisions explicitly. XAL scores indicate model confidence, not semantic approval.
4. **Create final measurement masks only for approved features and supported checks.** Each mask must be a same-size binary PNG: black is outside and any nonzero pixel is inside. Preserve source dimensions and alignment; do not resize or repaint the source. Use unique final feature IDs, meaningful roles, and `parent_id` for useful hierarchies. Feature masks may overlap when concepts overlap; explain the overlap and do not invent an overlap limit. Keep rejected/unreviewed candidates out of the approved feature list.
5. Save final masks and a v0.5 manifest in a dedicated review output directory, using paths relative to the manifest. Include the source image's actual SHA-256. For approved but visually inferred names/boundaries, set provenance to `agent_inferred`; retain candidate ID, XAL label, model/config, prompt, score, source shape index, and review decision in feature evidence when useful. The manifest `geometry` should point to each final approved mask. The CLI checks file paths, hashes, and mask dimensions, not whether a mask truly represents its semantic label.
6. **Bridge XAL output to the i-mage-not-ai contract.** XAL's `*.candidates.json` is candidate provenance, not a `feature-manifest` and not an approval record. Map only Codex-approved features into `features[]` with stable `id`, `role`, optional `parent_id`, `geometry: {"type": "mask", "path": "..."}`, and provenance. Keep the source asset hash in `asset.sha256`. There is currently no automatic XAL-to-approved-manifest command; create the manifest explicitly and do not mark an XAL candidate approved merely to make the CLI accept it.
7. Select only registered checks supported by the final manifest and evidence. Apply thresholds only when explicitly supplied by the user or project configuration. Existing mask-based checks include palette/luminance, color uniformity, silhouette components, symmetry, occupancy, periodic energy, and overlap. Do not claim these measure aesthetics, cross-part realism, or AI provenance. A deterministic PASS means declared checks passed with complete coverage; it does not prove the image is free of “AI slop.”
8. Run, in order:

   ```text
   i-mage-not-ai inspect <image>
   i-mage-not-ai manifest validate <manifest>
   i-mage-not-ai delegate preview --manifest <manifest>
   i-mage-not-ai delegate rules --manifest <manifest>
   i-mage-not-ai plan --manifest <manifest>
   i-mage-not-ai review --manifest <manifest> --output <review.json>
   i-mage-not-ai coverage --report <review.json>
   i-mage-not-ai explain <review.json>
   ```

9. Read the saved JSON report. Summarize each relevant finding with its feature ID, rule, measured value, threshold, status, and region. Distinguish `FAIL`, `INCONCLUSIVE`, `SKIPPED`, and incomplete coverage; unknown or unsupported coverage is not PASS. Keep the original image, generation prompt/context, XAL native candidate output, candidate masks/metadata, agent-approved masks, manifest, optional visual overlay, and `review.json` together so the result can be reproduced and inspected.
10. Edit an asset only when the user authorized repair. After a targeted edit, run `i-mage-not-ai verify --before <original> --after <edited> --report <review.json>` with an explicit `regression.allowed_mask` or `regression.allowed_region`, update the hash, and rerun the manifest checks.

## Game trace workflow

For animation or runtime evidence, use a canonical JSON trace or a versioned Godot/Unity export wrapper as described in `docs/game-engine-export.md`. Never execute a project or import scripts during review. Set `intent.kind` to `game_trace`, point `asset.path` to the trace, and declare explicit thresholds in `game_policy`. Run manifest validation, planning, review, and coverage as above, or use `i-mage-not-ai game analyze --trace <trace> --policy <policy.json>` for direct trace analysis.

## Reproducibility

The `i-mage-not-ai` CLI is offline and deterministic for a fixed image, masks, manifest, Python/dependency environment, and rule version. XAL's first-pass model output and the agent's semantic review are separate upstream evidence; preserve the exact candidate files, approved masks, and manifest used for every report. Palette counts use exact RGB values unless fixed Lab bins are explicitly configured. Raster gradient intent is not inferred, and SVG stroke-width checks inspect explicit values only. No automatic hook is assumed; run this Skill explicitly when generation or editing has finished.
