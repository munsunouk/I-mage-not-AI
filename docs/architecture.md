# Architecture v0.5 implementation status

Core contract: **Agent interprets → CLI verifies → Agent repairs.** The CLI contains no ML inference, aesthetic scores, network access, or image editing. The Phase 0–4 implementation status and local verification evidence are tracked in [phase status](phase-status.md).

## Runtime flow

1. Manifest loading validates the typed Pydantic contract and schema version, requires the source SHA-256 in v0.5, checks unique feature IDs, parent and overlap references, local paths, supported format, and configured size limits. Legacy v0.1 manifests remain accepted without the new hash requirement.
2. The resolver turns declared constraints into required checks. It does not invent quality thresholds.
3. The planner resolves algorithm capability requirements from the packaged YAML registry and describes source and feature adapter IDs, requested measurements, and available capabilities before execution.
4. Adapters read raster pixels, masks, or SVG structure and normalize measurement inputs.
5. Algorithms produce metrics and evidence. They do not decide what quality threshold to use.
6. Policies compare metrics with explicitly declared constraints. Missing or semantically uncertain evidence stays inconclusive.
7. Coverage records every planned rule as completed or missing. PASS requires complete coverage and all required checks passing.

## Implemented adapter and algorithm surface

Raster: metadata/hash, alpha bounds and centroid, margins, exact/quantized-ready color counts, mask uniformity and palette, connected components, symmetry, occupancy, luminance bands, periodic FFT power, tile edge difference, and RGB-plane gradient-fit diagnostic.

SVG: safe structural parsing, gradient declarations, element counts, explicit stroke widths, and Path bounds/length/segment types for lines, Béziers, and elliptical arcs. Path-local transforms are not applied and cause constrained checks to be inconclusive.

The agent skill owns semantic feature labeling and repair. Masks are checked for file, dimensions, and path containment; pixel shape alone cannot prove their semantic label.

## Game engine evidence and extension points

Source adapters extract normalized raster/SVG metadata, feature adapters decode masks, and the JSON game-trace adapter validates temporal evidence without running engine code. The `game` rule pack measures motion derivatives, quaternion rotation, pose/loop boundaries, bone length, contact sliding, anchor alignment, event timing, particle lifetime/bounds, and alpha-weighted occlusion from PNG layers or atlas regions. Local positions compose through synchronized parents with per-sample 2D/3D basis matrices. Traces declare timebase, timestamps/frame indices, coordinate system, units, interpolation, and optional random seed. A bounded read-only project discovery command inventories supported Godot/Unity project markers, image files, and a limited set of static references. It does not execute project code and is not a complete native project parser. A separate explicitly opted-in engine CLI exporter can load a selected scene or clip, which may execute project/editor code. Plugin execution stays disabled in the CLI. See [project discovery](project-discovery.md), [Game asset roadmap](game-asset-roadmap.md), and [engine export contract](game-engine-export.md).
