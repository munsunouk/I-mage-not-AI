# I-mage-not-AI (`imreview`)

A local deterministic CLI for checking explicit image design constraints. The Agent interprets intent and labels features; the CLI measures image and SVG data, resolves declared rules, plans capabilities, evaluates policies, and reports coverage. It contains no LLM, ML scoring, network calls, or automatic image editing.

The CLI is implemented with Typer; typed manifest and evidence contracts use Pydantic v2. YAML packs declare algorithm versions and capabilities.

## Install

```sh
python -m pip install -e .
imreview --help
```

## Workflow

```sh
imreview inspect icon.svg
imreview manifest validate manifest.json
imreview delegate preview --manifest manifest.json
imreview delegate rules --manifest manifest.json
imreview delegate rules --manifest manifest.json --rules-file project-rules.yaml
imreview plan --manifest manifest.json
imreview review --manifest manifest.json --output review.json
imreview coverage --report review.json
imreview explain review.json
imreview verify --before original.png --after edited.png --report review.json
imreview benchmark score --ground-truth benchmark/ground-truth.json --predictions predictions.json --output benchmark-score.json
imreview benchmark generate-synthetic --output-dir benchmark/synthetic --count 20
imreview benchmark init-submission --dataset benchmark/synthetic/dataset.json --output benchmark/submission.json
imreview benchmark evaluate --dataset benchmark/synthetic/dataset.json --submission benchmark/submission.json --output benchmark/result.json
imreview benchmark leaderboard-add --result benchmark/result.json --leaderboard benchmark/leaderboard.json --run-id run-001
imreview benchmark gallery --dataset benchmark/synthetic/dataset.json --submission benchmark/submission.json --result benchmark/result.json --output benchmark/gallery/index.html
```

Review supports `--format json|markdown`. PASS requires complete planned-rule coverage and passing required checks. Missing measurements, semantic ambiguity, unsupported capabilities, or unresolved checks cannot become PASS. Exit codes follow the architecture contract: 0 PASS/complete, 1 explicit FAIL, 2 INCOMPLETE/INCONCLUSIVE, 3 invalid input or policy, and 4 internal execution error. `python -m imreview` runs the same CLI as the installed `imreview` command.

Project YAML policies are applied with `--rules-file` on `delegate rules`, `plan`, and `review`. They define match conditions, priority, algorithm parameters, capability requirements, and explicit assertions. Equal-priority contradictory rules are rejected.

## Current measurement packs

Icon rules include exact or fixed Lab-bin palette count, alpha bounds/margins, centroid, solid-color masks with CIEDE2000, SVG gradients/strokes, and SVG Path geometry. Character rules include masked palette and luminance levels, silhouette components, symmetry, and pairwise mask overlap. Background rules include occupancy, tile-edge difference, FFT periodic-energy ratio, and a fitted RGB-plane diagnostic. All enforced thresholds must come from explicit manifest or project policy.

SVG Path inspection parses line, Bézier, and elliptical arc segments and reports bounds, length, and types. Path-local transforms are not applied; constrained transformed Paths are inconclusive. External SVG references and scripts are rejected.

Raster `max_path` metrics are not supported. Raster gradient-fit R² is diagnostic only and stays INCONCLUSIVE. Palette counting defaults to exact RGB tuples; optional fixed Lab bins are deterministic and do not use clustering. Canonical JSON game traces support position/velocity/acceleration/jerk, quaternion rotation, pose and loop boundaries, bone length, contact foot sliding, anchor distance, event timing, particle lifetime/bounds, and alpha-weighted occlusion across PNG layers or atlas regions. Use `imreview game analyze` or the standard manifest `plan`/`review` flow. Local positions compose through synchronized parents with per-sample basis matrices. `imreview project preview` performs bounded, read-only Godot/Unity project discovery and reports image references and skipped paths. `imreview project manifest` creates a hash-pinned draft without inferred features or thresholds. Separate `project export-trace` commands explicitly invoke an engine exporter and require `--allow-project-code`; selected scenes/editor integrations can run project code. The CLI still does not load plugins or edit assets automatically.

For the project discovery and engine CLI workflow, see [project discovery](docs/project-discovery.md), the [engine export contract](docs/game-engine-export.md), and the [OpenCodeReview/REA tool boundaries](docs/project-analysis-tooling.md).

## Manifest and agent workflow

See [manifest schema](schemas/feature-manifest.schema.json), [game trace schema](schemas/game-trace.schema.json), [engine export contract](docs/game-engine-export.md), [plugin API](docs/plugin-api.md), [architecture](docs/architecture.md), [rule authoring](docs/rule-authoring.md), [game roadmap](docs/game-asset-roadmap.md), and [Codex/Cursor Skill](.agents/skills/image-review/SKILL.md). Version 0.5 manifests require the source asset SHA-256; legacy 0.1 manifests remain accepted. Masks are validated for file, path containment, and dimensions, not semantic correctness. The agent must record provenance and never invent measured values.

Phase 0–4 scope and verification evidence are listed in [phase status](docs/phase-status.md). Reproduce the raster performance measurement with `python benchmarks/benchmark_review.py 1024 3`.

## Labeled benchmark scoring

`imreview benchmark score` compares rule-level findings with a versioned ground-truth JSON file. Ground truth has `schema_version: "1"`, `dataset_id`, `dataset_version`, and a `findings` array of `{case_id, rule_id}` violations. The predictions file contains a `findings` array with `{case_id, rule_id, status}` records; only `FAIL` counts as a predicted violation. Duplicate finding identities are invalid. The report includes TP/FP/FN, precision, recall, and F1. Undefined metrics are `null` when their denominator is zero. Scores are scoped to one dataset version and do not establish image quality or benchmark validity by themselves.

`generate-synthetic` writes deterministic 32×32 flat icon pairs, alternating between an injected extra-color fault and an insufficient-transparent-margin fault. Each case has a ground-truth rule label and explicit editable pixel region(s). `init-submission` creates a skeleton for the three tracks (`original`, `agent_only`, `agent_plus_tool`), including every case ID. Fill each agent track's `assets` map with PNG paths relative to the submission file, then record `agent`, `model`, `prompt_version`, and `environment` metadata. The protocol also requires a shared prompt SHA-256, attempt limit, environment image, and seed. Evaluation rejects mismatched declared model, prompt, or environment metadata. The original track uses the generated faulty assets. `evaluate` rechecks source SHA-256 hashes and independently measures each output's palette count, normalized alpha margins, and per-pixel changes outside editable regions. It calculates detection metrics, repair success, and preservation from those measurements. Only `VERIFIED_SYNTHETIC` reports can be added to a local leaderboard, which is separated by dataset version and ranked by tool-assisted F1, repair success, then preservation. This leaderboard covers synthetic icon palette and margin faults only; it does not verify real-world benchmark claims or prove that two agent runs were operationally identical.

`gallery` re-runs the image validation before writing a static local HTML comparison. It shows original, agent-only, and tool-assisted images alongside track-level precision, recall, F1, repair success, and preservation. Keep the HTML file with access to the relative image files referenced by the submission and dataset; this is a local report, not a published website.

## Tests

```sh
python -m pytest -q
```

For the development checks, install `python -m pip install -e ".[dev]"`. GitHub-hosted Actions runners run Ruff, mypy, and the unit, schema-contract, and property-based suite on Linux, Windows, and macOS. Runtime tests target Python 3.11; mypy targets Python 3.12 to parse the installed NumPy type stubs.
