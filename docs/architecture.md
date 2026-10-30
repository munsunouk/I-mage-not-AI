# Architecture v0.5 implementation status

Core contract: **Agent interprets → CLI verifies → Agent repairs.** The CLI contains no ML inference, aesthetic scores, network access, or image editing. The implemented Phase 1 covers raster/SVG ingestion, a versioned feature manifest, deterministic rule resolution, a capability plan, measurements, explicit policy checks, report coverage, and edit regression checks.

## Runtime flow

1. Manifest loading validates the typed Pydantic contract and schema version, required fields, unique feature IDs, parent and overlap references, local paths, asset hash, and configured size limits.
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

## Extension points and deferred work

Source adapters now extract normalized raster/SVG metadata, feature adapters decode masks, and a JSON game-trace adapter validates exported temporal evidence without running engine code. The `game` rule pack measures motion derivatives, quaternion rotation, pose/loop boundaries, bone length, contact sliding, anchor alignment, event timing, particle lifetime/bounds, and alpha-weighted occlusion from PNG layers or atlas regions. Local positions compose through synchronized parent tracks with per-sample 2D/3D basis matrices. Trace values declare timebase, timestamps/frame indices, coordinate system, units, interpolation, and optional random seed. Native engine project exporters remain future work. The documented plugin API is opt-in for embedding hosts; the CLI never discovers or imports plugins. See [Game asset roadmap](game-asset-roadmap.md).
