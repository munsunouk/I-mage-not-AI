# Algorithm catalog (full registry)

Every ID in [`i_mage_not_ai/rules/algorithms.yaml`](../i_mage_not_ai/rules/algorithms.yaml) with **what it measures**, **how to run it**, **rule packs**, and **when to use it**. Thresholds always come from project policy or JSON policy files—the CLI does not invent limits.

Related: [packs.yaml](../i_mage_not_ai/rules/packs.yaml), [algorithm-literature-map.md](algorithm-literature-map.md), [rule-authoring.md](rule-authoring.md).

**Entry point legend**

| Entry point | Meaning |
| --- | --- |
| `review` | `i-mage-not-ai review --manifest …` (and `plan`, `measure`, `inspect` where the rule applies) |
| `rules-file` | Project YAML via `--rules-file` (required for some algorithms not in default manifest rules) |
| `game analyze` | `i-mage-not-ai game analyze --trace … --policy …` or manifest `intent.kind=game_trace` |
| `runtime-check` | `i-mage-not-ai game runtime-check --evidence … --policy …` |
| `render-check` | `i-mage-not-ai game render-check --evidence … --policy …` |
| `sprite-sheet check` | `i-mage-not-ai sprite-sheet check --sheet … --policy …` |
| `sprite-sheet compare` | `i-mage-not-ai sprite-sheet compare --policy …` |
| `project check-assets` | `i-mage-not-ai project check-assets --path … --policy …` |
| `project preview` | `i-mage-not-ai project preview --path …` (optional `--asset-policy` embeds completeness) |
| `lighting check` | `i-mage-not-ai lighting check --image … --policy …` |
| `character anatomy` | `i-mage-not-ai character anatomy --openpose-json … --policy …` |
| `similarity` | `i-mage-not-ai similarity --metric lpips\|dinov2 …` |
| `compare` | `i-mage-not-ai compare …` (cross-feature diagnostics only) |
| `scan images` | `i-mage-not-ai scan images --path …` (batch inspect + optional `--csv`) |
| `advisory detect` | `i-mage-not-ai advisory detect …` (non-gating external detector) |
| `serve` | `i-mage-not-ai serve` (optional `[api]` extra) |

Pack column lists [`packs.yaml`](../i_mage_not_ai/rules/packs.yaml) membership; **—** means no pack (still valid via manifest inline constraints or `rules-file`).

---

## Source and raster (manifest / review)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `image_metadata` | Asset readable, dimensions, optional SHA-256 match | `review` (always planned as IMAGE-001) | — | Every review pass; pins the file before any pixel rule runs. |
| `alpha_occupancy` | Transparent pixel fraction and alpha bounding box | `review` when manifest declares alpha occupancy limits | — | Icons/UI that must not be empty or must fill a minimum canvas area. |
| `alpha_centroid_offset` | Alpha centroid offset from image center (normalized) | `review` | icon | Centered icons, HUD glyphs, and symmetric layout specs. |
| `alpha_margin_ratio` | Normalized transparent margin around alpha bounds | `review` | icon | Safe padding for scaling, mipmaps, and store icon templates. |
| `exact_palette_count` | Distinct visible RGB colors (exact tuples) | `review` | icon | Flat icons and pixel art with hard palette caps (global canvas). |
| `masked_palette_count` | Distinct RGB inside a feature mask | `review` | icon, character | Per-part palette limits (body vs outline vs gem). |
| `quantized_palette_count` | Colors after fixed Lab bin quantization | `review` + **`rules-file`** | — | Same intent as masked/exact palette with project-defined bin grid; typical in YAML project rules. |
| `masked_color_uniformity` | RGB channel range inside a solid mask | `review` | background | Flat fills and UI panels that must not drift in channel spread. |
| `ciede2000_uniformity` | Lab ΔE00 vs reference or median; exceedance ratio | `review` | icon, character | Allowed subtle shading within a “solid” feature without breaking ΔE budget. |
| `mask_connected_components` | 8-connected component count in binary mask | `review` | character | Single-blob features; catches fragmented masks after repair. |
| `mask_hole_count` | Enclosed 4-connected holes in mask | `review` | character | Donut shapes, ring icons, or forbidden interior voids. |
| `mask_skeleton_endpoints` | Skeleton endpoint count | `review` | character | Thin strokes, branches, and line-art topology checks. |
| `mask_skeleton_branches` | Skeleton branch cluster count | `review` | character | Complexity limits on line art and character outlines. |
| `mask_minimum_width` | Minimum local width via distance transform on skeleton | `review` | character | Readability at target display size (stroke not too thin). |
| `mask_boundary_distance` | Symmetric Hausdorff distance between mask boundaries (px) | `review` | character | Approved mask vs candidate/repair boundary deviation. |
| `mask_iou_dice` | IoU between candidate and reference mask | `review` | character | Quantitative mask agreement after agent or tool edits. |
| `mask_dice` | Dice coefficient between masks | `review` | character | Same as IoU use case; alternative metric for small regions. |
| `mask_hu_shape_distance` | Hu moment descriptor distance vs reference | `review` | character | Rough shape class match when pixel alignment differs slightly. |
| `mask_intersection_ratio` | Intersection area / union of two feature masks | `review` + **`rules-file`** (feature pair) | character | Overlap budgets (face/hair, gem/silhouette) from project rules. |
| `mask_reflection_iou` | Mask vs horizontal reflection IoU | `review` | character | Bilateral symmetry requirements on icons or characters. |
| `roi_tenengrad_sharpness` | Mean squared Sobel gradient inside mask | `review` | character | Blur or over-softening inside a ROI (not global aesthetic score). |
| `mask_boundary_gradient` | Mean Sobel magnitude on mask boundary | `review` | character | Crisp vs soft edges on feature outline. |
| `masked_luma_levels` | Count of occupied quantized luma bands in mask | `review` | character | Limited shading steps (banding / posterization policy). |
| `silhouette_metrics` | Silhouette area, bounds, component count | `review` | character | Global character read and fragment detection on silhouette role. |
| `region_occupancy` | Mask area / canvas fraction | `review` | background | Background motifs that must cover a declared fraction of tile. |
| `tile_edge_color_error` | Exact RGB error on opposing tile edges | `review` | background | Seamless tiling for patterns and terrain textures. |
| `fft_periodic_energy_ratio` | Non-DC energy at periodic FFT peaks in mask | `review` | background | Detect unintended repeating pattern strength in a region. |
| `linear_gradient_fit_diagnostic` | RGB plane fit R² on raster | `review` | background | **Diagnostic only**—records gradient-like drift without PASS/FAIL unless you add a separate policy interpretation. |
| `raster_gradient_semantic_check` | Placeholder: raster cannot prove semantic gradient intent | `review` | — | Explicitly **INCONCLUSIVE** so agents do not treat gradient tags as verified. |

---

## SVG (manifest / review)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `svg_gradient_declarations` | Count of linear/radial gradient elements | `review` | icon | SVG icons with allowed gradient complexity. |
| `svg_stroke_width_range` | Declared stroke-width min/max | `review` | icon | Line weight consistency for vector icons. |
| `svg_path_geometry` | Path bounds, length, segment type counts | `review` | icon | Structural limits on vector complexity and path types. |

---

## Game trace (`game analyze`)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `position_difference` | Max/mean Euclidean step between consecutive positions | `game analyze` | game, motion | Teleport detection and step size vs declared animation sample rate. |
| `velocity_magnitude` | Speed from position deltas / Δt | `game analyze` | game, motion | Walk/run caps; binds to `max_velocity` and render motion oracle. |
| `acceleration_magnitude` | Acceleration from velocity midpoints | `game analyze` | game, motion | Snappy vs floaty motion; needs ≥3 position samples. |
| `jerk_magnitude` | Jerk from acceleration segments | `game analyze` | game, motion | Harsh direction changes; needs sufficient valid acceleration. |
| `rotation_distance` | Quaternion rotation change (step or loop) | `game analyze` | game, motion | Spin speed and loop continuity on rotation tracks. |
| `loop_boundary_difference` | Position distance first vs last sample on loop | `game analyze` | game, motion | Cycle seams for walk/idle loops in engine space. |
| `pose_boundary_distance` | Flattened pose vector distance at loop | `game analyze` | game, skeletal_animation | Skeletal clip loop closure without foot slide check alone. |
| `bone_length_deviation` | Bone length vs rest pose | `game analyze` | game, skeletal_animation | Stretching rigs or bad retarget on exported pose tracks. |
| `foot_sliding_distance` | Foot motion during contact windows | `game analyze` | game, skeletal_animation | Ground contact quality for humanoid locomotion traces. |
| `event_timing_difference` | \|observed − expected\| event time | `game analyze` | game, runtime | Hit frames, ability spawn, and sync to design spreadsheet. |
| `anchor_distance` | Distance between paired anchor tracks | `game analyze` | game, vfx | VFX attach points (weapon, socket) staying within tolerance. |
| `particle_lifetime` | Particle track lifetime duration | `game analyze` | game, vfx | Effect duration vs design (explosion, trail). |
| `particle_emitter_bounds` | Particle positions inside declared AABB | `game analyze` | game, vfx | Spawns not drifting outside allowed world/UI box. |
| `alpha_weighted_occlusion` | Alpha-weighted overlap of back layers under front | `game analyze` | game, sprite, vfx | 2D stack order and unintended overlap in trace frame layers. |

---

## Runtime evidence (`runtime-check`)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `runtime_callback_count` | Observed engine callback invocation count | `runtime-check` | game_runtime | Proof that gameplay hooks fired (fixture or live capture). |
| `runtime_callback_timing` | Callback time vs expected ± tolerance | `runtime-check` | game_runtime | Same as trace events but from live engine callbacks. |
| `runtime_particle_state` | Particle emitter state at sample time | `runtime-check` | game_runtime | Emitter on/off and parameters at a scripted sample point. |
| `runtime_particle_bounds` | Live particles inside AABB at sample | `runtime-check` | game_runtime | Runtime VFX containment vs trace-only bounds. |
| `runtime_particle_alive_count` | Live particle count min/max at sample | `runtime-check` | game_runtime | Burst counts and pooling behavior under load. |

---

## Render evidence (`render-check`)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `render_capture_count` | Number of captured PNG frames | `render-check` | game_render | Enough frames for delta, events, and flash analysis. |
| `render_changed_pixel_ratio` | Fraction of pixels changing between adjacent captures | `render-check` | game_render | Idle vs excessive flicker; complements trace motion. |
| `render_event_frame_alignment` | Event timestamp within tolerance; neighbor frame window | `render-check` | game_render | Attack flash, hit stop, and UI pop on correct frame index. |
| `render_flash_metrics` | Luminance-delta area events, rate, duration, optional red area | `render-check` | game_render | Photosensitivity and seizure-risk style guards on real pixels. |
| `render_roi_oracle` | Cropped region vs reference PNG (hash or changed-pixel ratio) | `render-check` | game_render | HUD, character slot, or stable UI region vs golden PNG. |
| `render_trace_motion_bound` | Max luminance-centroid step vs trace max velocity × scale | `render-check` + `--trace-report` | game_render | On-screen motion consistent with exported kinematics. |

---

## Sprite sheet CLI

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `sprite_baseline_y_variance` | Variance of bottom opaque row per frame | `sprite-sheet check` | sprite, sprite_sheet | Feet/baseline bobble across walk cycle strips. |
| `sprite_bbox_height_variance` | Variance of alpha bbox height per frame | `sprite-sheet check` | sprite, sprite_sheet | Vertical scale consistency without ML frame scoring. |
| `sprite_inter_frame_palette_subset` | Each frame opaque RGB ⊆ frame 0 palette | `sprite-sheet check` | sprite, sprite_sheet | Recolor drift and export accidents across animation. |
| `sprite_inter_frame_changed_pixel_ratio` | Max RGBA delta ratio between adjacent frames | `sprite-sheet check` | sprite, sprite_sheet | Frozen frames or huge pops between keys. |
| `sprite_reference_frame_changed_pixel_ratio` | Delta vs chosen reference frame index | `sprite-sheet check` | sprite, sprite_sheet | Hold pose vs extremes (e.g. idle vs attack windup). |
| `sprite_loop_changed_pixel_ratio` | RGBA changed-pixel ratio first vs last frame | `sprite-sheet check` | sprite_sheet | Loop closure proxy for PNG strips without engine playback. |
| `sprite_foot_metrics` | Ground line, feet pivot, bbox, COM per frame | `sprite-sheet check` | sprite_sheet | Pivot/ground-line QA; collider generation is a separate step. |
| `sprite_cell_empty_forbidden` | Any grid cell with zero opaque pixels | `sprite-sheet check` | sprite_sheet | Missing animation frames in a declared atlas grid. |
| `sprite_cell_duplicate_forbidden` | Identical full RGBA payloads across cells | `sprite-sheet check` | sprite_sheet | Accidental duplicate cels in a sheet. |
| `sprite_cell_min_inner_border` | Opaque pixels too close to the cell edge | `sprite-sheet check` | sprite_sheet | Padding / bleed room inside each cell. |
| `sprite_cell_near_empty` | Occupied pixel count below `min_occupied_pixels` | `sprite-sheet check` | sprite_sheet | Nearly blank cels and export truncation. |
| `sprite_margin_gap_contamination` | Opaque pixels in outer margins or inter-cell gaps | `sprite-sheet check` | sprite_sheet | Atlas gutters and sheet padding stay clear. |
| `sprite_sheet_file_limits` | File bytes, pixel count, cell count, encoded PNG bit depth at load | `sprite-sheet check` | sprite_sheet | Guard oversized or unexpected PNG inputs. |
| `sprite_sheet_bbox_height_spread` | Relative spread of max frame bbox height across sheets | `sprite-sheet compare` | sprite_sheet | Same character scale across atlases (Ludo sprite compare–style). |
| `sprite_sheet_ppu_spread` | Relative spread of bbox÷reference_height_m (PPU) | `sprite-sheet compare` | sprite_sheet | World-scale consistency when sheets share `reference_height_m`. |

---

## Project asset completeness

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `project_required_paths` | Each listed relative path exists as a file | `project check-assets`, `project preview --asset-policy` | project_assets | Folder completeness before review or export. |
| `project_required_globs` | Each glob matches ≥1 file under project_root | `project check-assets`, `project preview --asset-policy` | project_assets | “At least one texture per category” style policies. |

---

## Lighting CLI

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `lighting_luma_plane_fit` | Linear luminance plane R² on selection | `lighting check` | lighting | Decide if direction check is meaningful (flat vs noisy). |
| `lighting_declared_direction_alignment` | Angle error vs `light_direction_xy` | `lighting check` | lighting | Art bible light direction on stills or key frames. |
| `lighting_chromatic_shading_direction_cosine` | Min pairwise R/G/B plane direction cosine | `lighting check` | lighting | Shading moves coherently across channels (simple intrinsic-style check). |
| `lighting_cross_frame_direction_variance` | Variance of fitted direction across sheet frames | `lighting check` | lighting | Lighting stable across animation when using `sheet_layout`. |

**Note:** `i-mage-not-ai compare` reports a **diagnostic-only** lighting plane cosine between foreground and context; that is not a separate registry ID—it supports review, not policy PASS/FAIL by default.

---

## Advisory (non-gating)

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `advisory_ai_generated_likelihood` | External whole-image synthetic probability | `advisory detect`, `inspect --advisory-backend`, `scan --advisory-backend` | advisory | Extra signal only; never gates manifest review. Requires optional `aidetector` or `aidetect` on PATH. |

See [advisory-provenance.md](advisory-provenance.md).

---

## Character anatomy and learned similarity

| ID | 측정 내용 | CLI / 진입점 | 팩 | 왜 / 언제 쓰는지 |
| --- | --- | --- | --- | --- |
| `openpose_bone_ratio` | Segment length / scale pair vs policy range | `character anatomy` | character_anatomy | Humanoid proportion limits from saved OpenPose JSON (not live pose estimation). |
| `openpose_joint_angle` | Joint angle vs policy range | `character anatomy` | character_anatomy | Elbow/knee pose bands for specific animation frames. |
| `lpips_similarity` | Learned perceptual distance (aligned same size) | `similarity` | character_similarity | Optional reference match when explicit threshold and local weights are approved. |
| `dinov2_cosine_similarity` | CLS embedding cosine similarity | `similarity` | character_similarity | Optional global similarity diagnostic; poor for tiny local defects. |

---

## Maintenance

When adding an algorithm to `algorithms.yaml`:

1. Register version, adapter, and capabilities.
2. Add to one or more packs in `packs.yaml` if it should appear in `plan` for that asset class.
3. Add a row to this catalog and, if relevant, to [algorithm-literature-map.md](algorithm-literature-map.md).
4. For manifest-visible rules, add a `RULES` entry in `core.py` when the check is part of default rule planning.

Generated registry count: **70** algorithms (schema_version 1 in `algorithms.yaml`).
