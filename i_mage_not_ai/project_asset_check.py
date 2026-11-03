"""Required asset path/glob completeness against a bounded directory walk."""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from .project_discovery import _relative, _walk


def validate_asset_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict) or not policy:
        raise ValueError("asset policy must be a non-empty object")
    if "required_paths" not in policy and "required_globs" not in policy:
        raise ValueError("asset policy must include required_paths and/or required_globs")
    for key in ("required_paths", "required_globs", "optional_paths"):
        if key not in policy:
            continue
        value = policy[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise ValueError(f"{key} must be a non-empty list of path strings")
    return policy


def _collect_files(root: Path, *, max_files: int, max_depth: int) -> tuple[set[str], dict[str, Any]]:
    files, _, traversal = _walk(root, max_files, max_depth)
    rel_paths = {_relative(path, root) for path in files}
    return rel_paths, traversal


def check_project_assets(
    scan_root: Path,
    policy: Any,
    *,
    max_files: int = 20_000,
    max_depth: int = 16,
) -> dict[str, Any]:
    validate_asset_policy(policy)
    root = scan_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"scan root is not a directory: {root}")
    project_rel = policy.get("project_root", ".")
    project_path = (root / project_rel).resolve() if project_rel != "." else root
    if not project_path.is_dir() or not project_path.is_relative_to(root):
        raise ValueError("project_root must be a directory inside the scan root")

    rel_files, traversal = _collect_files(project_path, max_files=max_files, max_depth=max_depth)
    missing_paths: list[str] = []
    for item in policy.get("required_paths", []):
        normalized = Path(item).as_posix()
        if normalized not in rel_files:
            missing_paths.append(normalized)

    missing_globs: list[dict[str, str]] = []
    for pattern in policy.get("required_globs", []):
        matches = sorted(path for path in rel_files if fnmatch.fnmatch(path, pattern))
        if not matches:
            missing_globs.append({"pattern": pattern, "matches": []})

    optional_missing = [
        path for path in policy.get("optional_paths", []) if Path(path).as_posix() not in rel_files
    ]

    findings: list[dict[str, Any]] = []
    if policy.get("required_paths"):
        status = "PASS" if not missing_paths else "FAIL"
        findings.append(
            {
                "rule_id": "PROJECT-REQUIRED-PATHS",
                "algorithm": "project_required_paths",
                "status": status,
                "measured": {"missing": missing_paths, "required_count": len(policy["required_paths"])},
                "threshold": {"all_required_paths_present": True},
                "formula": "each required_paths entry must exist as a file under project_root",
            }
        )
    if policy.get("required_globs"):
        status = "PASS" if not missing_globs else "FAIL"
        findings.append(
            {
                "rule_id": "PROJECT-REQUIRED-GLOBS",
                "algorithm": "project_required_globs",
                "status": status,
                "measured": {"unsatisfied_globs": missing_globs, "required_glob_count": len(policy["required_globs"])},
                "threshold": {"each_glob_has_at_least_one_match": True},
                "formula": "each required_globs pattern must match at least one file",
            }
        )

    complete = bool(findings) and all(row["status"] in {"PASS", "FAIL"} for row in findings)
    status = "FAIL" if any(row["status"] == "FAIL" for row in findings) else ("PASS" if complete else "INCONCLUSIVE")
    scan_incomplete = not traversal["complete"]
    if scan_incomplete and status == "PASS":
        status = "INCONCLUSIVE"
    return {
        "schema_version": "0.5",
        "asset_type": "project_assets",
        "status": status,
        "completeness": "COMPLETE" if complete and not scan_incomplete else "INCOMPLETE",
        "project_root": _relative(project_path, root) if project_path != root else ".",
        "scan_root": str(root),
        "limits": {"max_files": max_files, "max_depth": max_depth},
        "coverage": {
            "required": len(findings),
            "completed": sum(row["status"] in {"PASS", "FAIL"} for row in findings),
            "missing": [row["rule_id"] for row in findings if row["status"] not in {"PASS", "FAIL"}],
            "scan_complete": traversal["complete"],
            "files_seen": len(rel_files),
        },
        "optional_paths_missing": optional_missing,
        "results": findings,
    }
