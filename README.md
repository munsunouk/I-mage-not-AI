# I-mage-not-AI

**AI generates the image. We verify the constraints.**

A planned **deterministic image and game-asset linter** for AI coding agents such as Codex and Cursor.

I-mage-not-AI is designed to inspect generated visual assets, break them into meaningful features through an agent, and evaluate those features using explicit mathematical and algorithmic rules—not an opaque aesthetic score.

> **Project status: early design / pre-release.** The CLI, package, Agent Skill, benchmark, and website described below are **planned**, not available to install or use yet. Commands in this README illustrate the proposed interface.

## Why build this?

AI-generated icons, characters, backgrounds, sprites, and effects can violate concrete project constraints: a flat icon contains unwanted color variation, a sprite's pivot shifts between frames, an animation loop jumps, or a weapon effect appears away from its attachment point.

A generic "looks good" score cannot reliably explain these failures. I-mage-not-AI aims to answer a more useful question:

**Which declared constraint failed, where did it fail, how was it measured, and can a fix be verified?**

## How it works

```text
Codex / Cursor
    │
    ├── Generated asset(s)
    └── Agent-produced feature manifest + intended constraints
                  │
                  ▼
        Manifest & provenance validation
                  │
                  ▼
       Preview, rules & capability plan
                  │
                  ▼
     Source adapters + feature adapters
                  │
                  ▼
       Canonical measurement evidence
                  │
                  ▼
       Deterministic algorithm engine
                  │
                  ▼
     Policy evaluation + coverage checks
                  │
                  ▼
     Findings: PASS / FAIL / INCONCLUSIVE
                  │
                  ▼
     Agent fixes the asset → full re-check
```

**Agent interprets. CLI measures. Rules decide. Agent repairs.**

The agent can identify candidate features and their intended roles. The CLI must independently calculate measurements from the source assets. An agent's interpretation of a region is **not** itself mathematically proven; unverified or missing prerequisites must be reported explicitly.

## Planned capabilities

| Asset | Checks under consideration | Evidence needed |
| --- | --- | --- |
| Flat icons | Palette limits, uniform color regions, margins, alignment, alpha bounds | PNG/SVG, masks, project constraints |
| Characters | Declared palette consistency, silhouettes, shape preservation | Image(s), masks, reference constraints |
| Backgrounds | Solid-region rules, seamless tile boundaries, repeated patterns | Images, regions, tiling intent |
| Sprite animations | Frame dimensions, pivot drift, loop boundaries | Sprite sheets, frame metadata, anchors |
| Rigged animation | Bone lengths, pose continuity, contact-point drift | Rig and motion tracks |
| VFX | Effect anchors, event timing, particle lifetime, coverage | Effect tracks, events, engine traces |

A rule is only a hard pass/fail check when its prerequisites and acceptance criterion are explicitly defined. For example, frequency analysis can measure repetitive texture, but cannot prove a texture is aesthetically bad.

## Proposed CLI experience

The following commands are **design targets, not working instructions today**.

After a future package release:

```bash
# Proposed installation (not yet published)
uv tool install i-mage-not-ai

# Planned commands
imreview init
imreview doctor
imreview inspect assets/icon.png
imreview manifest validate .imreview/icon.json
imreview delegate preview --manifest .imreview/icon.json
imreview delegate rules --manifest .imreview/icon.json
imreview plan --manifest .imreview/icon.json
imreview review --manifest .imreview/icon.json --format json
```

`imreview init` is intended to install a common Agent Skill into the current project. The CLI itself will remain independent of any specific editor or model provider.

## Example rule and finding

Illustrative policy (the schema and parameters are subject to implementation):

```yaml
id: ICON-SOLID-001
match:
  asset_type: icon
  feature_role: background
requires:
  - valid_mask
  - declared_solid_color_policy
algorithm: masked_color_uniformity
assertion:
  metric: max_delta_e00
  operator: less_than_or_equal
  value: 2.0
```

Illustrative result — **not a real benchmark measurement**:

```json
{
  "rule_id": "ICON-SOLID-001",
  "feature_id": "background",
  "status": "FAIL",
  "measurement": {"metric": "max_delta_e00", "value": 8.4},
  "constraint": {"operator": "less_than_or_equal", "value": 2.0},
  "evidence": {"region": "masks/background.png"}
}
```

The policy must come from a user requirement or project configuration. It must **not** be silently invented by an agent. These values are only examples.

## Principles

- **Deterministic core:** No LLM or trained aesthetic classifier inside the validation engine.
- **Feature-aware checks:** Select measurements by asset type, feature, intent, and available evidence.
- **Explainable findings:** Return rule IDs, measured values, thresholds, provenance, and locations.
- **No silent passes:** Missing required evidence yields `INCONCLUSIVE` or incomplete coverage, never a passing verdict.
- **Safe correction loop:** Preserve originals, restrict allowed changes, and re-run previous checks.
- **Portable integrations:** Keep source adapters, feature adapters, rules, and algorithms independently extensible.
- **Offline-first goal:** Source assets should not need to be uploaded to a third-party API for CLI evaluation.

### What “deterministic” means here

The **evaluation stage** should produce reproducible results for the same inputs, manifest, rules, algorithm versions, and defined runtime environment. This does **not** imply that an agent's feature segmentation is infallible, that all CPU/GPU platforms produce identical floating-point bits, or that aesthetic quality can be proven mathematically.

## Benchmarking (planned)

We intend to publish a reproducible benchmark comparing:

1. **Original:** the first generated asset.
2. **Agent only:** correction by the coding agent without I-mage-not-AI.
3. **Agent + I-mage-not-AI:** the same agent using the CLI's findings.

Results will be separated into three tracks:

| Track | Purpose | Official aggregate? |
| --- | --- | --- |
| **Official** | Versioned datasets with independently checked ground truth | Yes, after verification |
| **Community** | Voluntary before/after examples and user-reported runs | No; shown separately |
| **Contributions** | New test cases, failure reports, and rule proposals | Only in a future dataset release after review |

Planned metrics include precision/recall for independently labeled violations, fix success rate, regression rate, coverage, preservation outside permitted regions, and execution time. We will not mix unrelated dataset versions or treat submitted self-reported scores as verified results.

A future `imreview benchmark submit` workflow may package results and open a pull request. Submitted evidence would be schema-checked and independently re-evaluated before appearing on an official leaderboard. **No benchmark scores or leaderboard are available yet.**

## Roadmap

- [ ] **Phase 0 — Foundations:** Package, CLI, manifest schema, preview, rule resolver, capability planner, structured reports.
- [ ] **Phase 1 — Flat icon MVP:** PNG feature masks, color/geometry validators, coverage gate, regression checker, Codex/Cursor Skill.
- [ ] **Phase 2 — More image types:** SVG, character, and background rule packs.
- [ ] **Phase 3 — Game assets:** Sprite-sheet, motion, VFX, and engine-trace adapters.
- [ ] **Phase 4 — Community benchmark:** Datasets, reproducible submissions, validated leaderboard, and before/after gallery.
- [ ] **Phase 5 — Distribution:** PyPI package, optional standalone binaries, GitHub Pages documentation.

## Contributing

The project is at the architecture stage. Feedback on deterministic validation rules, synthetic fixtures with known ground truth, adapter contracts, and measurable failure cases is especially valuable.

Use [GitHub Issues](https://github.com/munsunouk/I-mage-not-AI/issues) for proposals and bug reports. Please distinguish a reproducible rule violation from a subjective design preference. Contribution guidelines will be added as the codebase is established.

## Inspiration and acknowledgments

The workflow architecture draws inspiration from [Alibaba OpenCodeReview](https://github.com/alibaba/open-code-review), particularly its separation of agent work from deterministic orchestration, review previews, rule selection, and coverage tracking. I-mage-not-AI is an independent project and is not affiliated with Alibaba.

## License

**Not yet selected.** A public GitHub repository without a license does not automatically grant open-source reuse rights. A license file will be added before the first distributable release.

---

**Repository:** https://github.com/munsunouk/I-mage-not-AI