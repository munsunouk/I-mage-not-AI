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
```

Review supports `--format json|markdown`. PASS requires complete planned-rule coverage and passing required checks. Missing measurements, semantic ambiguity, unsupported capabilities, or unresolved checks cannot become PASS. Exit codes: 0 for PASS/complete, 1 for FAIL or incomplete review, 2 for invalid input.

Project YAML policies are applied with `--rules-file` on `delegate rules`, `plan`, and `review`. They define match conditions, priority, algorithm parameters, capability requirements, and explicit assertions. Equal-priority contradictory rules are rejected.

## Current measurement packs

Icon rules include exact or fixed Lab-bin palette count, alpha bounds/margins, centroid, solid-color masks with CIEDE2000, SVG gradients/strokes, and SVG Path geometry. Character rules include masked palette and luminance levels, silhouette components, symmetry, and pairwise mask overlap. Background rules include occupancy, tile-edge difference, FFT periodic-energy ratio, and a fitted RGB-plane diagnostic. All enforced thresholds must come from explicit manifest or project policy.

SVG Path inspection parses line, Bézier, and elliptical arc segments and reports bounds, length, and types. Path-local transforms are not applied; constrained transformed Paths are inconclusive. External SVG references and scripts are rejected.

Raster `max_path` metrics are not supported. Raster gradient-fit R² is diagnostic only and stays INCONCLUSIVE. Palette counting defaults to exact RGB tuples; optional fixed Lab bins are deterministic and do not use clustering. Canonical JSON game traces support position/velocity/acceleration/jerk, quaternion rotation, pose and loop boundaries, bone length, contact foot sliding, anchor distance, event timing, particle lifetime/bounds, and alpha-weighted occlusion across PNG layers or atlas regions. Use `imreview game analyze` or the standard manifest `plan`/`review` flow. Local positions compose through synchronized parents with per-sample basis matrices. Native Godot/Unity project parsing, plugin execution, and automatic repair remain deferred.

## Manifest and agent workflow

See [manifest schema](schemas/feature-manifest.schema.json), [game trace schema](schemas/game-trace.schema.json), [engine export contract](docs/game-engine-export.md), [plugin API](docs/plugin-api.md), [architecture](docs/architecture.md), [rule authoring](docs/rule-authoring.md), [game roadmap](docs/game-asset-roadmap.md), and [Codex/Cursor Skill](.agents/skills/image-review/SKILL.md). Masks are validated for file, path containment, and dimensions, not semantic correctness. The agent must record provenance and never invent measured values.

## Tests

```sh
python -m unittest discover -s tests -v
```
