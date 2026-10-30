"""Command-line interface."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core import ManifestError, RULES, RULE_PACKS, inspect_image, load_manifest, review, verify_images, resolve_rules, plan_review
from .policies import load_project_rules, match_project_rules

def emit(value, output=None):
    rendered = json.dumps(value, indent=2, ensure_ascii=False)
    if output: Path(output).write_text(rendered + "\n", encoding="utf-8")
    else: print(rendered)

def markdown_report(report):
    lines=[f"# Image Review: {report.get('status','UNKNOWN')}", "", f"Completeness: **{report.get('completeness','UNKNOWN')}**", "",
           f"Coverage: {report.get('coverage',{}).get('completed',0)}/{report.get('coverage',{}).get('required',0)} required checks passed", "",
           "| Rule | Feature | Status | Measured | Threshold |", "|---|---|---|---:|---:|"]
    for row in report.get("results",[]):
        lines.append(f"| {row.get('rule_id')} | {row.get('feature_id') or 'asset'} | {row.get('status')} | `{json.dumps(row.get('measured'),ensure_ascii=False)}` | `{json.dumps(row.get('threshold'),ensure_ascii=False)}` |")
    return "\n".join(lines)+"\n"

def main(argv=None):
    parser = argparse.ArgumentParser(prog="imreview", description="Deterministic image design constraint linter")
    subs = parser.add_subparsers(dest="command", required=True)
    inspect = subs.add_parser("inspect"); inspect.add_argument("image")
    manifest = subs.add_parser("manifest").add_subparsers(dest="manifest_command", required=True)
    validate = manifest.add_parser("validate"); validate.add_argument("manifest")
    delegate = subs.add_parser("delegate").add_subparsers(dest="delegate_command", required=True)
    preview = delegate.add_parser("preview"); preview.add_argument("--manifest"); preview.add_argument("--path", default=".")
    rules = delegate.add_parser("rules"); rules.add_argument("--manifest", required=True); rules.add_argument("--rules-file")
    packs = delegate.add_parser("packs"); packs.add_argument("--kind", choices=sorted(RULE_PACKS))
    rev = subs.add_parser("review"); rev.add_argument("--manifest", required=True); rev.add_argument("--output"); rev.add_argument("--rules-file")
    rev.add_argument("--format", choices=("json","markdown"), default="json")
    plan = subs.add_parser("plan"); plan.add_argument("--manifest",required=True); plan.add_argument("--rules-file")
    coverage = subs.add_parser("coverage"); coverage.add_argument("--report",required=True)
    explain = subs.add_parser("explain"); explain.add_argument("report")
    verify = subs.add_parser("verify"); verify.add_argument("--before", required=True); verify.add_argument("--after", required=True); verify.add_argument("--region", nargs=4, type=int, metavar=("X1","Y1","X2","Y2")); verify.add_argument("--report")
    diff = subs.add_parser("diff"); diff.add_argument("--before", required=True); diff.add_argument("--after", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect": emit(inspect_image(Path(args.image)))
        elif args.command == "manifest":
            data, _ = load_manifest(Path(args.manifest)); emit({"status":"VALID", "schema_version":data["schema_version"]})
        elif args.command == "delegate" and args.delegate_command == "rules":
            data, _ = load_manifest(Path(args.manifest)); selected=resolve_rules(data)
            registry={r["algorithm"]:r for r in RULES}
            result={"manifest_schema":data["schema_version"], "resolved_rules":[{**item, **registry.get(item["algorithm"],{})} for item in selected]}
            if args.rules_file:
                policies=load_project_rules(Path(args.rules_file)); matched=match_project_rules(data,policies)
                result["project_rules"]=[{"id":rule.id,"version":rule.version,"priority":rule.priority,"feature_id":feature,"algorithm":rule.algorithm.model_dump(),"assertion":rule.assertion.model_dump()} for rule,feature in matched]
            emit(result)
        elif args.command == "delegate" and args.delegate_command == "packs":
            emit({key:value for key,value in RULE_PACKS.items() if args.kind is None or key == args.kind})
        elif args.command == "delegate":
            if args.manifest:
                data,root=load_manifest(Path(args.manifest)); asset=Path(data["asset"]["path"])
                emit({"asset":{"path":str(asset),"exists":True},"intent":data.get("intent",{}),"features":[{"id":f["id"],"role":f["role"],"parent_id":f.get("parent_id")} for f in data.get("features",[])],"planned_checks":len(resolve_rules(data))})
            else:
                files = sorted(str(p) for p in Path(args.path).rglob("*") if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"})
                emit({"images":files})
        elif args.command == "plan":
            data,_=load_manifest(Path(args.manifest)); result=plan_review(data)
            if args.rules_file:
                policies=load_project_rules(Path(args.rules_file)); matched=match_project_rules(data,policies)
                result["project_rules"]=[{"id":rule.id,"feature_id":feature,"algorithm":rule.algorithm.id,"status":"PLANNED"} for rule,feature in matched]
            emit(result)
        elif args.command == "coverage":
            report=json.loads(Path(args.report).read_text(encoding="utf-8")); cov=report.get("coverage")
            if not isinstance(cov,dict): raise ManifestError("report has no coverage data")
            emit({"completeness":report.get("completeness"),**cov})
            if report.get("completeness")!="COMPLETE": return 1
        elif args.command == "review":
            data, root = load_manifest(Path(args.manifest)); project_rules=load_project_rules(Path(args.rules_file)) if args.rules_file else []
            result = review(data, root, project_rules)
            if args.format=="markdown":
                rendered=markdown_report(result)
                if args.output: Path(args.output).write_text(rendered,encoding="utf-8")
                else: print(rendered,end="")
            else: emit(result, args.output)
            if result["status"] != "PASS" or result["completeness"]!="COMPLETE": return 1
        elif args.command in {"verify", "diff"}:
            region=tuple(args.region) if args.command=="verify" and args.region else None
            allowed_mask=None
            if args.command=="verify" and args.report:
                source=json.loads(Path(args.report).read_text(encoding="utf-8"))
                if region is None and source.get("allowed_region"): region=tuple(source["allowed_region"])
                if source.get("allowed_mask"): allowed_mask=Path(source["allowed_mask"])
            result = verify_images(Path(args.before), Path(args.after), region, allowed_mask); emit(result)
            if result["status"] != "PASS": return 1
        elif args.command == "explain":
            report = json.loads(Path(args.report).read_text(encoding="utf-8"))
            print(f"Overall: {report.get('status', 'UNKNOWN')}")
            for item in report.get("results", []):
                print(f"{item.get('status')} {item.get('rule_id')} feature={item.get('feature_id')} measured={item.get('measured')} threshold={item.get('threshold')} region={item.get('region')} formula={item.get('formula')}")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status":"INVALID_INPUT", "error":str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == "__main__": raise SystemExit(main())
