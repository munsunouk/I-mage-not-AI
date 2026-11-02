# Algorithm and literature map (inspection gaps)

This document records how **external methods and papers** relate to **I-mage-not-AI inspection gaps**. It is a maintenance guide for scope and prioritization—not a metric suite and not automatic PASS/FAIL.

**Related registries**

| Artifact | Role |
| --- | --- |
| [`i_mage_not_ai/rules/algorithms.yaml`](../i_mage_not_ai/rules/algorithms.yaml) | Implemented algorithm IDs, adapter, version |
| [`docs/algorithm-catalog.md`](algorithm-catalog.md) | Full ID list: measurement, CLI entry, packs, when to use |
| [`i_mage_not_ai/rules/packs.yaml`](../i_mage_not_ai/rules/packs.yaml) | Which algorithms belong to which asset/tower pack |
| [`docs/game-policy-reference.md`](game-policy-reference.md) | Trace / runtime / render policy keys |
| [`docs/sprite-lighting-policy.md`](sprite-lighting-policy.md) | Sprite sheet and lighting CLI policies |
| [`docs/learned-character-checks.md`](learned-character-checks.md) | Optional LPIPS / DINOv2 (local weights) |
| [`artifacts/metric-audit-2026-10-31/external-review.md`](../artifacts/metric-audit-2026-10-31/external-review.md) | Icon loop vs T2I / preference literature |

**Status legend**

| Status | Meaning |
| --- | --- |
| **Implemented** | Shipped CLI or manifest path; ID in `algorithms.yaml` |
| **Diagnostic** | Number computed; PASS/FAIL only with explicit project threshold (often `INCONCLUSIVE` without one) |
| **Optional learned** | Available via `similarity` or `[perceptual]` extra; not default gate/CI |
| **Deferred** | Deterministic candidate; not implemented yet |
| **Out of scope** | Different construct (semantics, preference, video physics, etc.) |

---

## Game and render towers

| Inspection gap | Typical methods in literature | Deterministic vs learned | Our status | Algorithm ID / entry point |
| --- | --- | --- | --- | --- |
| Motion, velocity, acceleration, jerk | Kinematic finite differences on sampled tracks | Deterministic | **Implemented** | `velocity_magnitude`, `acceleration_magnitude`, `jerk_magnitude` — `game analyze` |
| Loop / pose / rotation continuity | Boundary distance on tracks | Deterministic | **Implemented** | `loop_boundary_difference`, `pose_boundary_distance`, `rotation_distance` |
| Event timing | Timestamp vs expected | Deterministic | **Implemented** | `event_timing_difference` (trace), `render_event_frame_alignment`, `runtime_callback_timing` |
| Particles (trace + runtime) | Lifetime, bounds, alive count | Deterministic | **Implemented** | `particle_*`, `runtime_particle_*` |
| Layer occlusion in trace | Alpha-weighted overlap | Deterministic | **Implemented** | `alpha_weighted_occlusion` |
| Adjacent render frame change | Pixel delta ratio | Deterministic | **Implemented** | `render_changed_pixel_ratio` |
| Flash / photosensitivity | Luminance-delta area over time | Deterministic | **Implemented** | `render_flash_metrics` |
| ROI vs reference capture | Cropped hash or changed-pixel vs PNG oracle | Deterministic | **Implemented** | `render_roi_oracle` — `game render-check` `roi_oracles` |
| On-screen motion vs trace speed | Centroid / flow magnitude vs kinematic bound | Deterministic (classical CV) | **Implemented** | `render_trace_motion_bound` + `--trace-report` |
| Full-scene perceptual video quality | VBench, VBench-2.0 temporal/physics axes | Learned + human prefs | **Out of scope** | Static PNG captures + explicit policies only; see [external-review](../artifacts/metric-audit-2026-10-31/external-review.md) |
| Engine headless CI for every PR | Custom harness | Process | **Out of scope** | Local `doctor --game-fixture`; no default engine CI job |

---

## Sprite sheet and 2D animation art

| Inspection gap | Typical methods in literature | Deterministic vs learned | Our status | Algorithm ID / entry point |
| --- | --- | --- | --- | --- |
| Foot / baseline consistency | Bottom-row or anchor Y variance across frames | Deterministic | **Implemented** | `sprite_baseline_y_variance` — `sprite-sheet check` |
| Frame silhouette height stability | Bbox height variance | Deterministic | **Implemented** | `sprite_bbox_height_variance` |
| Palette drift across frames | Set inclusion / palette count | Deterministic | **Implemented** | `sprite_inter_frame_palette_subset`; manifest `exact_palette_count` / `masked_palette_count` |
| Animation delta magnitude | Changed-pixel ratio between frames | Deterministic | **Implemented** | `sprite_inter_frame_changed_pixel_ratio`, `sprite_reference_frame_changed_pixel_ratio` |
| Perceptual “same character” across frames | LPIPS, DINO, SSIM | Learned / statistical | **Optional learned** | `lpips_similarity`, `dinov2_cosine_similarity` — diagnostic with explicit threshold |
| FLIP / deep video consistency | FLIP, warping-based metrics | Learned | **Out of scope** | Not registered; pixel-art oracle path preferred |

---

## Lighting and shading

| Inspection gap | Typical methods in literature | Deterministic vs learned | Our status | Algorithm ID / entry point |
| --- | --- | --- | --- | --- |
| Global light direction | Linear plane on luminance; gradient angle | Deterministic | **Implemented** | `lighting_declared_direction_alignment`, `lighting_luma_plane_fit` — `lighting check` |
| Chromatic shading (shared shading, different albedo) | Intrinsic / Barron & Malik-style RGB plane alignment | Deterministic (simplified) | **Implemented** | `lighting_chromatic_shading_direction_cosine` (pairwise R/G/B plane direction cosines) |
| Light direction stable across animation frames | Variance of fitted direction | Deterministic | **Implemented** | `lighting_cross_frame_direction_variance` (with `sheet_layout`) |
| Foreground vs context lighting harmony | Cross-feature plane cosine | Deterministic | **Diagnostic** | `compare` → `lighting_diagnostic` in measurements (no inferred PASS/FAIL) |
| Full intrinsic decomposition (albedo / shading split) | Barron & Malik CVPR 2013, later intrinsic networks | Mixed (classic vs learned) | **Deferred** | Only plane-fit proxies; no full intrinsic solver |
| Learned lighting realism score | Generative metrics, preference models | Learned | **Out of scope** | Same construct gap as PickScore/ImageReward for “looks lit well” |

Reference (concept, not bundled): Barron, J. T., & Malik, J., *Shape, Illumination, and Reflectance from Shading*, TPAMI 2015 (intrinsic shading decomposition lineage).

---

## Static image / manifest (icons, characters, backgrounds)

| Inspection gap | Typical methods in literature | Deterministic vs learned | Our status | Algorithm ID / entry point |
| --- | --- | --- | --- | --- |
| Declared palette / color limits | Exact or quantized palette count, ΔE uniformity | Deterministic | **Implemented** | `exact_palette_count`, `masked_palette_count`, `ciede2000_uniformity` — `review` |
| Mask topology / shape | Components, holes, skeleton, IoU | Deterministic | **Implemented** | `mask_*`, `silhouette_metrics` |
| Tileable backgrounds | Edge color error, FFT periodicity | Deterministic | **Implemented** | `tile_edge_color_error`, `fft_periodic_energy_ratio` |
| Prompt / object faithfulness | GenEval, TIFA (VQA on questions) | Learned + human eval | **Out of scope** | Human/agent supplies masks and policies; CLI does not score prompt meaning |
| Aesthetic preference | Pick-a-Pic, ImageReward | Learned | **Out of scope** | See [external-review](../artifacts/metric-audit-2026-10-31/external-review.md) |
| Icon recognizability / search | McDougall et al. icon usability tasks | Human study | **Unmeasured** | Requires product-sized user tasks, not automatic lint |
| Distribution quality (FID, CMMD) | Image-set metrics | Statistical | **Out of scope** | Per-asset explicit constraints, not corpus FID |

---

## Deferred deterministic candidates (low priority)

These appeared in gap reviews as **possible** oracles without ML. They are **not** in `algorithms.yaml` yet.

| Gap | Typical approach | Why deferred |
| --- | --- | --- |
| Shadow consistency | Histogram or shape of dark regions vs declared light | Needs ROI policy and art-direction-specific thresholds |
| Depth / point-cloud vs mesh | Render depth buffer vs reference cloud | Requires engine export contract and reference assets |
| Classical dense optical flow bound | Farneback/Lucas–Kanade max flow vs trace | Overlaps centroid bound; higher false-positive risk on effects |

---

## How to use this map

1. **Before adding an algorithm** — Pick a row, confirm the construct matches what you want to claim (constraint compliance vs semantics vs preference).
2. **Before citing a paper** — Check **Out of scope** / **Unmeasured**; citing VBench or GenEval does not imply this repo implements them.
3. **When updating code** — Add or rename IDs in `algorithms.yaml`, pack membership in `packs.yaml`, and update the matching row here in the same PR.

---

## Primary external reading (summary)

For T2I and benchmark context (icons and masks), see the numbered list in [`artifacts/metric-audit-2026-10-31/external-review.md`](../artifacts/metric-audit-2026-10-31/external-review.md) (GenEval, TIFA, PickScore, ImageReward, FID/CMMD, VBench, LPIPS, icon usability, T2IScoreScore). For optional learned similarity in this repo, see [`docs/learned-character-checks.md`](learned-character-checks.md).
