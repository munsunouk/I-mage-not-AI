from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from i_mage_not_ai.learned_similarity import compare_dinov2, compare_lpips
from i_mage_not_ai.openpose_anatomy import BODY_25, analyze_openpose_anatomy


def _image(path: Path) -> None:
    Image.new("RGBA", (40, 60), (255, 255, 255, 255)).save(path)


def _pose() -> list[float]:
    values = [0.0] * (len(BODY_25) * 3)
    points = {
        "Neck": (20, 10), "MidHip": (20, 50),
        "RShoulder": (10, 14), "RElbow": (6, 24), "RWrist": (10, 34),
    }
    for name, (x, y) in points.items():
        index = BODY_25[name] * 3
        values[index:index + 3] = [float(x), float(y), 0.9]
    return values


def _policy(path: Path, *, max_ratio: float = 0.30) -> None:
    path.write_text(json.dumps({
        "schema_version": "1", "keypoint_model": "BODY_25", "person_index": 0,
        "min_keypoint_confidence": 0.25,
        "scale_pair": {"from": "Neck", "to": "MidHip"},
        "bone_ratio_limits": [{"id": "right_upper_arm", "from": "RShoulder", "to": "RElbow",
                               "min_ratio": 0.25, "max_ratio": max_ratio}],
        "joint_angle_limits": [{"id": "right_elbow", "proximal": "RShoulder", "joint": "RElbow",
                                "distal": "RWrist", "min_degrees": 100, "max_degrees": 170}],
    }), encoding="utf-8")


def test_openpose_anatomy_emits_measured_pass_with_complete_coverage(tmp_path: Path) -> None:
    image = tmp_path / "character.png"
    detections = tmp_path / "openpose.json"
    policy = tmp_path / "policy.json"
    _image(image)
    detections.write_text(json.dumps({"people": [{"pose_keypoints_2d": _pose()}]}), encoding="utf-8")
    _policy(policy)

    report = analyze_openpose_anatomy(image, detections, policy)

    assert report["status"] == "PASS"
    assert report["completeness"] == "COMPLETE"
    assert [finding["algorithm"] for finding in report["findings"]] == [
        "openpose_bone_ratio", "openpose_joint_angle"]
    assert report["evidence"]["keypoint_model"] == "BODY_25"


def test_openpose_anatomy_fails_explicit_proportion_limit(tmp_path: Path) -> None:
    image = tmp_path / "character.png"
    detections = tmp_path / "openpose.json"
    policy = tmp_path / "policy.json"
    _image(image)
    detections.write_text(json.dumps({"people": [{"pose_keypoints_2d": _pose()}]}), encoding="utf-8")
    _policy(policy, max_ratio=0.26)

    report = analyze_openpose_anatomy(image, detections, policy)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["status"] == "FAIL"


def test_openpose_missing_person_is_inconclusive_not_pass(tmp_path: Path) -> None:
    image = tmp_path / "character.png"
    detections = tmp_path / "openpose.json"
    policy = tmp_path / "policy.json"
    _image(image)
    detections.write_text(json.dumps({"people": []}), encoding="utf-8")
    _policy(policy)

    report = analyze_openpose_anatomy(image, detections, policy)

    assert report["status"] == "INCONCLUSIVE"
    assert report["completeness"] == "INCOMPLETE"
    assert report["reason"] == "OpenPose detected no people"


def test_openpose_low_confidence_landmark_is_inconclusive(tmp_path: Path) -> None:
    image = tmp_path / "character.png"
    detections = tmp_path / "openpose.json"
    policy = tmp_path / "policy.json"
    _image(image)
    values = _pose()
    values[BODY_25["RElbow"] * 3 + 2] = 0.1
    detections.write_text(json.dumps({"people": [{"pose_keypoints_2d": values}]}), encoding="utf-8")
    _policy(policy)

    report = analyze_openpose_anatomy(image, detections, policy)

    assert report["status"] == "INCONCLUSIVE"
    assert report["findings"][0]["status"] == "INCONCLUSIVE"


def test_learned_similarity_requires_explicit_limit_and_local_model(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    candidate = tmp_path / "candidate.png"
    _image(reference)
    _image(candidate)

    lpips_report = compare_lpips(reference, candidate, max_distance=None)
    dino_report = compare_dinov2(reference, candidate, model_dir=tmp_path / "missing")

    assert lpips_report["status"] == "INCONCLUSIVE"
    assert lpips_report["completeness"] == "INCOMPLETE"
    assert dino_report["status"] == "INCONCLUSIVE"
    assert dino_report["completeness"] == "INCOMPLETE"


def test_different_dimensions_are_rejected_before_model_loading(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    candidate = tmp_path / "candidate.png"
    Image.new("RGB", (20, 20)).save(reference)
    Image.new("RGB", (21, 20)).save(candidate)

    with pytest.raises(ValueError, match="identical dimensions"):
        compare_lpips(reference, candidate)
    with pytest.raises(ValueError, match="identical dimensions"):
        compare_dinov2(reference, candidate, model_dir=tmp_path)
