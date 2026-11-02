# X-AnyLabeling candidates — fox forest (Skill step 2)

Headless inference export for `../skill-segmentation-test/fox-forest.png`.

- **Metadata:** `candidates/fox-forest.png.candidates.json` (`schema: xanylabeling.candidates.v1`, status `unreviewed_candidates` at export time).
- **Masks:** `masks/fox-forest.png/candidate-*.png` (23 shapes).
- **Overlay review aids:** `contact-sheet-01.jpg`, `contact-sheet-02.jpg`, `inspection-overlays/`.

Regenerate contact sheets (requires repo checkout paths):

```sh
python3 artifacts/xal-fox-candidates-01/review_candidates.py
```

Downstream Skill steps 3–9: `artifacts/skill-segmentation-test/README.md`.
