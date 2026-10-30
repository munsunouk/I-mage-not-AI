# Icon benchmark v2: Agent Only vs Agent + CLI

## Result

This is a one-run, controlled conformance pilot on 24 blind inputs: four newly generated icon designs, each tested as normal, center-shifted, margin-shifted, palette-altered, disconnected-component, and compound-defect versions. Both arms received the same randomized sample IDs and the same clean-derived policy limits. The hidden condition map was not included in either task prompt or input package.

| Measure | Agent Only | Agent + CLI |
|---|---:|---:|
| Rule diagnosis micro F1 (40 rule instances) | 0.000 | 1.000 |
| Per-sample macro F1 | 0.167 | 1.000 |
| Exact rule-set match | 4/24 (16.7%) | 24/24 (100%) |
| Normal specificity | 4/4 (100%) | 4/4 (100%) |
| Defect-case detection | 0/20 | 20/20 |
| Clean samples preserved byte-for-byte | 4/4 | 4/4 |
| Faulty samples restored byte-for-byte to clean source | 0/20 | 1/20 (5%) |
| Output passes all supported CLI policy checks | 4/24 (16.7%) | 24/24 (100%) |
| Mean fault silhouette IoU against clean source | 0.816 | 0.923 |

Agent Only returned no diagnoses and left all images unchanged. Its per-sample macro F1 is 16.7% only because the four normal cases were correctly left empty; micro F1 over actual defect-rule instances is 0. Agent + CLI matched all 40 expected rule instances with no false positives and kept all four normal icons unchanged. It restored one of 20 faulty inputs exactly. All its repaired outputs passed the configured supported checks, but passing those thresholds does not mean the original artwork was recovered: exact recovery was only 5%.

The CLI-only reports also matched the independent gold rule set in 24/24 cases. This 100% reflects the benchmark's deliberately injected measurable faults (centroid, margin, palette, connectivity) and the CLI checks designed to detect those quantities. It is a conformance result on this fixed pilot, not evidence that the CLI can judge icon aesthetics, semantic correctness, prompt fidelity, or AI slop.

## Evaluation method

- Diagnosis was read from the same structured `diagnosed_rule_ids` field in both arms. Natural-language parsing was not used, and Agent + CLI decisions were not replaced with raw CLI output.
- The scorer used hidden labels only after both sessions completed. A separate pixel-level audit recomputed alpha-weighted centroid, alpha-bbox margins, distinct visible RGB count, and 8-connected components from the input pixels and clean-derived limits. It did not use CLI statuses to produce gold labels. The 24 labels agreed with the intended injected defects; the separate gold was then compared with CLI reports.
- The scorer regenerated each repaired output's silhouette mask from that output's alpha channel before running the CLI policy checks. It never reused a clean target mask to score a repaired image.
- Diagnosis, clean preservation, exact source recovery, silhouette IoU, and output policy pass rate are reported separately. Full details are in `evaluator/final-score.json`; gold calculations are in `evaluator/independent-ground-truth-audit.json`.

## Scope and limitations

- The generated-art set contains four designs (potion, owl mask, compass, beetle), not 24 independent designs. Six variants per design make the observations clustered; this single run is descriptive and does not establish statistical generalization.
- The generated icons have a deterministic neutral-gray background key and a binary global foreground silhouette. There are no independently reviewed semantic-part masks, so this run did not test masked gem colors, semantic overlap, symmetry, or aesthetic quality.
- Labels and the evaluator folder were withheld from the task prompts, but both sessions ran on a machine where repository files are accessible; isolation was procedural, not OS-enforced. The Agent Only task ran in a fresh projectless session; Agent + CLI ran in a separate fresh project session.
- No independent human aesthetic ratings were collected. Therefore this benchmark says nothing quantitative about perceived quality or AI slop.
- A larger evaluation should use more independently generated designs, multiple blinded runs, and independent human judgments for semantic/aesthetic outcomes.

## Artifacts

- `../../datasets/icon-multimetric-v2/generated-contact-sheet.png`: generated source sheet.
- `../../datasets/icon-multimetric-v2/generated-icons-preview.png`: extracted icon preview.
- `visuals/compound-repair-contact-sheet.png`: clean source, injected compound input, Agent Only output, and Agent + CLI output for each generated design.
- `sessions/agent-only/outputs/`: Agent Only decisions and outputs.
- `sessions/agent-cli/outputs/`: Agent + CLI decisions, reports, and outputs.
- `evaluator/ground-truth-map.json`: scorer-only labels; not part of either task input.
- `evaluator/independent-ground-truth-audit.json`: pixel-level oracle calculations and CLI agreement.
- `evaluator/final-score.json`: per-sample and aggregate metrics.
