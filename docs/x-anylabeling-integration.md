# X-AnyLabeling integration

This document is the hub for using [X-AnyLabeling](https://github.com/CVHub520/X-AnyLabeling) (XAL) with **i-mage-not-AI**. XAL is a **separate** application (GPL v3); this repository does not vendor XAL code or model weights. For the [Agent Skill](../.agents/skills/i-mage-not-ai/SKILL.md) **image workflow**, XAL is **required** at step 2 (candidate masks). Hand-authored manifests (e.g. [examples/icon](../examples/)) do not need XAL.

**Upstream project:** [CVHub520/X-AnyLabeling](https://github.com/CVHub520/X-AnyLabeling) · [Documentation](https://xanylabeling.com/docs/x-anylabeling) · [Remote inference server](https://github.com/CVHub520/X-AnyLabeling-Server)

Agent workflow entry point: [.agents/skills/i-mage-not-ai/SKILL.md](../.agents/skills/i-mage-not-ai/SKILL.md).

## Headless CLI install (Skill step 2)

The Skill image workflow expects **`xanylabeling models …`** and **`xanylabeling segment …`** (headless candidate masks, no GUI). That CLI is proposed in upstream [PR #1485](https://github.com/CVHub520/X-AnyLabeling/pull/1485) and is **not** on upstream `main` yet. Until it merges, install from the PR branch:

```sh
git clone --branch codex/headless-cli-inference --single-branch \
  https://github.com/hyeyoung-Moon/X-AnyLabeling.git
cd X-AnyLabeling
git checkout d072c4446b136533e5f7e979f7413b94cfef2ad1
python3 -m pip install -e .
xanylabeling models list --task segmentation --json
```

Branch tree: [hyeyoung-Moon/X-AnyLabeling `codex/headless-cli-inference`](https://github.com/hyeyoung-Moon/X-AnyLabeling/tree/codex/headless-cli-inference). Headless command reference: [cli.md § Headless Model Inference](https://github.com/hyeyoung-Moon/X-AnyLabeling/blob/codex/headless-cli-inference/docs/en/cli.md#4-headless-model-inference) on that branch.

After PR #1485 lands on [CVHub520/X-AnyLabeling](https://github.com/CVHub520/X-AnyLabeling) `main`, switch to an upstream checkout or release and retire this pin. Use a **separate Python environment** from `i-mage-not-ai` (GPL v3 vs MIT).

Example (fox forest trial model):

```sh
xanylabeling --work-dir <model-data-dir> models check groundingdino_swint_sam2_large-r20240806 --device cpu --json
xanylabeling --work-dir <model-data-dir> segment \
  --input /path/to/fox-forest.png \
  --model groundingdino_swint_sam2_large-r20240806 \
  --prompt fox --prompt mushroom \
  --output ./review-candidates --json
```

`models check` does not download weights; `segment` may. Get user approval before large downloads.

## Compatibility notes

Snapshot **2026-11-03 (KST)**. Re-check upstream [README](https://github.com/CVHub520/X-AnyLabeling/blob/main/README.md) when upgrading XAL.

| Date (upstream) | XAL change | Relevance here |
|-----------------|------------|----------------|
| 2026-11-03 | [PR #1485](https://github.com/CVHub520/X-AnyLabeling/pull/1485): headless `models` + `segment` CLI | **Install for Skill step 2** — [branch `codex/headless-cli-inference`](https://github.com/hyeyoung-Moon/X-AnyLabeling/tree/codex/headless-cli-inference) until merge. |
| 2026-11-03 | Adjustable image grid + cell labels for inspecting annotations | Aligns with contact-sheet / overlay review before manifest (Skill step 3). |
| 2026-10-27 | Shape display modes; **binary mask view** (white foreground on black) | Same convention as final measurement masks (black outside, nonzero inside). |
| 2026-10-24 | Smooth zoom, pan, boundary clipping on canvas | Useful when manually refining shapes in the GUI fallback path. |
| 2026-08-05 | X-AnyLabeling v4.x line | Record `application.version` in candidate exports (see `xanylabeling.candidates.v1` examples under `artifacts/`). |

Repository trials have used XAL **4.2.3** with model `groundingdino_swint_sam2_large-r20240806` (`artifacts/xal-fox-candidates-01/`).

## Pipeline role (three evidence stages)

```text
XAL candidates  →  Agent approval  →  i-mage-not-ai review
(proposal)          (manifest v0.6)     (deterministic PASS/FAIL/INCOMPLETE)
```

| Stage | Owner | Output | Ground truth? |
|-------|--------|--------|---------------|
| 1. Inference / annotation | X-AnyLabeling (+ optional Agent prompts) | XLABEL JSON, `*.candidates.json`, candidate mask PNGs | **No** — model proposals only |
| 2. Review & contract | Agent (Cursor/Codex per Skill) | Approved binary masks, `feature_inventory`, [feature manifest](../schemas/feature-manifest-v0.6.schema.json) | **Partial** — semantic labels not verified by CLI |
| 3. Measurement | `i-mage-not-ai` CLI | `review.json`, coverage, exit codes | **Yes** for declared rules and thresholds only |

XAL does **not** run manifest `review`, declare project thresholds, or replace the Agent. A deterministic CLI **PASS** does not prove that masks match human intent or that the image is non-AI.

## Upstream documentation map

| # | Topic | Link |
|---|--------|------|
| 0 | Remote inference | [X-AnyLabeling-Server](https://github.com/CVHub520/X-AnyLabeling-Server) |
| 1 | Install & quickstart | [get_started.md](https://github.com/CVHub520/X-AnyLabeling/blob/main/docs/en/get_started.md) |
| 2 | GUI usage, formats, display modes | [user_guide.md](https://xanylabeling.com/docs/x-anylabeling/user_guide) |
| 3 | Published CLI (convert, GUI) on upstream `main` | [cli.md](https://github.com/CVHub520/X-AnyLabeling/blob/main/docs/en/cli.md) |
| 3b | Headless `models` / `segment` (Skill step 2; PR #1485) | [cli.md on `codex/headless-cli-inference`](https://github.com/hyeyoung-Moon/X-AnyLabeling/blob/codex/headless-cli-inference/docs/en/cli.md#4-headless-model-inference) |
| 4 | Custom models | [custom_model.md](https://github.com/CVHub520/X-AnyLabeling/blob/main/docs/en/custom_model.md) |
| 5 | Segmentation examples | [examples/segmentation](https://github.com/CVHub520/X-AnyLabeling/tree/main/examples/segmentation) |
| 6 | Segment-anything / grounding examples | [examples/vision_foundation](https://github.com/CVHub520/X-AnyLabeling/tree/main/examples/vision_foundation), [examples/grounding](https://github.com/CVHub520/X-AnyLabeling/tree/main/examples/grounding) |

## Data formats (do not conflate)

| Artifact | Schema / format | Role |
|----------|-----------------|------|
| XAL native label | **XLABEL** JSON (per image) | XAL’s canonical annotation file; shapes, labels, attributes |
| Skill candidate export | `xanylabeling.candidates.v1` | Candidate provenance + masks; **not** a feature manifest |
| Agent overlay log | `i-mage-not-ai/overlay-review/1` ([schema](../schemas/overlay-review.schema.json)) | Accept/reject audit before final masks |
| Codex review decisions | `xanylabeling.codex-review.v1` (repo convention) | Structured review notes alongside overlays |
| Weight revision | `i-mage-not-ai/xal-weights-revision/1` ([schema](../schemas/xal-weights-revision.schema.json)) | ONNX file hashes when weights change |
| Final contract | [feature manifest v0.6](../schemas/feature-manifest-v0.6.schema.json) | Only **approved** features + SHA-256 pinned asset |

### Bridging to measurement masks

Final masks for `i-mage-not-ai`:

- Same width/height as the source asset.
- Binary PNG: **black = outside**, any **nonzero = inside** (matches XAL binary mask display mode).

**Path A — GUI / documented CLI (upstream):**

1. Run segmentation in the X-AnyLabeling desktop app (or import labels).
2. Export masks using XAL’s **MASK** support and `xlabel2mask` conversion ([format list in upstream README](https://github.com/CVHub520/X-AnyLabeling#key-features); details in [user guide § formats](https://xanylabeling.com/docs/x-anylabeling/user_guide)).
3. Agent maps exported PNGs into manifest `features[].geometry.path` and completes v0.6 `feature_inventory`.

**Path B — Headless `segment` (Skill default):**

Install X-AnyLabeling from [PR #1485 branch `codex/headless-cli-inference`](https://github.com/hyeyoung-Moon/X-AnyLabeling/tree/codex/headless-cli-inference) ([install steps above](#headless-cli-install-skill-step-2)). Run `xanylabeling models list|info|check` and `xanylabeling segment` as in the [Skill](../.agents/skills/i-mage-not-ai/SKILL.md). Upstream `main` [cli.md](https://github.com/CVHub520/X-AnyLabeling/blob/main/docs/en/cli.md) still documents convert/GUI only until the PR merges; use Path A if you cannot install the PR branch.

There is **no** automatic XAL → approved-manifest command in this repo; the Agent builds the manifest explicitly.

## Model selection checklist (Skill step 2)

Before `segment` or heavy GUI inference:

1. **Task** — segmentation / grounding / instance seg (see upstream [model library](https://github.com/CVHub520/X-AnyLabeling#model-library)).
2. **Prompting** — Grounding models need text prompts; SAM-style models may need points/boxes; class detectors return fixed classes only.
3. **`--work-dir`** — model cache directory; `models check` does not download; `segment` may download weights (get user approval first).
4. **Record** — XAL app version, `model_id`, device, provider, prompts, and [weight revision](../schemas/xal-weights-revision.schema.json) when ONNX files change.
5. **Pose** — XAL pose exports (DWPose, YOLO-Pose) are **not** the same as OpenPose BODY_25 JSON used by optional `character anatomy` (separate command, separate evidence).

Common trial model: `groundingdino_swint_sam2_large-r20240806` (Grounding + SAM2).

## End-to-end examples in this repository

| Path | Description |
|------|-------------|
| [artifacts/skill-segmentation-test/README.md](../artifacts/skill-segmentation-test/README.md) | Skill steps 2–9 replay on `fox-forest.png` |
| [artifacts/xal-fox-candidates-01/README.md](../artifacts/xal-fox-candidates-01/README.md) | XAL step 2 exports (`xanylabeling.candidates.v1`) |
| [artifacts/xal-fox-review-01/](../artifacts/xal-fox-review-01/) | Extended 12-feature overlay audit |

Local only (not CI): `bash scripts/run_local_skill_flow.sh` or `pytest -m local_skill`.

## License and distribution

- **i-mage-not-AI** is [MIT](../LICENSE).
- **X-AnyLabeling** is [GPL v3](https://github.com/CVHub520/X-AnyLabeling/blob/main/LICENSE). Install and run XAL in its own environment; do not combine or redistribute XAL source inside this repository.
- Optional **X-AnyLabeling-Server** for remote inference is a separate component; treat network egress and API keys under your org policy (Skill: no silent remote switch).

## What we do not copy from XAL

Do not expect this repo to ship XAL’s model zoo, VLM/OCR/3D tooling, or annotation UI. XAL output is **never** treated as CLI PASS without Agent approval and explicit manifest rules.
