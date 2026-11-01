# Manual image review run

These are agent-generated CLI test fixtures, not benchmark corpus entries. The proposed flat-icon constraints are labeled `agent_inference`; they are not user requirements.

## Inputs and results

- `sun-icon.png`: opaque 1254x1254 RGB image. `inspect` recorded SHA-256 `75dba29ede538dd5ab4d245a6822e900db01ec2ce7b8c784666fd521b515c3d9`. Review measured 8,937 exact visible colors (limit 3), zero transparent margin (minimum 8% required), and an inconclusive alpha-centroid check because the image has no alpha channel. Coverage was INCOMPLETE; overall status FAIL.
- `sun-icon-transparent.png`: transparent 1254x1254 RGBA image. `inspect` recorded SHA-256 `3c31378d34f46448b90d7080a426cf1fa7e5723ded277586482d69ea9122afd6`. Review measured 3,927 exact visible colors (limit 2), minimum normalized transparent margin 0.0518 (limit 0.04), and alpha-centroid offset 0.00255 (limit 0.05). Metadata, margin, and centroid passed; palette failed. Coverage was COMPLETE; overall status FAIL.

The palette count uses exact colors, so antialiasing and shading create more entries than the two intended nominal fills. The CLI reports explicit image-rule measurements only; this run does not evaluate aesthetics or prove semantic intent.

## Reproduce

Run from the repository root with the project environment:

```powershell
.venv\Scripts\i-mage-not-ai.exe inspect artifacts\manual-image-review\sun-icon-transparent.png
.venv\Scripts\i-mage-not-ai.exe manifest validate artifacts\manual-image-review\manifest-transparent.json
.venv\Scripts\i-mage-not-ai.exe delegate preview --manifest artifacts\manual-image-review\manifest-transparent.json
.venv\Scripts\i-mage-not-ai.exe delegate rules --manifest artifacts\manual-image-review\manifest-transparent.json
.venv\Scripts\i-mage-not-ai.exe plan --manifest artifacts\manual-image-review\manifest-transparent.json
.venv\Scripts\i-mage-not-ai.exe review --manifest artifacts\manual-image-review\manifest-transparent.json --output artifacts\manual-image-review\review-transparent.json
.venv\Scripts\i-mage-not-ai.exe coverage --report artifacts\manual-image-review\review-transparent.json
.venv\Scripts\i-mage-not-ai.exe explain artifacts\manual-image-review\review-transparent.json
```
