# OpenPose anatomy and learned image similarity

These checks complement the feature-mask and game-trace review. They run as explicit CLI commands because each needs separate model evidence and configuration; they are not inferred from a generic image manifest.

## OpenPose BODY_25 anatomy

Run OpenPose outside the review CLI and save its ordinary JSON keypoint output. The checker consumes that saved output and a policy file:

```text
i-mage-not-ai character anatomy --image character.png --openpose-json openpose.json --policy anatomy-policy.json --output anatomy-report.json
```

The policy declares BODY_25 landmark names, an explicit scale pair (default `Neck` to `MidHip`), a confidence floor, normalized bone-ratio ranges, and joint-angle ranges. For example:

```json
{
  "schema_version": "1",
  "keypoint_model": "BODY_25",
  "person_index": 0,
  "min_keypoint_confidence": 0.25,
  "scale_pair": {"from": "Neck", "to": "MidHip"},
  "bone_ratio_limits": [
    {"id": "upper_arm_right", "from": "RShoulder", "to": "RElbow", "min_ratio": 0.1, "max_ratio": 0.5}
  ],
  "joint_angle_limits": [
    {"id": "elbow_right", "proximal": "RShoulder", "joint": "RElbow", "distal": "RWrist", "min_degrees": 0, "max_degrees": 180}
  ]
}
```

The sample limits above only demonstrate the schema. Replace them with approved requirements for the character, art style, camera, and pose. The checker measures segment length divided by the declared scale length, and the angle between adjacent landmark vectors. Low-confidence or missing points, degenerate scale pairs, and missing policy checks stay `INCONCLUSIVE`; a missing person is not a pass. Reports include source hashes, detector evidence, and coverage.

This is a deterministic check of supplied points, not a proof that OpenPose located the true joints. BODY_25 is a human skeleton; it is unsuitable for animals, monsters, robots with non-human articulation, or deliberately abstract designs unless an appropriately validated custom detector and schema are added. OpenPose itself is not bundled or launched by this command. Its upstream license is limited to academic/non-profit noncommercial research use; check the license before using or redistributing OpenPose in a commercial workflow.

## LPIPS and DINOv2 similarity

```text
i-mage-not-ai similarity --metric lpips --reference reference.png --candidate candidate.png --max-distance 0.18 --network alex
i-mage-not-ai similarity --metric dinov2 --reference reference.png --candidate candidate.png --min-similarity 0.82 --model-dir models/dinov2-base
```

LPIPS reports a learned perceptual distance (smaller is more similar); this implementation requires identical image dimensions and a local torchvision backbone cache. DINOv2 reports cosine similarity between the model's CLS-token embeddings (larger is more similar) and requires a local Hugging Face model directory. Both load only local model files: they never download code or weights. Install the optional runtime with `pip install -e ".[perceptual]"` after selecting a compatible PyTorch build and obtaining model weights through their official distribution channels.

Thresholds are optional for diagnostic measurements. Without an explicit threshold, the report is `INCONCLUSIVE` with `INCOMPLETE` coverage, even when the number is computed. A threshold produces `PASS` or `FAIL` for that comparison only. Record the model files, code/runtime versions, device, image hashes, crop/resize policy, and threshold when comparing a set of assets. Learned similarity does not certify identity, anatomy, visual quality, or preservation of a particular feature; DINOv2 global embeddings can overlook small local changes, while LPIPS is intended for aligned image patches.

LPIPS follows the authors' CVPR 2018 learned perceptual metric and its implementation uses BSD-2-Clause terms. DINOv2's official code and weights are Apache-2.0. Model output depends on the selected checkpoint and preprocessing; do not compare scores from different configurations as if they shared one scale.

## References

- Cao et al., [OpenPose: Realtime Multi-Person 2D Pose Estimation using Part Affinity Fields](https://arxiv.org/abs/1812.08008); [official implementation and license](https://github.com/CMU-Perceptual-Computing-Lab/openpose).
- Zhang et al., [The Unreasonable Effectiveness of Deep Features as a Perceptual Metric](https://openaccess.thecvf.com/content_cvpr_2018/papers/Zhang_The_Unreasonable_Effectiveness_CVPR_2018_paper.pdf); [official LPIPS implementation](https://github.com/richzhang/PerceptualSimilarity).
- Oquab et al., [DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193); [official code, model card, and license](https://github.com/facebookresearch/dinov2).
