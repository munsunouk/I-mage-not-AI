"""Preflight checks for CLI and optional Skill fox trial artifacts."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _check(name: str, ok: bool, detail: str, *, required: bool = True) -> dict[str, Any]:
    return {"name": name, "ok": ok, "required": required, "detail": detail}


def run_doctor(repo_root: Path | None = None, *, skill_trial: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    root = repo_root.resolve() if repo_root else None

    checks.append(
        _check(
            "python_version",
            sys.version_info >= (3, 11),
            f"{sys.version_info.major}.{sys.version_info.minor}",
        )
    )
    spec_ok = importlib.util.find_spec("i_mage_not_ai") is not None
    checks.append(_check("package_import", spec_ok, "i_mage_not_ai importable"))

    if root is not None:
        schemas = root / "schemas" / "feature-manifest.schema.json"
        checks.append(
            _check(
                "schemas_present",
                schemas.is_file(),
                str(schemas) if schemas.is_file() else f"missing {schemas}",
                required=False,
            )
        )

    if skill_trial:
        if root is None:
            checks.append(
                _check("skill_trial_paths", False, "pass --repo-root for skill-trial checks")
            )
        else:
            trial = root / "artifacts" / "skill-segmentation-test"
            xal = root / "artifacts" / "xal-fox-candidates-01"
            required_files = [
                trial / "manifest.json",
                trial / "fox-forest.png",
                trial / "overlay-review.json",
                trial / "review_intent_fox.json",
                xal / "candidates" / "fox-forest.png.candidates.json",
                xal / "inference-weights-revision.json",
            ]
            missing = [str(p.relative_to(root)) for p in required_files if not p.is_file()]
            checks.append(
                _check(
                    "skill_trial_artifacts",
                    not missing,
                    "ok" if not missing else f"missing: {', '.join(missing)}",
                )
            )

    required_fail = any(not c["ok"] and c["required"] for c in checks)
    optional_fail = any(not c["ok"] and not c["required"] for c in checks)
    if required_fail:
        status = "FAIL"
    elif optional_fail:
        status = "INCOMPLETE"
    else:
        status = "READY"
    return {"status": status, "checks": checks}


def validate_overlay_inventory_alignment(manifest: dict, overlay_review: dict) -> list[str]:
    """Return human-readable errors when overlay-approved features diverge from inventory."""
    errors: list[str] = []
    overlay_by_feature = {f["feature_id"]: f for f in overlay_review.get("features", [])}
    inventory = manifest.get("feature_inventory") or []
    inv_by_feature = {
        item["feature_id"]: item for item in inventory if item.get("feature_id")
    }

    for feature_id, ov in overlay_by_feature.items():
        inv = inv_by_feature.get(feature_id)
        if inv is None:
            errors.append(f"overlay feature {feature_id!r} has no feature_inventory entry")
            continue
        if inv.get("status") != "approved":
            errors.append(f"inventory {feature_id!r} status is {inv.get('status')!r}, expected approved")
        approved_candidates = {
            c["candidate_id"]
            for c in inv.get("candidates", [])
            if c.get("status") == "approved"
        }
        ov_candidates = set(ov.get("approved_candidates") or [])
        if ov.get("decision") == "derived_from_approved_candidates":
            if not ov_candidates.issubset(approved_candidates | {"codex-derived-from-xal"}):
                extra = ov_candidates - approved_candidates
                if extra:
                    errors.append(
                        f"{feature_id!r}: overlay approved_candidates {sorted(extra)} "
                        f"not marked approved in inventory"
                    )
            continue
        if not ov_candidates:
            errors.append(f"overlay {feature_id!r} lists no approved_candidates")
            continue
        if not ov_candidates.issubset(approved_candidates):
            errors.append(
                f"{feature_id!r}: overlay candidates {sorted(ov_candidates)} "
                f"not all approved in inventory {sorted(approved_candidates)}"
            )

    for feature_id in inv_by_feature:
        if feature_id not in overlay_by_feature:
            errors.append(f"inventory feature {feature_id!r} missing from overlay-review.json")

    return errors
