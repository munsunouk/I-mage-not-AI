# External validity and metric comparison audit

Reviewed on 2026-10-31 (Asia/Seoul). Scope: current source, multimetric icon loop04 results, project skill contract, and primary scientific literature. No source code was edited and no new agent A/B run was conducted. A read-only pixel calculation was used for the transparent-image counterexample below.

## Judgment

The current CLI has a defensible role as a deterministic checker of explicit design constraints. The current evaluation does not establish a universal 100/100 image-generation or icon-quality evaluator. Mathematical correctness of a color or geometry calculation, usefulness of a threshold, validity of a synthetic benchmark, and agreement with actual users are separate claims.

No scientifically calibrated overall grade can be calculated from the current evidence. A weighted scorecard would be an auditor-defined rubric, requiring explicit weights; it would not be a probability that the evaluation is correct. This audit therefore uses evidence statuses.

The declared scope is appropriately narrow: the skill says the CLI does not infer semantics or taste, and validates mask files and dimensions rather than their semantic labels. See `E:/I-mage-not-AI/.agents/skills/i-mage-not-ai/SKILL.md:13`, `:36`, and `:38`. That is a strength when results are described as declared-constraint compliance. It becomes a construct-validity gap if those results are presented as overall visual quality or absence of AI slop.

## Constructs covered by the metrics

| Construct | Current CLI / loop04 | External comparison | Audit status |
|---|---|---|---|
| Explicit alpha, margin, color, component, reflection, overlap constraints | Registered calculations with explicit policies; known procedural masks | Fine-grained, task-specific decomposition is consistent with GenEval and VBench design philosophy | Present; independent numerical correctness belongs to the mathematical audit |
| Whether the image contains the intended object and relations | Human or agent supplies feature interpretation; CLI does not validate meaning | GenEval checks objects/count/color/position; TIFA checks prompt-derived questions | Unmeasured by this loop |
| Aesthetic preference and perceived visual coherence | No human ratings or independent preference labels | Pick-a-Pic/PickScore and ImageReward use human comparison labels | Unvalidated |
| Icon meaning, recognizability, confusion with similar icons | Not scored | Icon usability research measures interpretation and search performance | Unmeasured |
| Small-size performance at the product's display size | 128x128 synthetic source only | Requires recognition/confusion/response-time tasks at the actual display conditions | Unmeasured |
| Pixel-perfect recovery of a known clean source | Full-canvas RGBA exact match and exact-reconstruction count | Reference-based fidelity measures answer a narrower question than preference | Present, scoped to this synthetic recovery task |
| Preservation outside the approved repair area | loop04 compares output with clean, but does not score an allowed-edit mask | Skill step 10 requires explicit allowed mask/region and verification | Missing in loop04 score |
| Actual submitted output symmetry and feature overlap | Clean feature masks reused by output rechecks | A useful output metric must depend on the submitted output geometry | Invalid as an independent output-geometry verification |
| Video temporal consistency, motion, physics and commonsense | Not exercised by this icon run | VBench and VBench-2.0 evaluate separate temporal and semantic capabilities | Out of scope |
| General generation distribution/diversity | Four procedural designs, repeated across six faults | FID/CMMD are image-set distribution metrics | Not established; adding FID to 24 icons would not resolve the gaps |

Generic pretrained learned scores also need validation in this domain. PickScore, ImageReward, LPIPS, object detectors, or VQA models are not automatically calibrated for pixel art, abstract icons, tiny displays, or project-specific art direction. Treat them as comparison signals until their errors and human agreement are measured on representative icons.

## Concrete counterexamples and code evidence

### Full-canvas pixel agreement is not a visual-quality percentage

`E:/I-mage-not-AI/benchmarks/score_multimetric_ab.py:101`-`:109` calculates equality of every RGBA tuple with uniform weight:

`pixel_match = matching_RGBA_pixels / (128 * 128)`.

A fully transparent `(0,0,0,0)` image receives exact-pixel agreement of **61.54% to 68.10%, mean 64.6942%**, against the 24 clean references. This was calculated from the current PNGs, without modifying them. The icon is absent, but its transparent background matches. Thus the reported 96.06% mean pixel agreement cannot be interpreted as 96 points of semantic, aesthetic, or usable icon quality. Perfect full-image equality remains a legitimate strict gate for this known-source synthetic reconstruction task.

Report foreground-union and feature-specific errors separately, retain full-image exact reconstruction, and add an outside-allowed-edit preservation measure. These answer different questions and should not be merged with unexplained weights.

### Output geometry rechecks reuse target geometry

`score_multimetric_ab.py:162` regenerates the clean icon and masks. Line 164 passes clean masks as the output feature masks. Lines 169-175 replace only the silhouette with a mask derived from output alpha. Reflection IoU and feature-overlap rechecks therefore see the clean feature geometry rather than independently recovered output gems. A PASS is not evidence that the submitted output actually has the intended pair geometry. This is stated as a limitation in the report, but it still prevents treating the count of all output checks passed as complete output verification.

### The public policy depends on the hidden defect label

`E:/I-mage-not-AI/benchmarks/prepare_multimetric_icon_dataset.py:167`-`:169` uses `case['fault']`: center cases get `clean_offset + 0.01`, others `clean_offset + 0.2`; symmetry cases get `0.98`, others `0.0`. These policies help isolate fixture categories, but are not independent evidence for a general blind defect detector. Use an intent-defined policy fixed before choosing the faulty examples; then assess natural and injected errors against that same policy.

### Reconstruction improvement does not enforce edit preservation

`score_multimetric_ab.py:152`-`:158` compares input and output distances to clean. Lines 200-208 report reconstruction and improvement metrics, without an allowed-edit mask. This can show progress toward this single reference while failing to identify damage outside the permitted repair region. The project's skill explicitly asks for `verify` with an allowed mask or region at line 53. The presence of preservation checks elsewhere in the repository does not make them part of loop04.

## Primary literature and narrow implications

1. **GenEval (2023)** — [paper](https://arxiv.org/abs/2310.11513). An object-focused evaluation of object co-occurrence, count, color, and position, evaluated against human judgments. It motivates explicitly testing prompt meaning rather than treating mask measurements as semantic correctness.
2. **TIFA, ICCV 2023** — [paper](https://openaccess.thecvf.com/content/ICCV2023/papers/Hu_TIFA_Accurate_and_Interpretable_Text-to-Image_Faithfulness_Evaluation_with_Question_Answering_ICCV_2023_paper.pdf). Uses prompt-derived question-answer pairs and VQA to evaluate fine-grained text-image faithfulness, with human-correlation experiments. It does not make a VQA model an error-free judge.
3. **Pick-a-Pic / PickScore (2023)** — [paper](https://arxiv.org/abs/2305.01569). Learns and evaluates a preference predictor using human comparisons of generated images. Its lesson is to obtain independent preference labels; the model itself is not universal aesthetic ground truth.
4. **ImageReward (2023)** — [paper](https://arxiv.org/abs/2304.05977). Uses expert image comparisons to learn a preference reward model. Its validation is empirical agreement with people, not mathematical derivation of an absolute beauty scale.
5. **Rethinking FID, CVPR 2024** — [paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Jayasumana_Rethinking_FID_Towards_a_Better_Evaluation_Metric_for_Image_Generation_CVPR_2024_paper.pdf). Demonstrates failures of FID including human disagreement and sample-count sensitivity, and proposes CMMD. A widely used metric is still subject to validation; distribution scores are not per-icon semantic or repair judgments.
6. **VBench, CVPR 2024** — [paper](https://openaccess.thecvf.com/content/CVPR2024/html/Huang_VBench_Comprehensive_Benchmark_Suite_for_Video_Generative_Models_CVPR_2024_paper.html). Uses 16 evaluation dimensions and human-preference annotations for the dimensions. More calculations alone are not equivalent to more validated constructs.
7. **VBench-2.0 (2025)** — [paper](https://arxiv.org/abs/2503.21755). Expands video evaluation to human fidelity, controllability, creativity, physics, and commonsense. Static color/geometry compliance does not establish these capabilities.
8. **LPIPS, CVPR 2018** — [paper](https://arxiv.org/abs/1801.03924). Evaluates feature-based perceptual similarity using human judgments. It supports measuring perceptual difference separately from pixel equality; its original validation does not automatically cover tiny pixel-art icons.
9. **McDougall et al. (2000), icon usability** — [paper abstract and DOI](https://pubmed.ncbi.nlm.nih.gov/11218339/). Studies how concreteness, complexity, and distinctiveness affect interpretation and search performance. Recognition and confusion tasks are relevant external criteria for usable icons. Product display sizes must be selected from actual use conditions, not attributed to this paper as universal thresholds.
10. **T2IScoreScore / TS2, NeurIPS 2024** — [paper](https://arxiv.org/abs/2404.04251), [primary project](https://t2iscorescore.github.io/). Evaluates text-to-image faithfulness metrics using semantic error graphs. It tests ordering with a Spearman-derived meta-metric and separation of adjacent error populations with two-sample Kolmogorov-Smirnov statistics. The dataset distinguishes synthetic errors, natural images, and natural model errors. Its experiments also show that complicated VLM-based metrics do not necessarily outperform simpler embedding metrics on challenging nearby examples.

## How TS2 can inform an icon metric audit

TS2's original task is prompt-faithfulness meta-evaluation. Our proposed application to deterministic icon color, placement, shape, and usability checks is an **adaptation**, not an existing validation result from TS2.

For each icon/intent pair, create a blinded series with known per-axis error severity: for example center displacement, unwanted color area, component damage, or omitted required objects. Freeze the intent policy before generating or selecting examples. Include both controlled alterations and real failures from independent image generators. Test whether each proposed metric orders severity correctly, distinguishes neighboring severities, and remains stable under irrelevant transformations. Report the synthetic and real-error partitions separately.

For color and geometry, severity must be defined through the declared design constraints or independent human/task labels. Do not simply define severity as the exact same metric being audited; that would only verify implementation consistency. The KS statistic indicates separation, not whether the direction or semantic meaning is correct. Pair it with ordering and independent labels.

## Evidence gates for a defensible evaluation

| Gate | Current external-audit status | Required evidence |
|---|---|---|
| Explicit narrow measurement contract | Present | Continue reporting PASS only for declared checks and masks |
| Independent semantic/policy ground truth | Compromised in current fixture | Policies and labels fixed independently of observed outputs and defect category |
| Output-sensitive geometry evaluation | Failed for reused clean feature masks | Output-derived or independently annotated feature geometry with annotation quality checks |
| Human criterion validity | Unmeasured | Blind pairwise decisions or axis-specific ratings, rater agreement, pairwise accuracy and rank correlation with confidence intervals |
| Icon task usefulness | Unmeasured | Recognition accuracy, confusion matrices, and response times at actual product sizes/backgrounds |
| Perceptual fidelity beyond raw pixels | Unmeasured | Representative icon perceptual judgments; compare candidate distances rather than assume pretrained scores are valid |
| Unintended-edit preservation | Missing in loop04 | Outside-allowed-mask RGBA changes and semantic feature damage |
| Real-generation generalization | Unmeasured | Held-out real icons, multiple generators/styles/resolutions, natural multi-defect cases |
| Robustness | Unmeasured in this external review | Mask boundary errors, resampling, anti-aliasing, alpha/color-space perturbations with known expected behavior |
| Repeated-trial statistical support | Not established by one loop | Independent repeated runs, paired uncertainty, full failures and run metadata |

If a 100-point rubric is adopted, publish the weights and status-to-points mapping before the next run. Describe it as a project audit rubric, while reporting empirical success rates and uncertainty separately. A perfect score on one synthetic diagnostic set is insufficient to satisfy the missing gates.
