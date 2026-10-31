# Project inspection and code review tool boundaries

Reviewed 2026-10-30 against the projects' current GitHub documentation. This repository keeps deterministic image verification, source-project inventory, engine export, and code review as separate responsibilities.

## OpenCodeReview

[OpenCodeReview](https://github.com/alibaba/open-code-review) is a CLI for reviewing source code. Its documented modes review Git diffs (`ocr review`) or scan selected files/repositories (`ocr scan --path ...`); it selects files and applies configured rules, with an LLM agent producing code review comments. That can help a maintainer review changes to `i_mage_not_ai` itself, including the discovery and exporter implementation. It does not measure image constraints or produce Godot/Unity animation traces.

Recommendation: keep it an optional maintainer review tool. Ruff, mypy, pytest, manifest checks, and engine fixture exports remain reproducible project gates. An LLM code review may add findings, but must not replace those gates or decide an image-quality PASS. The documented CLI requires Git for repository operations, and model configuration is needed for full agent review; delegation mode is an alternative when a host agent performs the review.

## REA

[REA](https://github.com/morluto/rea) is an MCP/CLI toolkit for reverse engineering software and packaged binaries. Its current documentation lists static Godot PCK inventory/extraction and Unity IL2CPP metadata decoding, alongside other binary and application analyzers. Those capabilities can answer questions about a built game package when source projects are unavailable. They do not replace source-project asset references, editor animation curves, or pixel-based constraint checks. REA also has runtime/decompiler integrations that depend on platform and installed analysis tools; treat any such analysis as a separate, explicit operation on a trusted artifact.

Recommendation: do not add REA as a mandatory runtime dependency for this CLI. If packaged-build inspection becomes a requirement, add a separate optional adapter that accepts an explicit PCK/IL2CPP artifact and records the tool version, input hash, findings, and limitations. Never silently invoke REA during project discovery or let reverse-engineered claims count as measured image evidence.

## Implemented workflow in this repository

- `i-mage-not-ai project preview` performs bounded, read-only Godot/Unity source discovery.
- `i-mage-not-ai project manifest` creates a draft for an explicitly selected image; semantic labels and thresholds still need review.
- `i-mage-not-ai project export-trace` invokes an explicit engine CLI exporter for a selected scene/clip and requires `--allow-project-code`.
- The normal image/game-trace CLI remains deterministic and has no OCR, REA, model, MCP, or network dependency.

This split uses the engine's own CLI for source project evidence and reserves OCR/REA for optional code-review and packaged-binary investigation tasks.
