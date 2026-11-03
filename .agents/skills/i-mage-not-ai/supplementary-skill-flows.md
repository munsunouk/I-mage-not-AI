# Supplementary flows (route by user need)

Use this file when the user’s goal is **not** the full default path (XAL → manifest → `review --plan`). Pick **one primary path**; combine others only when the user asks for multiple deliverables. None of these replace manifest review unless the user explicitly wants feature-mask QA.

Docs: [sprite-lighting-policy.md](../../../docs/sprite-lighting-policy.md), [project-discovery.md](../../../docs/project-discovery.md), [advisory-provenance.md](../../../docs/advisory-provenance.md), [game-capture-and-gate.md](game-capture-and-gate.md), [optional-extensions.md](optional-extensions.md).

## Decision table

| User need | XAL + manifest required? | Commands | Gates PASS/FAIL? |
| --- | --- | --- | --- |
| “What images are in this repo / project?” | No | `project preview --path …` [`--csv …`] | No (inventory); exit 2 if scan INCOMPLETE |
| “Flat folder inventory + digests” | No | `scan images --path …` [`--csv …`] | No |
| “Required art paths / globs must exist” | No | `project check-assets --path … --policy …` or `project preview --asset-policy …` | Yes for asset policy only |
| “Quick file metadata (size, alpha, SVG paths)” | No | `inspect <file>` [`--advisory-backend …`] | No; advisory never gates |
| “Palette / mask / ΔE on approved features” | **Yes** (steps 1–9 in SKILL.md) | `plan` → `review --plan` | Yes for declared rules |
| “Sprite strip / atlas (baseline, palette, loop, feet)” | No* | `sprite-sheet check --sheet … --policy …` | Yes with JSON policy |
| “Same character scale across sheets (PPU)” | No | `sprite-sheet compare --policy …` | Yes with compare policy |
| “Light direction / shading planes on a still” | No | `lighting check --image … --policy …` | Yes with lighting policy |
| “Optional AI-generation likelihood (extra signal)” | No | `advisory detect …` or `inspect` / `scan` with `--advisory-backend` | **Never** on `review`; ADVISORY / INCONCLUSIVE only |
| “Reference looks like candidate (LPIPS/DINO)” | No | `similarity --metric …` | Only if user sets explicit threshold |
| “OpenPose proportions on a frame” | No | `character anatomy …` | Only with anatomy policy |
| “Game motion / runtime / render evidence” | No | [game-capture-and-gate.md](game-capture-and-gate.md) | Yes on three-tower gate |

\*Sprite checks do not require XAL masks unless the user also wants manifest feature rules on the same asset; do not skip XAL when they asked for both.

## Typical command bundles

**Onboarding a game art folder**

```text
i-mage-not-ai project preview --path <root> --csv inventory.csv
i-mage-not-ai project check-assets --path <root> --policy <asset-policy.json>
```

**Batch technical inventory (any tree, includes SVG)**

```text
i-mage-not-ai scan images --path <root> --csv scan.csv
```

**Sprite pipeline QA (policies from art bible, not invented)**

```text
i-mage-not-ai sprite-sheet check --sheet walk.png --policy walk-policy.json
i-mage-not-ai sprite-sheet compare --policy cast-scale-policy.json
```

**User asked “is this AI?” — advisory only**

Install optional backend separately ([advisory-provenance.md](../../../docs/advisory-provenance.md)), then:

```text
i-mage-not-ai advisory detect <image-or-folder> --backend ultra --csv advisory.csv
```

Report `probability_ai` as **one non-gating signal**. Do not map advisory output to manifest `review` PASS/FAIL. If they need enforceable art rules, use manifest review or sprite/lighting policies instead.

**HTTP upload bridge (optional extra)**

```text
pip install -e '.[api]'
i-mage-not-ai serve --port 8765
```

## Agent rules

1. **Do not** run the full XAL segmentation workflow when the user only requested inventory, advisory, or policy-only sprite/lighting checks.
2. **Do** run XAL + manifest when the user wants per-feature masks, palette on parts, or project `rules.yaml` on features.
3. **Do not** treat `advisory`, `compare` (foreground/context diagnostic), or `measure` as substitutes for missing manifest rules.
4. **Do** state which path was taken and which registered algorithms ran; cite saved JSON paths in the summary.
5. Preflight still applies: `doctor` before long scans; respect `INCOMPLETE` / exit 2 on truncated walks.
