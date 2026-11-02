# README quality rubric comparison

Scores reflect **each project’s root `README.md` only** (not product capability or runtime behavior). Scale **1–10**. Snapshot **2026-11-02**.

## Axes

| # | Axis | What we look for |
|---|------|------------------|
| 1 | Purpose / value | Clear “what is this?” above the fold |
| 2 | Explanation | Audience, concepts, readable prose |
| 3 | Install | Commands, prerequisites, optional extras |
| 4 | Getting started | Minimal path to first success (not a full CLI dump) |
| 5 | Visuals | Screenshots, diagrams, demos (not badges alone) |
| 6 | Structure / TOC | Headings, table of contents, scan order |
| 7 | Examples | Copy-paste commands that match real layouts |
| 8 | Badges / meta | CI, license, version, language links |
| 9 | Limits / scope | Non-goals and honesty in the README |
| 10 | Doc links | README as hub to deeper docs |
| 11 | Contribute / test | Dev install, pytest, contributing pointer |
| 12 | Scannability | Skim-friendly; density vs wall-of-text |

**Overall** = simple mean of the 12 axes.

## Compared projects

Sources: upstream `README.md` on default branch unless noted.

- [I-mage-not-AI](../README.md) (this repo)
- [OpenCodeReview](https://github.com/alibaba/open-code-review)
- [reviewdog](https://github.com/reviewdog/reviewdog)
- [Semgrep](https://github.com/semgrep/semgrep)
- [Ruff](https://github.com/astral-sh/ruff)
- [Danger](https://github.com/danger/danger)
- [SonarQube Community](https://github.com/SonarSource/sonarqube)
- [CodeQL libraries](https://github.com/github/codeql)

## Scores (before README refresh)

| Axis | I-mage-not-AI | OCR | reviewdog | Semgrep | Ruff | Danger | SonarQube | CodeQL |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Purpose | 8 | 9 | 8 | 8 | 9 | 7 | 9 | 5 |
| Explanation | 7 | 9 | 7 | 7 | 7 | 5 | 8 | 4 |
| Install | 5 | 8 | 8 | 7 | 10 | 3 | 4 | 2 |
| Getting started | 3 | 9 | 6 | 8 | 9 | 4 | 3 | 2 |
| Visuals | 1 | 9 | 8 | 7 | 6 | 4 | 7 | 0 |
| Structure / TOC | 5 | 7 | 9 | 6 | 9 | 6 | 8 | 4 |
| Examples | 7 | 8 | 10 | 5 | 9 | 6 | 3 | 1 |
| Badges / meta | 1 | 8 | 7 | 6 | 9 | 7 | 9 | 0 |
| Limits / scope | 9 | 6 | 4 | 8 | 4 | 3 | 7 | 6 |
| Doc links | 8 | 10 | 5 | 9 | 9 | 8 | 9 | 8 |
| Contribute / test | 5 | 7 | 4 | 6 | 7 | 8 | 7 | 5 |
| Scannability | 4 | 8 | 5 | 7 | 8 | 7 | 7 | 5 |
| **Overall** | **5.3** | **8.2** | **6.8** | **7.0** | **8.0** | **5.7** | **6.8** | **3.5** |

## I-mage-not-AI README improvements (this repo)

Priority order applied in [README](../README.md):

1. **Quick start** — `examples/` icon path: validate → plan → review → coverage  
2. **Visuals** — [agent–CLI flow](assets/readme/agent-cli-flow.svg), [exit outcomes](assets/readme/review-exit-outcomes.svg), sample asset thumbnail  
3. **Install** — Python ≥3.11, `[dev]`, optional `[perceptual]`  
4. **Badges** — CI, Python, license  
5. **TOC** — separate **Quick start** from **Command reference**

## Scores (after README refresh — I-mage-not-AI only)

| Axis | Before | After (est.) |
|------|:---:|:---:|
| Purpose | 8 | 8 |
| Explanation | 7 | 7 |
| Install | 5 | 8 |
| Getting started | 3 | 8 |
| Visuals | 1 | 7 |
| Structure / TOC | 5 | 8 |
| Examples | 7 | 8 |
| Badges / meta | 1 | 7 |
| Limits / scope | 9 | 9 |
| Doc links | 8 | 9 |
| Contribute / test | 5 | 7 |
| Scannability | 4 | 8 |
| **Overall** | **5.3** | **7.8** |

Other projects unchanged; re-fetch their READMEs to refresh comparative scores.

## Method notes

- OpenCodeReview and Semgrep READMEs embed multiple PNG/JPG figures; I-mage-not-AI previously had **zero** figures.  
- CodeQL’s root README is a **library repo pointer**, not a product quickstart — low scores are expected.  
- Danger’s README intentionally sends **end users** to [danger.systems](https://danger.systems); the GitHub README targets contributors.
