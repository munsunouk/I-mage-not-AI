# Benchmarks

- **Synthetic flat-icon leaderboard** (`i-mage-not-ai benchmark …`): deterministic 32×32 palette/margin faults with editable-region verification.
- **Icon multimetric v1** (`prepare_multimetric_icon_dataset.py`, `score_multimetric_ab.py`): controlled renderer icons. Dataset version **1.0.3** stores clean-derived `policy_thresholds` (no fault-label leakage) and scores output repairs with masks regenerated from each submitted RGBA.
- **Icon multimetric v2** (`prepare_multimetric_icon_dataset_v2.py`, `score_multimetric_ab_v2.py`): label-blind generated icons with alpha-key silhouettes only; prefer this for new agent A/B runs.

Regenerate v1 dataset metadata after changing thresholds:

```sh
python benchmarks/prepare_multimetric_icon_dataset.py
```
