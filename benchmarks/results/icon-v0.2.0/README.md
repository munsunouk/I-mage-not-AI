# Icon synthetic detection benchmark, v0.2.0

**Status:** SCORED  
**Dataset:** 20 synthetic icon pairs (40 images: 20 clean controls and 20 fault-injected images)  
**Decisions:** 80 rule decisions across `COLOR-001` and `GEOMETRY-002`  
**Ground truth:** 20 generator-injected defects, 10 per rule

| Metric | Result |
|---|---:|
| TP / FP / FN / TN | 20 / 0 / 0 / 60 |
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |
| Accuracy across 80 rule decisions | 1.000 |
| Median Typer CLI review time per image | 0.01917 s |

Both rules independently scored 10 TP, 0 FP, 0 FN, and 30 TN (precision, recall, and F1 all 1.000). Each image was reviewed three times. The timing is the median of in-process Typer CLI invocations and excludes Python interpreter startup; per-image medians sum to approximately 0.930 s across 40 images.

The result is limited to these deterministic synthetic 32x32 icon constraints. It is not real-world image quality evidence and does not compare Agent Only with Agent + I-mage-not-AI. Detailed machine-readable metrics are in `score.json`; individual inputs, manifests, and review reports are in `reviews/`.

Reproduce from the repository root:

```powershell
.venv\Scripts\python.exe benchmarks\run_icon_dataset.py --dataset benchmarks\datasets\icon --output benchmarks\results\icon-v0.2.0 --repeat 3
```
