# Sprite sheet and lighting policies (deterministic)

These checks do **not** use learned metrics (no LPIPS/DINO/FLIP). They complement manifest raster rules and the game three-tower pipeline.

For how these fit among papers and other methods, see [algorithm-literature-map.md](algorithm-literature-map.md).

## Sprite sheet (`i-mage-not-ai sprite-sheet check`)

Policy JSON (`sprite-sheet-policy.schema.json`). Required frame geometry plus at least one check.

| Key | Meaning |
| --- | --- |
| `layout` | `horizontal_strip` (default) or `grid` |
| `frame_width`, `frame_height` | Frame size in pixels |
| `columns` | Required for `grid` |
| `frame_count` | Optional cap on frames read |
| `margin_left`, `margin_top`, `margin_right`, `margin_bottom` | Outer padding (default 0); gaps must stay transparent |
| `gap_x`, `gap_y` | Spacing between cells (default 0) |
| `forbid_empty_cells` | FAIL when a cell has no opaque pixels at `alpha_threshold` |
| `forbid_duplicate_cells` | FAIL when two cells have identical RGBA payloads |
| `min_transparent_inner_border_px` | Minimum distance from opaque pixels to the cell edge |
| `min_occupied_pixels` | FAIL when occupied pixel count is below this (near-empty / empty) |
| `include_cell_metadata` | Emit per-cell bbox, coverage, and `rgba_sha256` on the report (default true) |
| `max_file_bytes`, `max_pixel_count`, `max_cell_count` | Optional PNG/WebP size limits at load |
| `required_bit_depth` | When set to `8`, reject unsupported image modes before convert |
| `max_baseline_y_variance` | Variance of bottom opaque row per frame |
| `max_bbox_height_variance` | Variance of alpha bbox height |
| `require_palette_subset_of_first_frame` | Each frame’s opaque RGB set ⊆ frame 0 |
| `max_inter_frame_changed_pixel_ratio` | Adjacent-frame RGBA delta ratio (like render delta) |
| `max_reference_changed_pixel_ratio` | Requires `reference_frame_index` |

## Lighting (`i-mage-not-ai lighting check`)

Policy JSON (`lighting-policy.schema.json`).

| Key | Meaning |
| --- | --- |
| `light_direction_xy` + `max_direction_error_degrees` | Luma plane slope vs declared direction (image x right, y down) |
| `min_channel_direction_cosine` | Min pairwise cosine between R/G/B linear plane directions (chromatic shading) |
| `min_luma_plane_r2` | Minimum plane fit quality on linear luminance |
| `max_cross_frame_direction_variance` | With `sheet_layout` + frame geometry, variance of directions across frames |
| `selection` | `full_frame` or `rect` `[x,y,w,h]` |

## Render extensions (`game render-check`)

Added to `render-policy.schema.json`:

| Key | Meaning |
| --- | --- |
| `roi_oracles` | Map id → `{frame_index, region, reference, match_mode?, max_changed_pixel_ratio?}` — reference PNG path relative to evidence root or policy directory |
| `trace_motion_bound` | `{pixels_per_engine_unit, margin?, centroid_luma_threshold?}` — pass `--trace-report` with the game trace review JSON; compares max luminance-weighted centroid step to trace `velocity_magnitude` max |

See also [game-policy-reference.md](game-policy-reference.md).
