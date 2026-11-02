"""Run the Skill image workflow (plan → review_intent → review --plan)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
CLI = [sys.executable, "-m", "i_mage_not_ai"]
MANIFEST = OUT / "manifest.json"
SOURCE = OUT / "fox-forest.png"
RULES = OUT / "rules.yaml"
PLAN = OUT / "review-plan.json"
REPORT = OUT / "review.json"

THRESHOLD_SOURCE = "artifacts/skill-segmentation-test/manifest.json (feature properties and overlap_constraints)"


def run_step(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run([*CLI, *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    (OUT / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (OUT / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    return completed


def attach_review_intent(plan_path: Path) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    checks = plan.get("execution_plan", plan).get("checks", plan.get("checks", []))
    plan["review_intent"] = [
        {
            "rule_id": check["rule_id"],
            "purpose": (
                f"Confirm declared constraint {check['rule_id']} "
                f"({check.get('algorithm', 'unknown')}) for the fox-forest skill trial."
            ),
            "threshold_source": THRESHOLD_SOURCE,
        }
        for check in checks
    ]
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    steps: list[tuple[str, list[str]]] = [
        ("inspect", ["inspect", str(SOURCE.relative_to(REPO))]),
        ("manifest_validate", ["manifest", "validate", str(MANIFEST.relative_to(REPO))]),
        ("delegate_preview", ["delegate", "preview", "--manifest", str(MANIFEST.relative_to(REPO))]),
        ("delegate_rules", ["delegate", "rules", "--manifest", str(MANIFEST.relative_to(REPO)), "--rules-file", str(RULES.relative_to(REPO))]),
        ("plan", ["plan", "--manifest", str(MANIFEST.relative_to(REPO)), "--rules-file", str(RULES.relative_to(REPO)), "--output", str(PLAN.relative_to(REPO))]),
    ]
    results: list[dict] = []
    for name, args in steps:
        completed = run_step(name, args)
        results.append({"step": name, "argv": [*CLI, *args], "exit_code": completed.returncode})
        if completed.returncode != 0:
            break

    if results and results[-1]["exit_code"] == 0:
        attach_review_intent(PLAN)
        (OUT / "plan_with_intent.stdout.txt").write_text(PLAN.read_text(encoding="utf-8"), encoding="utf-8")
        for name, args in (
            ("review", ["review", "--manifest", str(MANIFEST.relative_to(REPO)), "--rules-file", str(RULES.relative_to(REPO)), "--plan", str(PLAN.relative_to(REPO)), "--output", str(REPORT.relative_to(REPO))]),
            ("coverage", ["coverage", "--report", str(REPORT.relative_to(REPO))]),
            ("explain", ["explain", str(REPORT.relative_to(REPO))]),
        ):
            completed = run_step(name, args)
            results.append({"step": name, "argv": [*CLI, *args], "exit_code": completed.returncode})
            if completed.returncode != 0:
                break

    (OUT / "cli-run.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(row["exit_code"] not in (0, 1, 2) for row in results):
        raise SystemExit(1)
    if results and results[-1]["exit_code"] not in (0, 1, 2):
        raise SystemExit(results[-1]["exit_code"])


if __name__ == "__main__":
    main()
