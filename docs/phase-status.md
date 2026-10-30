# Architecture v0.5 phase completion record

This record maps the repository to the four phases in the v0.5 specification. “Complete” means the phase's in-scope deliverables exist and have local evidence; it does not mean every possible engine project or runtime behavior is supported.

## Phase 0 — Core foundation: complete

- Installable `imreview` entry point and `python -m imreview` are provided by `pyproject.toml` and `imreview/__main__.py`.
- Typed manifest validation, path containment, hashes, image ingestion, rule registry, adapter capability planning, JSON/Markdown output, and coverage gating are implemented.
- `inspect`, `manifest validate`, `delegate preview`, `delegate rules`, `plan`, `review`, `coverage`, `explain`, and `verify` are exposed by the CLI.
- The checked-in Codex/Cursor Skill documents the preview → plan → review → repair → regression workflow.
- Evidence: local CLI help; full pytest and Ruff runs recorded below.

## Phase 1 — Flat icon end to end: complete

- Raster and mask checks include exact palette, fixed Lab bins, CIEDE2000 uniformity, alpha bounds/margins/centroid, and masked edit regression verification.
- Explicit policy checks are separate from measurements. Missing or uncertain required checks cannot produce a complete PASS.
- JSON Schema, generated-image contract, deterministic metric, CLI, and property-based checks are in `tests/`.
- No automatic image editing or unsupported automatic hook is claimed.

## Phase 2 — Character, background, and SVG: complete

- Character and background measurements include masked palette/luminance, silhouette components, symmetry, occupancy, overlap, tile edges, and FFT periodic energy.
- SVG checks include gradient declarations, explicit stroke widths, and path geometry. A constrained path with unsupported transforms stays inconclusive.
- The available rules and limitations are described in `README.md` and `docs/rule-authoring.md`.

## Phase 3 — Game asset evidence: complete for the trace contract

- The shared trace contract and game rule pack cover transform tracks, derivatives, rotation, pose and loop boundaries, contacts, anchors, events, particle records, and alpha-weighted frame/atlas-region occlusion.
- Godot and Unity editor exporters produce versioned wrappers. Checked-in CLI fixtures exercise keyed position/rotation and one event in each engine.
- Actual local evidence, rerun on 2026-10-30:
  - Godot 4.6.3 headless editor: exit 0, 2 transform tracks and 1 event exported; CLI analysis PASS/COMPLETE.
  - Unity 6000.3.25f1 batch editor: integration marker present; 2 transform tracks and 1 event exported; CLI analysis PASS/COMPLETE. Unity printed a licensing token refresh warning, but the batch export completed successfully.
- This is trace-based integration. The CLI has a bounded read-only Godot/Unity project preview that finds project markers, supported image assets, and statically visible references/settings. It also creates a policy-free manifest draft for an explicitly selected image. These are not complete native project parsers and do not establish extraction of runtime callbacks or simulated particle state from arbitrary projects.
- A separate explicit engine CLI export command now supports selected Godot scenes and Unity `.anim` clips. It requires an engine executable and `--allow-project-code`; selected project/editor code may run. Integration evidence covers keyed transforms and event metadata for the checked-in fixtures.

## Phase 4 — Ecosystem: complete for the agreed Godot + Unity scope

- Plugin API v1 supports explicit host-side trust and registration; the standard CLI keeps plugin import/execution disabled.
- User project YAML rules can match features and select only registered algorithms, requirements, and explicit assertions.
- Godot is the initial engine exporter; Unity supplies additional engine support for this phase.
- Raster hot paths for CIEDE2000, connected components, occupancy, luminance, gradient diagnostics, and mask intersection use array operations. A reproducible benchmark is available at `benchmarks/benchmark_review.py`.
- Benchmark evidence: generated 1024×1024 RGBA checkerboard and full mask, 3 runs, median 2.767 s, 8/8 checks PASS, COMPLETE. The pre-optimization run recorded 20.453 s on the same fixture shape, about 7.4× slower. Machine timings vary; compare on the same host.

## Local verification

- `.venv\Scripts\python.exe -m pytest -q`: **42 passed** (includes discovery and execution-gate cases).
- `.venv\Scripts\ruff.exe check imreview tests benchmarks`: **passed**.
- `mypy imreview tests benchmarks`: **passed** (Python 3.12 target for installed NumPy stubs).
- `.venv\Scripts\python.exe benchmarks\benchmark_review.py 1024 3`: **PASS/COMPLETE**, 8 required checks.
- Godot and Unity headless/batch integration commands: **passed** as recorded above.
- The checker targets Python 3.12 because the installed NumPy 2.5 stubs use PEP 695 syntax; runtime tests still target Python 3.11.

## Deliberate limits

- Discovery is bounded by file/depth limits, skips generated/dependency directories and symlinks, and only parses a limited set of text references. It can miss assets hidden behind unsupported formats or references assembled dynamically. Review the preview coverage and exclusions before relying on its inventory.
- No plugin execution in the CLI, model-based aesthetic scoring, automatic image repair, runtime callback invocation, or live particle simulation extraction is included.
- Game-engine verification is limited by the trace evidence the exporter provides. The current editor fixtures prove keyed transforms and event metadata, not every game rule against live engine simulation.
