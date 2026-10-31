# Complex synthetic icon dataset v1.0.1

Twenty 128x128 RGBA fantasy inventory icons were cropped from `source-sheet.png`,
centered on transparent canvases, and given one deterministic defect each.
Ten add a conspicuous isolated palette color; ten shift the intact icon toward
one canvas edge. The per-case requirements set an exact visible RGB palette cap
and a minimum transparent margin ratio of 0.12 on every edge.

`prepare_complex_icon_dataset.py` records the source hash and per-asset hashes.
All 20 generated inputs were preflighted with the local `i-mage-not-ai review`
CLI: the injected rule failed and the other rule passed for every case.
Dataset labels remain evaluator-side during blind runs.
