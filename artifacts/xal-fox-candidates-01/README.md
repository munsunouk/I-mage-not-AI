# X-AnyLabeling candidates — fox forest (Skill step 2)

Headless inference export for `../skill-segmentation-test/fox-forest.png`. Regenerate with `xanylabeling segment` after installing XAL from [PR #1485 branch `codex/headless-cli-inference`](../../docs/x-anylabeling-integration.md#headless-cli-install-skill-step-2).

- **Metadata:** `candidates/fox-forest.png.candidates.json` (`schema: xanylabeling.candidates.v1`, status `unreviewed_candidates` at export time).
- **Masks:** `masks/fox-forest.png/candidate-*.png` (23 shapes).
- **Overlay review aids:** `contact-sheet-01.jpg`, `contact-sheet-02.jpg`, `inspection-overlays/`.

Regenerate contact sheets (requires repo checkout paths):

```sh
python3 artifacts/xal-fox-candidates-01/review_candidates.py
```

- **Weight revision record:** `inference-weights-revision.json` (refresh with `sync_xal_weight_revision.py --work-dir <model-data-dir> --update` after downloads).

Downstream Skill steps 3–9: `artifacts/skill-segmentation-test/README.md` (`overlay-review.json`, `review_intent_fox.json`).
