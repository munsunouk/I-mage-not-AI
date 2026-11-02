# Game capture, trace review, and gate

Use this document when the task is **runtime or engine-visible evidence**, not a static PNG/SVG review alone. A **game gate PASS** does not follow from image `review.json` PASS.

## Trace-only review (no project execution during review)

For animation or runtime **trace JSON**:

- Read `docs/game-engine-export.md`.
- Set manifest `intent.kind` to `game_trace`, `asset.path` to the trace, thresholds in `game_policy`.
- Run the same validate → plan → `review --plan` → coverage sequence as image assets, or:

```text
i-mage-not-ai game analyze --trace <trace> --policy <policy.json>
```

**Never** execute project code or import scripts during trace **review**.

Trace PASS does **not** prove pixels on screen matched the scenario.

## Visual capture (executes project code)

Steps when the user needs rendered frames:

1. **`i-mage-not-ai game capture`** — project, scene, scenario ID, dimensions, FPS, **`--allow-project-code`**.
   - Godot: bundled runtime runner.
   - Unity: run `project install-capture-adapter` first; GPU RenderTexture capture.
   - Godot events: event map; Unity: `i_mage_not_aiRenderCapture.MarkEvent()` in real handlers.
   - Render policy: `before_frames` / `after_frames` around events; boundary events → INCONCLUSIVE.
   - Multi-case: `game capture-suite` with a JSON matrix.
   - Unity: Screen Space Overlay canvases excluded unless a project compositor adapter exists.
   - Does not capture physical mobile OS composition.

2. **`game render-check`** — policy-driven checks on capture output.

3. **`i-mage-not-ai game gate`** — aggregate **three** reports with the **same scenario_id**:
   - trace (or trace-review) report — PASS/COMPLETE
   - runtime report — PASS/COMPLETE
   - render report — PASS/COMPLETE

```text
i-mage-not-ai game gate \
  --review-report <trace-review.json> \
  --runtime-report <runtime-report.json> \
  --render-report <render-report.json> \
  --output <game-gate.json>
```

Static image `review.json` is **not** accepted as the trace-review input.

## Partial XAL note (image pipeline only)

If resuming image segmentation (main Skill step 2), keep unreviewed prompts as `unreviewed` in `feature_inventory` and append new XAL exports rather than replacing candidate history without record.

## Related CLI exit codes

See main [SKILL.md](SKILL.md) — gate and `review` use exit 0/1/2; invalid inputs exit 3.
