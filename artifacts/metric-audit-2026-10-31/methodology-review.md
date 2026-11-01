# Benchmark methodology and statistics review — 2026-10-31

Scope: current `icon-multimetric-isolated-loop-04`, dataset v1.0.2, its generator, package preparation, scorer, saved decisions and CLI JSON. This audit did not change benchmark code or outputs. Small calculations inspected existing images, masks and JSON. No calibrated overall score is assigned: the evidence supports validity findings and necessary gates, not an arbitrary weighted number.

## Assessment

This is a useful controlled algorithm regression fixture. It is not yet a validated estimate of general Agent Only versus Agent + CLI image-quality or repair performance. Two confirmed pipeline problems invalidate a stronger interpretation: fault-label-dependent thresholds, and output geometry rechecks using the clean target masks rather than geometry independently obtained from the submitted output.

## Confirmed high-priority findings

### Public policy depends on the hidden fault label

`benchmarks/prepare_multimetric_icon_dataset.py:167-169` reads `case['fault']` and sets the centroid limit to clean offset +0.01 only for center faults, versus +0.2 otherwise. Symmetry limit is 0.98 only for symmetry faults, versus 0.0 otherwise. Thus the declared design policy differs with the intended answer. In addition to leaking label information in public thresholds, this disables meaningful cross-defect testing. A uniform policy per clean design, fixed before defect injection, would be a valid alternative; clean assets can legitimately establish reference policies, but the defect label cannot decide which checks are stringent.

`benchmarks/prepare_multimetric_ab.py:90-96` checks that the CLI failures equal exactly the injected category's expected rules and raises otherwise. This is appropriate for construction of a diagnostic regression fixture. Measuring the same CLI on that selected fixture is consequently not an independent generalization test. It does not show that a random real generated icon will be diagnosed with 100% accuracy. Kapoor and Narayanan's validation arguments require legitimate prediction features and evaluation on the distribution of scientific interest [1].

### Output symmetry and overlap are measured from clean target geometry

`benchmarks/score_multimetric_ab.py:160-175` regenerates clean masks and uses them for the output review. Only the silhouette is replaced by an alpha mask derived from the actual submitted output. Gem-pair and left/right gem masks remain target geometry. Reflection IoU and overlap therefore measure the clean masks irrespective of actual repaired image content.

Concrete saved-data counterexamples, verified by RGBA array equality:

| Sample | Agent Only submitted pixels | Input CLI | Output recheck |
|---|---|---|---|
| sample-02, overlap | Exactly identical to faulty input | OVERLAP=1.0 FAIL | OVERLAP=0.0 PASS |
| sample-09, symmetry | Exactly identical to faulty input | SYMMETRY=0.0 FAIL | SYMMETRY=1.0 PASS |

Output evidence: `benchmarks/results/icon-multimetric-isolated-loop-04/evaluator/repair-reviews-agent-only/sample-09/report.json:242` and `.../sample-02/report.json:355`. Input evidence: `sessions/agent-cli/outputs/cli-reports/sample-02.json` and `sample-09.json`. PNG file byte equality is false because the agent re-encoded the PNG; decoded RGBA pixel equality is true. These examples prove a repair can leave the defect untouched while the corresponding geometry rule changes from FAIL to PASS. The reported 20/24 aggregate output-check passes must not be interpreted as fully validated actual-state repair success.

### Correction: the margin cases did not lose pixels to clipping

The previous result narrative claimed exact recovery was impossible because generated margin defects clipped pixels outside the canvas. That claim is false for these four saved cases.

The generator injects +14px horizontal translation (`prepare_multimetric_icon_dataset.py:218`). Verified alpha bboxes:

| Sample | Clean bbox | Input bbox | Input translated -14px equals clean RGBA |
|---|---|---|---|
| sample-01 | (22,22,107,109) | (36,22,121,109) | Yes |
| sample-06 | (22,22,107,107) | (36,22,121,107) | Yes |
| sample-07 | (26,21,103,108) | (40,21,117,108) | Yes |
| sample-23 | (22,22,107,107) | (36,22,121,107) | Yes |

All four input bboxes remain inside 128x128. A non-destructive Pillow inverse translation reconstructed all clean pixels exactly. The CLI arm's saved decisions state -9px or -5px corrections, satisfying the margin requirement while leaving residual translation. This demonstrates the distinction between reaching a declared tolerance and reproducing the clean source, not an impossible restoration.

## Further validity limitations

### Different diagnosis endpoints for the arms

`score_multimetric_ab.py:118-131` overwrites Agent + CLI's predictions from its `decisions.json` with raw CLI FAIL categories when a complete hash-matched report exists. Agent Only is graded from natural-language evidence. Thus diagnosis F1 compares the tool's raw diagnostic output with the unaided agent's self-reported answer; it is not an identical measurement of both agents' diagnostic interpretation. A CLI arm with wrong or empty decisions could still receive the same diagnostic F1 because the tool report replaces its answer. Use the same fixed structured diagnosis schema and endpoint for both, preserving tool reports as treatment-compliance evidence.

### Free-text scoring is not a robust semantic classifier

`score_multimetric_ab.py:44-48` uses substring membership. The current normalization mapping was adjusted after the saved outputs were available, as recorded in this chat's execution history; it was not demonstrated to be preregistered. The aliases include phrases occurring in Agent Only's particular evidence, such as 'farther outward' and 'magenta pixel'. This can be a transparent exploratory adjudication, but should not be presented as an independently validated fixed scoring rule.

Direct calls to the existing normalization function returned:

| Text | Assigned category |
|---|---|
| No color defect was found. | color |
| There is no overlap. | overlap |
| The gem is absent, not overlapped. | overlap |
| No detached components. | components |

The parser ignores negation. Equating absent details with overlap also conflates absence with a geometric relationship. Agent Only's feature IDs do not identify canonical rule IDs, and they cannot safely be converted by keyword guessing alone. Fixed category outputs or independent blind adjudicators with explicit rubrics are preferable.

### Only four distinct clean images

Counting SHA-256 of the 24 clean PNGs produced four unique hashes. The generator (`prepare_multimetric_icon_dataset.py:206-224`) reuses orb, shield, hex and potion across six faults, with colors also bound to design variant. These are 24 controlled corruptions of four visuals, not 24 independent natural images. Samples share design factors and outputs can be correlated. Conclusions and uncertainty should respect design-level clustering.

### Normal inputs are not evaluated by either agent

Normal controls are run only in the evaluator's CLI preflight (`prepare_multimetric_ab.py:97-119`). Both arms receive 24 faulty inputs. Therefore the agent experiment does not estimate false repairs, specificity, or no-op behavior on valid icons. Observed category precision 100% among four emitted Agent Only diagnoses is not proof that the method avoids false diagnoses on normal images.

### Single execution and incompletely specified budgets

`protocol.json` records one attempt, independent conversation histories and procedural filesystem isolation. It does not provide a pinned model/reasoning version, token/time/tool budgets, repeated independent agent runs, or complete environment/commit manifest. There is no evidence here of actual contamination; there is also no OS-level enforcement that would establish impossible cross-folder access. State the procedural boundary precisely. Independent conversation history does not imply enforced filesystem isolation.

Agent Only's ban on any CLI diagnostic also compares visual-only reasoning against numerical tooling. That is a legitimate treatment if clearly defined, but narrower than unrestricted agent-only versus the project CLI's incremental benefit. A stronger ablation would include a visual-only arm, an unrestricted generic pixel-computation arm, and the project-CLI arm under comparable budgets. Variance across data sampling and other execution choices can materially affect benchmarking conclusions [2].

### Oracle masks bypass the real segmentation stage

Both arms receive exact renderer-authored masks, including semantic feature separation and reference RGB. The benchmark does not estimate errors in feature discovery, missing features, inaccurate masks or human approval. It cannot establish success of the full real-image pipeline.

### Whole-image exact pixels are valid but incomplete

`score_multimetric_ab.py:101-109` measures RGBA tuple equality over all 16,384 pixels including background. This is valid for exact recovery of a known synthetic source. Large translations contribute thousands of mismatches while a detached one-pixel component contributes one, so the aggregate is driven by large-area defects. Report foreground/feature-specific error and preservation outside the allowed repair area alongside total exact-match error. It is not a human visual-quality or preference metric.

## Statistical uncertainty

Computed using SciPy beta quantiles for two-sided 95% Clopper-Pearson intervals, following the exact-binomial method described by NIST [3]. These are illustrative only under independent identically distributed Bernoulli assumptions; the four reused designs and deterministic selection violate the intended independent random-sampling interpretation. They must not be advertised as population-valid intervals for this benchmark.

| Observed success count | 95% exact interval |
|---|---|
| 24/24 | 85.753%–100% |
| Category-specific 4/4 | 39.764%–100% |
| 20/24 output-rule passes | 62.616%–95.265% |
| 11/24 exact reconstructions | 25.553%–67.179% |
| 1/24 exact reconstruction | 0.105%–21.120% |
| 4/24 correct diagnosis | 4.735%–37.384% |

For all-success n=24, lower bound = (0.025)^(1/24) = 0.85753. These intervals concern binary success probabilities, not F1 itself. F1 would require an appropriate resampling or interval method with the actual clustered sampling unit. Observing 100% does not establish the true probability equals 100%, even before considering leakage and selection.

## Strengths and valid present claims

The same seeded shuffled inputs are used for both arms (`prepare_multimetric_ab.py:37-42`), exact source-authored masks and original hashes are retained, the tool's pre-repair reports are stored and validated against input hashes, and actual output PNGs are preserved. A known clean source permits exact reconstruction checks. The report separates diagnosis F1, output-rule pass counts and pixel reconstruction, rather than equating them. Separate conversation histories are an improvement over one agent seeing both methods' diagnostics. These make the set useful as an inspectable controlled regression fixture.

Valid current claims are descriptive: on these saved 24 corrupted inputs, raw CLI failure categories matched injected labels; 11 CLI-arm outputs versus one unaided output exactly matched their known sources. Broader claims require fixing the noted oracle and policy defects, and independently assessing representative data. Benchmark-dependent rankings are a documented concern [4].

## Gates for a defensible evaluation

1. Freeze one clean-design policy before injecting faults; remove all fault-label-dependent thresholds.
2. Freeze scorer, category rubric, main endpoint and budget before running the held-out arms. Use the same diagnosis endpoint for both.
3. Measure output geometry from the submitted output or explicitly verify target-region contents; do not score a target mask's own symmetry/overlap as repaired-state truth.
4. Add normal inputs, combined faults, severity and threshold-boundary sweeps, unseen designs/styles/resolutions and segmentation errors.
5. Repeat independent paired runs, stratify per defect and report clustered uncertainty at the original design/prompt level; preserve model and execution provenance.
6. Add allowed-edit-area preservation, feature-specific reconstruction, semantic design success and blind human preference with independent graders.

These are necessary validity conditions; satisfying them is not an automatic universal 100/100 certification. Criteria and weighting must correspond to a stated use case and be validated against external outcomes.

## Sources

1. Kapoor & Narayanan (2023), Leakage and the reproducibility crisis in machine-learning-based science, Patterns. https://doi.org/10.1016/j.patter.2023.100804 — legitimate prediction features, clean separation and evaluation on the distribution of interest.
2. Bouthillier et al. (2021), Accounting for Variance in Machine Learning Benchmarks, MLSys. https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html — multiple variation sources and repeated comparisons.
3. NIST, Exact Binomial Confidence Limits. https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm — inversion of exact binomial tails; https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.2119.pdf — instrument performance confidence intervals and bounds.
4. Dehghani et al. (2021), The Benchmark Lottery. https://arxiv.org/abs/2107.07002 — sensitivity of comparative rankings to benchmark task choices. This source supports a methodological warning, not a claim that our observed pixel differences are false.
