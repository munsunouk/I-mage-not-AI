# Synthetic flat icon benchmark, v0.2.0

This dataset contains 20 deterministic 32x32 flat icon pairs (40 PNG files): one clean source and one fault-injected variant per case. Every faulty image has exactly one generated target defect, alternating between an extra visible palette color (`COLOR-001`) and insufficient transparent margin (`GEOMETRY-002`). `dataset.json` labels the injected fault and records source SHA-256 hashes for both variants.

## Run the detector benchmark

From the repository root in the project Python environment:

```powershell
.venv\Scripts\python.exe -m i-mage-not-ai benchmark generate-synthetic --output-dir benchmarks\datasets\icon --count 20
.venv\Scripts\python.exe benchmarks\run_icon_dataset.py --dataset benchmarks\datasets\icon --output benchmarks\results\icon-v0.2.0 --repeat 3
```

The runner invokes the CLI on both images in every pair. The clean controls are named `<case-id>-clean`; the faulty image keeps the labeled case ID. It scores all finding outputs against the generator's injected-fault labels, retains one review report and exact input/manifest per image, and writes aggregate `score.json` plus run timing metadata.

This is a public synthetic smoke benchmark with transparent, generated labels. It measures only the two defined deterministic constraints. It is not real-world evidence, not a hidden test set, and not an Agent Only vs Agent + CLI experiment.
