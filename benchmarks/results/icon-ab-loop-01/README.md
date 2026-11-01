# Icon Agent Only vs Agent + CLI: single loop

**Dataset:** `imreview-synthetic-flat-icons` v0.2.0, 20 fault-injected 32x32 icons  
**Evaluation:** `VERIFIED_SYNTHETIC`; comparison label: `SINGLE_LOOP_EXPLORATORY`  
**Shared protocol:** same Codex session, same declared prompt hash, one repair attempt

| Track | Fix success | Regression rate | Preservation | Changed pixels | Outside allowed region |
|---|---:|---:|---:|---:|---:|
| Agent Only (visual rule selection) | 100% (20/20) | 0% (0/20) | 100% | 970 | 0 |
| Agent + CLI (CLI rule selection) | 100% (20/20) | 0% (0/20) | 100% | 970 | 0 |
| CLI delta vs Agent Only | 0 pp | 0 pp | 0 pp | 0 | 0 |

The benchmark evaluator re-measured every repaired output. Both tracks used the same deterministic pixel repair operations after their respective rule selection: replace the isolated palette outlier with the dominant color, or clear pixels at the canvas edges until the 10% transparent-margin constraint passes. These measurements cover only the generated palette and margin faults.

## Interpretation and limits

This is one exploratory in-session loop, not a blinded causal study. The Agent Only visual pass occurred after this session had already run the CLI smoke benchmark and seen the dataset behavior. It therefore cannot establish that CLI access caused an improvement. Both tracks tied on every measured repair metric. No independent model trials, token/cost measurements, or agent reasoning-time measurements were captured. The synthetic generator and labels are public, so this is not real-world performance evidence.

The per-case evidence is in `cli-reports/`, the submitted assets and protocol are in `submission.json`, and the mechanically rechecked three-track output is `verified-result.json`. Open `gallery/index.html` for the Original / Agent Only / Agent + CLI images.

Reproduce with:

```powershell
.venv\Scripts\python.exe benchmarks\run_icon_ab_loop.py
```
