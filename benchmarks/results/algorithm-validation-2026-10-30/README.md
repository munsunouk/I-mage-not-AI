# Algorithm golden-value validation — 2026-10-30

## Result

`tests/test_cli.py`, `tests/test_benchmark.py`, and the new
`tests/test_algorithm_gold_values.py` completed with **52 passed**. JUnit
evidence is in [junit.xml](junit.xml). The six new golden-value cases exercise
the raster, mask, SVG, game-trace, and runtime-evidence CLI paths. Their small
synthetic inputs have explicit pixel coordinates, binary masks, trace samples,
and expected numeric outputs; they do not depend on model-generated labels.

Saved CLI JSON is in this directory. The corresponding source images, masks,
SVG, manifests, trace, and policy files are under [fixtures](fixtures/).
Run `.\.venv\Scripts\python.exe benchmarks\results\algorithm-validation-2026-10-30\save_cli_reports.py`
from the repository root to recreate the saved CLI reports. Run
`.\.venv\Scripts\pytest.exe tests\test_cli.py tests\test_benchmark.py tests\test_algorithm_gold_values.py -q`
to repeat the assertions.

## Ground-truth checks

| Input | Calculation | Expected and observed |
|---|---|---|
| 8×8 RGBA alpha fixture; visible pixels `(1,2)` with alpha 255 and `(5,3)` with alpha 128 | Alpha bbox, transparent fraction, alpha-weighted centroid, margins, exact visible palette | bbox `[1,2,6,4]`; transparent `62/64 = 0.96875`; centroid offset `0.20585497558047625`; margins `{left:0.125, top:0.25, right:0.25, bottom:0.5}`; 2 RGB colors |
| 8×8 feature mask with pixels `(1,1),(2,1),(2,2),(6,6),(6,7)` | 8-connected topology, occupancy, bbox, reflection IoU, palette, luma | 2 components; `5/64 = 0.078125`; bbox `[1,1,7,8]`; reflection IoU `0`; exact masked palette `2`; fixed Lab bins `[100,100,100]` yield `1`; luma levels `1` |
| Same mask, with one red pixel changed from `(200,40,30)` to `(201,40,30)` | Channel range and CIEDE2000, explicit reference and channel-median reference | Maximum channel range `1`; both reference paths choose `[200,40,30]`; max ΔE00 `0.20515146556976527`; exceedance fraction at tolerance `0.1` is `1/5 = 0.2` |
| Published Sharma CIEDE2000 Lab pair in the existing CLI test suite | CIEDE2000 formula reference vector | ΔE00 `2.0425` to four decimal places |
| 8×8 black/white checkerboard and full-frame mask | Mask occupancy, 2D FFT periodic energy, planar fit and raster-gradient semantic state | occupancy `1`; periodic energy ratio `1`; planar-fit R² `0`; gradient semantics `INCONCLUSIVE` |
| 8×8 RGB plane fixture and full-frame mask | Plane-fit diagnostic and raster-gradient semantic state | planar-fit R² `1`; both semantic decisions remain `INCONCLUSIVE` |
| 2×2 RGB seam fixture | Maximum mean opposite-edge color error | `5.0` |
| SVG with one line from `(0,0)` to `(3,4)`, one linear and one radial gradient, explicit stroke width 3 | Gradient declarations, stroke width, path bounds/length/segments | 2 gradients; stroke width 3; bbox `[0,0,3,4]`; length `5`; 1 line segment |
| Four-sample game trace with positions `[0,1,4,9]` on x | Motion, velocity, acceleration, jerk, rotation, loop, pose, bone, foot slide, anchor, event, particle lifetime/bounds, occlusion | max step `5`, mean step `3`, max velocity `5`, max acceleration `2`, max jerk `0`; rotation step/loop `180°`; pose boundary `5`; bone deviation `0`; foot slide and anchor distance `0.1`; event error `0.05`; particle lifetime `1`; out-of-bounds samples `0`; occlusion `0.0625` |
| Versioned runtime record with two callbacks and one particle sample | Callback count/timing, particle sample/bounds/alive count | 2 callbacks; maximum time error `0.01s`; sample at `1.02s`; bounds `[-0.5,-0.25,0.75,0.5]`; alive count `8`; report `PASS/COMPLETE` |

## Reading the statuses

Some fixture reviews intentionally end in `FAIL` because their supplied
threshold is set just below the known measurement: centroid `0.20585 > 0.2`,
overlap `1.0 > 0.99`, checkerboard energy `1.0 > 0.9`, seam error `5 > 4`,
and SVG gradient/stroke values `2 > 1` and `3 > 2`. Those are threshold
behavior checks; the measurements match their expected values. The game trace
and runtime evidence policies pass completely. Raster gradient intent and
plane-fit intent remain `INCONCLUSIVE` by design because pixel statistics
cannot establish semantic intent.

## Scope

This validates the deterministic calculations against controlled numeric
fixtures. It does not validate whether a human-authored mask captures the right
semantic feature, whether thresholds are artistically appropriate, or whether
an image is aesthetically good / “AI slop.” No X-AnyLabeling semantic masks
were needed for these math conformance fixtures: mask membership itself is the
known ground truth. The checked-in game trace is deterministic sample evidence,
not a live Godot/Unity run in this validation.
