# Multimetric icon A/B benchmark — v1.0.2

> **Audit correction — 2026-10-31:** The table below preserves the original descriptive results. Fault-dependent public thresholds and clean feature-mask reuse invalidate interpreting diagnosis F1 as a blind generalization estimate or `all_output_cli_checks_pass` as complete repair success. See the [evaluation audit](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/audit.md) and [reproduced evidence](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/audit-evidence.json). Exact-source pixel comparisons remain descriptive measurements for these four procedural base icons.

## Dataset and preflight

This controlled synthetic set has 24 faulty icons and 24 matched clean controls, four fault cases each for center offset, alpha margin, masked color/ΔE00, silhouette components, symmetry, and feature overlap. Each task package includes source-authored binary masks for the silhouette and gem features. These are exact procedural masks, not model-generated or hand-traced annotations.

Before the blind run, all 24 faulty inputs produced complete CLI reports and failed only their intended defect groups; all 24 clean controls passed every declared check. The reports exercised 12 algorithms: alpha centroid and bbox/margins; global and masked exact palette; masked Lab palette, channel range and CIEDE2000 ΔE00; region occupancy; silhouette bounds and 8-connected components; horizontal reflection IoU; and feature overlap ratio.

## Blind A/B result

Both arms received the same randomized inputs, masks, manifests, and task limits in separate fresh Codex sessions with no shared conversation history. Agent Only could inspect and edit images but could not run the CLI. Agent + CLI produced one complete JSON diagnostic report per image before editing. One repair attempt was allowed per image.

| Measure (24 faulty icons) | Agent Only | Agent + CLI |
|---|---:|---:|
| Correct injected-fault category | 4/24 (16.7%) | 24/24 (100%) |
| Fault-category precision / recall / F1 | 100% / 16.7% / 28.6% | 100% / 100% / 100% |
| Output exactly matches clean source | 1/24 (4.2%) | 11/24 (45.8%) |
| All declared CLI output checks pass | 4/24 (16.7%) | 20/24 (83.3%) |
| Cases closer to clean source than input | 4/24 | 24/24 |
| Cases unchanged / worse than input | 20 / 0 | 0 / 0 |
| Mean pixels differing from clean source (16,384 px) | 1,335 (8.15%) | 646 (3.94%) |

Agent Only categories were normalized from its written visual evidence because it emitted mask feature IDs rather than registered defect rule IDs. Its four diagnoses were the two missing-gem overlap cases, one displaced-gem symmetry case, and one off-color gem case. It did not identify center, margin, or detached-component defects in this trial. Precision is 100% among its four emitted diagnoses; recall is low because it left 20/24 inputs undiagnosed.

Agent + CLI's 100% F1 records the six injected categories on a preflight-selected fixture set whose policy thresholds depend on the hidden fault labels. It is not an unbiased blind estimate of general diagnostic quality. Only 11/24 outputs exactly match the clean source, and pixel error decreased in all 24 cases. The previous explanation that the margin inputs lost clipped pixels was incorrect: every shifted icon remains inside the canvas, and translating each margin input by exactly -14 px reproduces its clean source pixel-for-pixel. The submitted -9/-5 px repairs satisfied the margin limit but left residual translation. Several gem-pair repairs also improved the known pixel error without reproducing every clean-source pixel. The 20 output reports with all checks passing cannot establish complete geometry repair: symmetry and overlap use clean target masks, and an unchanged faulty output can therefore pass those checks. These failures are demonstrated in the audit.

## Interpretation and limits

The CLI metrics helped identify and localize these declared faults, and the CLI-guided arm repaired more of the known pixel errors in this single controlled run. This is not evidence that the CLI can judge icon meaning, aesthetics, or "AI slop"; those qualities were not operationalized or scored. The result is one trial on procedurally generated icons, with known clean sources. A larger human-rated dataset and repeated independent runs would be needed to claim general visual-quality gains. Session history was isolated, while filesystem isolation was procedural rather than OS-enforced.

## Artifacts

- [A/B comparison JSON](comparison.json)
- [Six-category visual comparison](comparison-contact-sheet.png)
- [Randomized inputs and task specifications](sessions/)
- [Faulty-input CLI preflight reports](evaluator/preflight-cli/)
- [Clean-control CLI reports](evaluator/preflight-clean/)
- [Hidden mapping and clean references](evaluator/ground-truth-map.json)
- [Protocol metadata](protocol.json)

