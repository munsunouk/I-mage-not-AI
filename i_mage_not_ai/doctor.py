"""Preflight checks for CLI and optional Skill fox trial artifacts."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .game import (
    aggregate_game_gate,
    analyze_runtime_evidence,
    load_runtime_evidence,
    load_runtime_policy,
    load_trace,
    validate_event_bridge,
    validate_input_binding,
    validate_policy,
)
from .render_evidence import analyze_render_evidence, load_render_evidence, validate_render_policy

FIXTURE_SCENARIO_ID = "integration-fixture-walk-v1"
FIXTURE_EVIDENCE_RUN_ID = "integration-fixture-run-001"


def _check(name: str, ok: bool, detail: str, *, required: bool = True) -> dict[str, Any]:
    return {"name": name, "ok": ok, "required": required, "detail": detail}


_GAME_FIXTURE_SPEC: dict[str, dict[str, Any]] = {
    "godot": {
        "export": "i_mage_not_ai-godot-export.json",
        "files": [
            "policy.json",
            "review.json",
            "runtime-evidence.json",
            "runtime-policy.json",
            "runtime-review.json",
            "render-policy.json",
            "render-evidence.json",
            "render-review.json",
            "event-bridge.json",
            "input-binding.json",
        ],
    },
    "unity": {
        "export": "i_mage_not_ai-unity-export.json",
        "files": [
            "policy.json",
            "review.json",
            "i_mage_not_ai-unity-runtime-evidence.json",
            "runtime-policy.json",
            "runtime-review.json",
            "render-policy.json",
            "render-evidence.json",
            "render-review.json",
            "event-bridge.json",
            "input-binding.json",
        ],
    },
}


def _report_contract(report: dict[str, Any], expected_type: str) -> str | None:
    if report.get("asset_type") != expected_type:
        return f"expected asset_type={expected_type}, got {report.get('asset_type')!r}"
    if report.get("status") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
        return "missing status"
    if report.get("completeness") not in {"COMPLETE", "INCOMPLETE"}:
        return "missing completeness"
    scenario = report.get("scenario_id")
    if not isinstance(scenario, str) or scenario.strip() != FIXTURE_SCENARIO_ID:
        return f"scenario_id must be {FIXTURE_SCENARIO_ID!r}"
    run_id = report.get("evidence_run_id")
    if not isinstance(run_id, str) or run_id.strip() != FIXTURE_EVIDENCE_RUN_ID:
        return f"evidence_run_id must be {FIXTURE_EVIDENCE_RUN_ID!r}"
    return None


def _check_game_fixture_engine(root: Path, engine: str, spec: dict[str, Any]) -> dict[str, Any]:
    fixture_dir = root / "integration-fixtures" / engine
    name = f"game_fixture_{engine}"
    if not fixture_dir.is_dir():
        return _check(name, False, f"missing directory {fixture_dir.relative_to(root)}", required=False)
    missing = [rel for rel in spec["files"] if not (fixture_dir / rel).is_file()]
    export_path = fixture_dir / spec["export"]
    if not export_path.is_file():
        missing.append(str(Path("integration-fixtures") / engine / spec["export"]))
    frame_dir = fixture_dir / "render-evidence_frames"
    if "render-evidence.json" in spec["files"] and (not frame_dir.is_dir() or not any(frame_dir.glob("*.png"))):
        missing.append("render-evidence_frames/*.png")
    if missing:
        return _check(name, False, f"missing: {', '.join(missing)}", required=False)
    details: list[str] = []
    try:
        load_trace(export_path)
        details.append("trace export loads")
    except ValueError as exc:
        return _check(name, False, f"trace export invalid: {exc}", required=False)
    try:
        validate_policy(json.loads((fixture_dir / "policy.json").read_text(encoding="utf-8")))
        load_runtime_policy(fixture_dir / "runtime-policy.json")
        runtime_path = fixture_dir / (
            "runtime-evidence.json" if engine == "godot" else "i_mage_not_ai-unity-runtime-evidence.json"
        )
        runtime_bundle = load_runtime_evidence(runtime_path)
        runtime_policy = load_runtime_policy(fixture_dir / "runtime-policy.json")
        analyze_runtime_evidence(runtime_bundle, runtime_policy)
        details.append("runtime evidence/policy analyze")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return _check(name, False, f"runtime fixture invalid: {exc}", required=False)
    if (fixture_dir / "render-evidence.json").is_file():
        try:
            render_bundle, _ = load_render_evidence(fixture_dir / "render-evidence.json")
            render_policy = validate_render_policy(
                json.loads((fixture_dir / "render-policy.json").read_text(encoding="utf-8"))
            )
            render_report = analyze_render_evidence(render_bundle, render_policy)
            if (render_report["status"], render_report["completeness"]) != ("PASS", "COMPLETE"):
                return _check(name, False, "render analyze must PASS/COMPLETE for fixture bundle", required=False)
            details.append("render evidence/policy analyze")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            return _check(name, False, f"render fixture invalid: {exc}", required=False)
    reports: dict[str, dict[str, Any]] = {}
    try:
        reports["game_trace"] = json.loads((fixture_dir / "review.json").read_text(encoding="utf-8"))
        reports["runtime_evidence"] = json.loads((fixture_dir / "runtime-review.json").read_text(encoding="utf-8"))
        for label, expected in (("game_trace", "game_trace"), ("runtime_evidence", "runtime_evidence")):
            err = _report_contract(reports[label], expected)
            if err:
                return _check(name, False, f"{label} report: {err}", required=False)
        if (fixture_dir / "render-review.json").is_file():
            reports["render_evidence"] = json.loads((fixture_dir / "render-review.json").read_text(encoding="utf-8"))
            err = _report_contract(reports["render_evidence"], "render_evidence")
            if err:
                return _check(name, False, f"render report: {err}", required=False)
            bridge = validate_event_bridge(json.loads((fixture_dir / "event-bridge.json").read_text(encoding="utf-8")))
            binding = validate_input_binding(json.loads((fixture_dir / "input-binding.json").read_text(encoding="utf-8")))
            gate = aggregate_game_gate(
                reports["game_trace"],
                reports["runtime_evidence"],
                reports["render_evidence"],
                require_evidence_run_id=True,
                event_bridge=bridge,
                require_event_bridge=True,
                input_binding=binding,
                require_input_digests=True,
                require_state_join=True,
            )
            if (gate["status"], gate["completeness"]) != ("PASS", "COMPLETE"):
                return _check(name, False, f"game gate dry-run: {gate['status']}/{gate['completeness']}", required=False)
            details.append("game gate dry-run PASS")
    except (OSError, json.JSONDecodeError) as exc:
        return _check(name, False, f"fixture reports invalid: {exc}", required=False)
    return _check(name, True, "; ".join(details) if details else "fixture files present", required=False)


def run_doctor(
    repo_root: Path | None = None,
    *,
    skill_trial: bool = False,
    game_fixture: bool = False,
) -> dict[str, Any]:
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
        for schema_name in (
            "game-trace.schema.json",
            "runtime-evidence.schema.json",
            "render-evidence.schema.json",
            "game-policy.schema.json",
            "runtime-policy.schema.json",
            "render-policy.schema.json",
            "game-evidence-report.schema.json",
            "game-gate.schema.json",
        ):
            path = root / "schemas" / schema_name
            checks.append(
                _check(
                    f"schema_{schema_name.replace('.schema.json', '').replace('-', '_')}",
                    path.is_file(),
                    str(path) if path.is_file() else f"missing {path}",
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

    if game_fixture:
        if root is None:
            checks.append(
                _check("game_fixture_paths", False, "pass --repo-root for --game-fixture checks")
            )
        else:
            for engine, spec in _GAME_FIXTURE_SPEC.items():
                checks.append(_check_game_fixture_engine(root, engine, spec))

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
