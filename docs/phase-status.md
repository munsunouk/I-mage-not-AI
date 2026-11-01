# Architecture v0.5 phase completion record

This record maps the repository to the four phases in the v0.5 specification. “Complete” means the phase's in-scope deliverables exist and have local evidence; it does not mean every possible engine project or runtime behavior is supported.

## Phase 0 — Core foundation: complete

- Installable `i-mage-not-ai` entry point and `python -m i_mage_not_ai` are provided by `pyproject.toml` and `i_mage_not_ai/__main__.py`.
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
- The bounded read-only Godot/Unity project preview finds project markers, supported image assets, and statically visible references/settings, and can draft a policy-free manifest for an explicitly selected image. These are not complete native project parsers. Separate opt-in runtime fixtures now observe an actual callback and live particle state in each engine; they do not establish arbitrary project behavior without an instrumented adapter and explicit runtime scenario.
- A separate explicit engine CLI export command now supports selected Godot scenes and Unity `.anim` clips. It requires an engine executable and `--allow-project-code`; selected project/editor code may run. Integration evidence covers keyed transforms and event metadata for the checked-in fixtures.
- `i-mage-not-ai game runtime-check` evaluates versioned runtime observations with explicit callback count/time and particle bounds/count thresholds. Godot Forward+ and Unity Play Mode fixture runs both produced PASS/COMPLETE evidence with fixed seeds and fixture timing.

## Phase 4 — Ecosystem: complete for the agreed Godot + Unity scope

- Plugin API v1 supports explicit host-side trust and registration; the standard CLI keeps plugin import/execution disabled.
- User project YAML rules can match features and select only registered algorithms, requirements, and explicit assertions.
- Godot is the initial engine exporter; Unity supplies additional engine support for this phase.
- Raster hot paths for CIEDE2000, connected components, occupancy, luminance, gradient diagnostics, and mask intersection use array operations. A reproducible benchmark is available at `benchmarks/benchmark_review.py`.
- Benchmark evidence: generated 1024×1024 RGBA checkerboard and full mask, 3 runs, median 2.767 s, 8/8 checks PASS, COMPLETE. The pre-optimization run recorded 20.453 s on the same fixture shape, about 7.4× slower. Machine timings vary; compare on the same host.

## Local verification

- `.venv\Scripts\python.exe -m pytest -q`: **57 passed**.
- `.venv\Scripts\ruff.exe check i_mage_not_ai tests benchmarks`: **passed**.
- `.venv\Scripts\mypy.exe i_mage_not_ai tests benchmarks`: **passed** (19 source files).
- `.venv\Scripts\python.exe benchmarks\benchmark_review.py 1024 3`: **PASS/COMPLETE**, 8 required checks.
- Godot and Unity headless/batch integration commands: **passed** as recorded above.
- Godot 4.6.3 Forward+ runtime scene: two consecutive runs produced the same callback time and GPU particle bounds; runtime policy PASS/COMPLETE.
- Unity 6000.3.25f1 Play Mode: two runs observed the same `AnimationEvent` time, 8 live particles, and local XZ bounds at a fixed-delta sample; runtime policy PASS/COMPLETE.
- The checker targets Python 3.12 because the installed NumPy 2.5 stubs use PEP 695 syntax; runtime tests still target Python 3.11.

## Deliberate limits

- Discovery is bounded by file/depth limits, skips generated/dependency directories and symlinks, and only parses a limited set of text references. It can miss assets hidden behind unsupported formats or references assembled dynamically. Review the preview coverage and exclusions before relying on its inventory.
- No plugin execution in the CLI, model-based aesthetic scoring, or automatic image repair is included. Runtime execution is a separate explicit engine CLI operation and can run project code.
- Runtime callback and particle checks are proven only for the instrumented fixtures. Arbitrary projects require a project adapter that records actual callback invocation and samples the engine's available particle state. Godot GPU particle sampling requires a working renderer; captured GPU bounds do not expose per-particle counts. These checks do not infer visual meaning or guarantee identical rendered pixels across drivers.
