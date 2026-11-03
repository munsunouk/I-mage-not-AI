# Advisory AI-generation likelihood (optional)

I-mage-not-AI does **not** treat AI provenance as a manifest review gate. The `advisory` commands optionally call an external detector (for example [lynote-ai/ai-image-detector](https://github.com/lynote-ai/ai-image-detector)) and attach **non-gating** signals to inspect or batch scans.

Install a backend separately, then either:

```sh
pip install git+https://github.com/lynote-ai/ai-image-detector
# or ensure `aidetect` is on PATH
```

## Commands

```sh
i-mage-not-ai advisory detect image.png --backend univfd --csv report.csv
i-mage-not-ai inspect asset.png --advisory-backend ultra --advisory-threshold 0.5
i-mage-not-ai scan images --path ./art --csv inventory.csv [--advisory-backend univfd]
i-mage-not-ai advisory benchmark-folder ./dataset --real-dir nature --fake-dir ai --optimize-metric f1
i-mage-not-ai benchmark calibrate-binary --scores scores.json
i-mage-not-ai project preview --path . --csv images.csv
pip install -e '.[api]'
i-mage-not-ai serve --host 127.0.0.1 --port 8765
```

`benchmark calibrate-binary` expects a JSON array of `{"score": float, "label": 0|1}` (for example exported `probability_ai` values from an advisory benchmark).

## HTTP (optional extra)

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness |
| `POST /inspect` | Upload PNG/JPEG/WebP/SVG; returns `inspect` JSON |
| `POST /advisory/detect` | Upload raster; query `backend`, `threshold`; advisory JSON only |

## Registry

Algorithm id: `advisory_ai_generated_likelihood` (pack: `advisory`). Status values are `ADVISORY` or `INCONCLUSIVE`; they must not override `review` PASS/FAIL.
