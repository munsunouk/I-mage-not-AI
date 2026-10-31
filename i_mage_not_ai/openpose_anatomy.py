"""Deterministic anatomy checks over saved OpenPose BODY_25 detections."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image


BODY_25 = {
    "Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
    "LShoulder": 5, "LElbow": 6, "LWrist": 7, "MidHip": 8,
    "RHip": 9, "RKnee": 10, "RAnkle": 11, "LHip": 12, "LKnee": 13,
    "LAnkle": 14, "REye": 15, "LEye": 16, "REar": 17, "LEar": 18,
    "LBigToe": 19, "LSmallToe": 20, "LHeel": 21, "RBigToe": 22,
    "RSmallToe": 23, "RHeel": 24,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _point(keypoints: list[tuple[float, float, float]], name: str,
           confidence_floor: float) -> tuple[float, float] | None:
    if name not in BODY_25:
        raise ValueError(f"unknown BODY_25 keypoint: {name}")
    x, y, confidence = keypoints[BODY_25[name]]
    return (x, y) if confidence >= confidence_floor else None


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle_degrees(a: tuple[float, float], vertex: tuple[float, float],
                   c: tuple[float, float]) -> float | None:
    ax, ay = a[0] - vertex[0], a[1] - vertex[1]
    cx, cy = c[0] - vertex[0], c[1] - vertex[1]
    denominator = math.hypot(ax, ay) * math.hypot(cx, cy)
    if denominator == 0:
        return None
    cosine = max(-1.0, min(1.0, (ax * cx + ay * cy) / denominator))
    return math.degrees(math.acos(cosine))


def analyze_openpose_anatomy(image_path: Path, keypoints_path: Path,
                             policy_path: Path) -> dict[str, Any]:
    """Check explicit proportion and joint-angle limits against OpenPose output.

    Detector inference is intentionally upstream. This function remeasures saved
    BODY_25 keypoints and never infers anatomical limits from the image.
    """
    image_path = image_path.resolve(strict=True)
    keypoints_path = keypoints_path.resolve(strict=True)
    policy_path = policy_path.resolve(strict=True)
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        evidence = json.loads(keypoints_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read OpenPose evidence or policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != "1":
        raise ValueError("anatomy policy schema_version must be '1'")
    if policy.get("keypoint_model", "BODY_25") != "BODY_25":
        raise ValueError("only the OpenPose BODY_25 keypoint layout is supported")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("people"), list):
        raise ValueError("OpenPose JSON must contain a people array")
    if not evidence["people"]:
        return _inconclusive(image_path, keypoints_path, policy_path, "OpenPose detected no people")

    person_index = policy.get("person_index", 0)
    if isinstance(person_index, bool) or not isinstance(person_index, int) or person_index < 0:
        raise ValueError("person_index must be a non-negative integer")
    if person_index >= len(evidence["people"]):
        return _inconclusive(image_path, keypoints_path, policy_path,
                             f"person_index {person_index} is absent from OpenPose output")
    person = evidence["people"][person_index]
    raw = person.get("pose_keypoints_2d") if isinstance(person, dict) else None
    if not isinstance(raw, list) or len(raw) != len(BODY_25) * 3:
        raise ValueError("selected person must contain exactly 75 BODY_25 pose_keypoints_2d values")
    parsed = [_finite_number(value, f"pose_keypoints_2d[{index}]") for index, value in enumerate(raw)]
    keypoints = [(parsed[i], parsed[i + 1], parsed[i + 2]) for i in range(0, len(parsed), 3)]
    if any(not 0 <= confidence <= 1 for _, _, confidence in keypoints):
        raise ValueError("OpenPose keypoint confidences must be between 0 and 1")

    confidence_floor = _finite_number(policy.get("min_keypoint_confidence", 0.25),
                                      "min_keypoint_confidence")
    if not 0 <= confidence_floor <= 1:
        raise ValueError("min_keypoint_confidence must be between 0 and 1")
    with Image.open(image_path) as image:
        image.load()
        width, height = image.size
    visible = [(x, y, confidence) for x, y, confidence in keypoints if confidence >= confidence_floor]
    outside = [BODY_25_NAME for BODY_25_NAME, index in BODY_25.items()
               if keypoints[index][2] >= confidence_floor and
               not (0 <= keypoints[index][0] < width and 0 <= keypoints[index][1] < height)]

    scale_spec = policy.get("scale_pair", {"from": "Neck", "to": "MidHip"})
    if not isinstance(scale_spec, dict) or set(scale_spec) != {"from", "to"}:
        raise ValueError("scale_pair must contain 'from' and 'to' BODY_25 names")
    scale_a = _point(keypoints, scale_spec["from"], confidence_floor)
    scale_b = _point(keypoints, scale_spec["to"], confidence_floor)
    scale = _distance(scale_a, scale_b) if scale_a and scale_b else None
    if scale is not None and scale <= 0:
        scale = None

    findings: list[dict[str, Any]] = []
    configured = 0
    for rule in policy.get("bone_ratio_limits", []):
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise ValueError("each bone_ratio_limits entry requires a string id")
        minimum = _finite_number(rule.get("min_ratio"), f"{rule['id']}.min_ratio")
        maximum = _finite_number(rule.get("max_ratio"), f"{rule['id']}.max_ratio")
        if minimum < 0 or maximum < minimum:
            raise ValueError(f"{rule['id']} requires 0 <= min_ratio <= max_ratio")
        landmark_from, landmark_to = rule.get("from"), rule.get("to")
        if not isinstance(landmark_from, str) or not isinstance(landmark_to, str):
            raise ValueError(f"{rule['id']} requires BODY_25 'from' and 'to' landmarks")
        measured: float | None
        reason: str | None
        if scale is None:
            measured, status, reason = None, "INCONCLUSIVE", "scale landmarks are unavailable or coincide"
        else:
            a = _point(keypoints, landmark_from, confidence_floor)
            b = _point(keypoints, landmark_to, confidence_floor)
            measured = _distance(a, b) / scale if a and b else None
            status = "INCONCLUSIVE" if measured is None else ("PASS" if minimum <= measured <= maximum else "FAIL")
            reason = "one or more keypoints are below the confidence floor" if measured is None else None
        findings.append({"id": rule["id"], "algorithm": "openpose_bone_ratio",
                         "status": status, "measured": measured,
                         "threshold": {"min_ratio": minimum, "max_ratio": maximum},
                         "reason": reason, "formula": "Euclidean segment length / declared scale-pair length"})
        configured += 1

    for rule in policy.get("joint_angle_limits", []):
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise ValueError("each joint_angle_limits entry requires a string id")
        minimum = _finite_number(rule.get("min_degrees"), f"{rule['id']}.min_degrees")
        maximum = _finite_number(rule.get("max_degrees"), f"{rule['id']}.max_degrees")
        if minimum < 0 or maximum > 180 or maximum < minimum:
            raise ValueError(f"{rule['id']} requires 0 <= min_degrees <= max_degrees <= 180")
        proximal, joint, distal = (rule.get(field) for field in ("proximal", "joint", "distal"))
        if not all(isinstance(name, str) for name in (proximal, joint, distal)):
            raise ValueError(f"{rule['id']} requires proximal, joint, and distal BODY_25 landmarks")
        assert isinstance(proximal, str) and isinstance(joint, str) and isinstance(distal, str)
        points = [_point(keypoints, name, confidence_floor) for name in (proximal, joint, distal)]
        angle_measurement: float | None = None
        if all(point is not None for point in points):
            first, vertex, last = points
            assert first is not None and vertex is not None and last is not None
            angle_measurement = _angle_degrees(first, vertex, last)
        status = "INCONCLUSIVE" if angle_measurement is None else ("PASS" if minimum <= angle_measurement <= maximum else "FAIL")
        findings.append({"id": rule["id"], "algorithm": "openpose_joint_angle",
                         "status": status, "measured": angle_measurement,
                         "threshold": {"min_degrees": minimum, "max_degrees": maximum},
                         "reason": "one or more keypoints are below the confidence floor or degenerate" if angle_measurement is None else None,
                         "formula": "acos(dot(v1, v2) / (|v1| * |v2|)) in degrees"})
        configured += 1

    complete = not outside and all(item["status"] != "INCONCLUSIVE" for item in findings)
    if any(item["status"] == "FAIL" for item in findings):
        status = "FAIL"
    elif not findings or not complete:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"
    return {
        "schema_version": "1", "status": status,
        "completeness": "COMPLETE" if complete and configured else "INCOMPLETE",
        "asset": {"path": str(image_path), "sha256": _sha256(image_path), "width": width, "height": height},
        "evidence": {"path": str(keypoints_path), "sha256": _sha256(keypoints_path),
                     "detector": "OpenPose", "keypoint_model": "BODY_25", "person_index": person_index,
                     "person_count": len(evidence["people"]), "confidence_floor": confidence_floor,
                     "confident_keypoint_count": len(visible), "out_of_bounds_keypoints": outside},
        "scale_pair": {**scale_spec, "measured_pixels": scale},
        "findings": findings,
        "limitations": ["OpenPose detections are model estimates, not ground-truth landmarks.",
                        "Anatomical limits must be supplied for the character species, style, and pose.",
                        "BODY_25 is a human skeleton and is not appropriate for non-human characters."],
    }


def _inconclusive(image_path: Path, keypoints_path: Path, policy_path: Path,
                  reason: str) -> dict[str, Any]:
    with Image.open(image_path) as image:
        width, height = image.size
    return {"schema_version": "1", "status": "INCONCLUSIVE", "completeness": "INCOMPLETE",
            "asset": {"path": str(image_path), "sha256": _sha256(image_path), "width": width, "height": height},
            "evidence": {"path": str(keypoints_path), "sha256": _sha256(keypoints_path), "detector": "OpenPose"},
            "findings": [], "reason": reason, "policy_path": str(policy_path)}
