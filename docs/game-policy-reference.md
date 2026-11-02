# Game policy key reference

Policies are plain JSON objects. Unknown top-level keys are rejected. Use `null` on trace `game_policy` limits to request a measurement without inventing a pass/fail threshold (except `expected_event_times` and `particle_bounds`, which must be objects when present).

## Trace policy (`game_policy` / `game analyze --policy`)

Used by `validate_policy` and `analyze_trace`.

| Key | Type | Meaning |
| --- | --- | --- |
| `max_position_step` | number ≥ 0 | Max Euclidean step between consecutive world-space position samples |
| `max_velocity` | number ≥ 0 | Max velocity magnitude between samples |
| `max_acceleration` | number ≥ 0 | Max acceleration magnitude |
| `max_jerk` | number ≥ 0 | Max jerk magnitude |
| `max_loop_boundary_difference` | number ≥ 0 | Position distance between first and last sample on a loop |
| `max_pose_loop_boundary_distance` | number ≥ 0 | Flattened pose vector distance at loop boundary |
| `max_rotation_step_degrees` | number 0–360 | Max rotation change between consecutive rotation samples |
| `max_rotation_loop_difference_degrees` | number 0–360 | Rotation distance at loop boundary |
| `expected_event_times` | object | Map event ID → expected time (seconds) |
| `max_event_timing_error` | number ≥ 0 | Max abs(observed − expected) event time |
| `max_particle_lifetime` | number ≥ 0 | Max particle lifetime duration |
| `max_bone_length_deviation` | number ≥ 0 | Max bone length deviation from rest |
| `max_foot_sliding_distance` | number ≥ 0 | Max foot sliding during contacts |
| `max_anchor_distance` | number ≥ 0 | Max distance between declared anchor tracks |
| `particle_bounds` | object | `{min, max, units, coordinate_system}` emitter AABB limits |
| `max_alpha_occlusion_ratio` | number 0–1 | Max alpha-weighted occlusion ratio in frame layers |

## Runtime policy (`runtime-policy.json` / `game runtime-check --policy`)

Used by `analyze_runtime_evidence`. Top level may only contain `callbacks` and/or `particles`; at least one must be non-empty.

### `callbacks` (map name → rule)

| Field | Type | Meaning |
| --- | --- | --- |
| `count` | int ≥ 0 | Expected invocation count |
| `time` | number ≥ 0 | Expected time (seconds) when count is 1 |
| `tolerance` | number ≥ 0 | Max abs timing error per invocation |

### `particles` (map emitter → rule)

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `sample_time` | number ≥ 0 | yes | Target sample time (seconds) |
| `time_tolerance` | number ≥ 0 | yes | Max abs(sample_time − target) |
| `bounds` | `[min_x, min_y, max_x, max_y]` | yes | Expected AABB containment |
| `min_alive_count` | int ≥ 0 | no | Minimum live particles at sample |
| `max_alive_count` | int ≥ 0 | no | Maximum live particles at sample |

Runtime evidence bundles use `format: i_mage_not_ai.runtime-evidence/1`, `timebase: seconds`, and integer `random_seed`. Optional top-level `provenance` or `evidence_run_id` is copied into runtime reports for gate binding.

## Render policy (`render-policy.json` / `game render-check --policy`)

Used by `validate_render_policy` and `analyze_render_evidence`.

| Key | Type | Meaning |
| --- | --- | --- |
| `min_capture_count` | int ≥ 2 | Minimum number of captured frames |
| `max_changed_pixel_ratio` | number 0–1 | Max fraction of pixels changing between adjacent frames |
| `pixel_delta_threshold` | int 1–255 | Per-channel delta counted as “changed” (default 1) |
| `event_times` | object | Map event ID → `{time, tolerance, before_frames?, after_frames?}` |
| `flash` | object | Luminance/area flash limits (`min_luminance_delta`, `min_area_ratio`, plus optional caps) |
| `roi_oracles` | object | Map oracle id → `{frame_index, region, reference, match_mode?, max_changed_pixel_ratio?}` — crop vs reference PNG |
| `trace_motion_bound` | object | `{pixels_per_engine_unit, margin?, centroid_luma_threshold?, max_render_motion_px?}` — requires `--trace-report` on `game render-check` |

Render evidence bundles require the keys documented in `docs/game-engine-export.md`. Optional `provenance` is validated but not required.

Sprite atlas and lighting policies (non-tower): [sprite-lighting-policy.md](sprite-lighting-policy.md).

## Gate binding

`i-mage-not-ai game gate` aggregates three **reports** (`asset_type`: `game_trace`, `runtime_evidence`, `render_evidence`), each PASS/COMPLETE with the same `scenario_id`. Pass `--require-evidence-run-id` to require the same non-empty `evidence_run_id` on all three (set on bundles via `evidence_run_id` or `provenance.evidence_run_id`, or on reports directly).

Preflight fixture exports (no engine run): `i-mage-not-ai doctor --repo-root . --game-fixture` (Godot includes render bundle validation and a three-report gate dry-run with `--require-evidence-run-id`).

JSON Schema: trace/export (`game-trace.schema.json`), bundles (`runtime-evidence.schema.json`, `render-evidence.schema.json`), policies (`game-policy.schema.json`, `runtime-policy.schema.json`, `render-policy.schema.json`), reports (`game-evidence-report.schema.json`), gate (`game-gate.schema.json`).

Runtime/render towers use **`game_runtime`** / **`game_render`** rule packs in `rules/packs.yaml`; they are **not** selected through manifest `features[]` today. See [game-three-tower-architecture.md](game-three-tower-architecture.md).

Gate optional flags: `--require-event-bridge`, `--event-bridge`, `--require-input-digests`, `--input-binding`, `--require-state-join`, `--require-evidence-run-id`.

Provenance may record `renderer`, `platform_composition` (`engine_viewport`, `desktop_compositor`, `mobile_os_unknown`, `unknown`), `capture_adapter_sha256`, and `cross_gpu_reproducible` (default expectation: false unless verified).
