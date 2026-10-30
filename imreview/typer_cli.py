"""Native Typer command interface for imreview."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import typer
from .core import RULES, RULE_PACKS, inspect_image, load_manifest, review as run_review, verify_images, resolve_rules, plan_review
from .policies import load_project_rules, match_project_rules
from .game import load_trace, load_policy, analyze_trace
from .benchmark import score_files, generate_synthetic_dataset, create_submission_template, verify_synthetic_submission, update_leaderboard, render_gallery

app=typer.Typer(no_args_is_help=True,help="Deterministic image design constraint linter")
manifest_app=typer.Typer(no_args_is_help=True)
delegate_app=typer.Typer(no_args_is_help=True)
game_app=typer.Typer(no_args_is_help=True,help="Analyze engine-exported game traces (never runs engine code)")
benchmark_app=typer.Typer(no_args_is_help=True,help="Score labeled benchmark findings")
app.add_typer(manifest_app,name="manifest")
app.add_typer(delegate_app,name="delegate")
app.add_typer(game_app,name="game")
app.add_typer(benchmark_app,name="benchmark")

def emit(data, output: Optional[Path]=None):
    rendered=json.dumps(data,indent=2,ensure_ascii=False)
    if output: output.write_text(rendered+"\n",encoding="utf-8")
    else: typer.echo(rendered)

def fail(exc: Exception):
    typer.echo(json.dumps({"status":"INVALID_INPUT","error":str(exc)},ensure_ascii=False),err=True)
    raise typer.Exit(2)

@benchmark_app.command("score")
def benchmark_score(ground_truth: Path=typer.Option(...,"--ground-truth"),predictions: Path=typer.Option(...,"--predictions"),output: Optional[Path]=typer.Option(None,"--output")):
    """Compute rule-level precision, recall and F1 for one dataset version."""
    try: emit(score_files(ground_truth,predictions),output)
    except (ValueError,OSError,json.JSONDecodeError) as exc: fail(exc)

@benchmark_app.command("generate-synthetic")
def benchmark_generate_synthetic(output_dir: Path=typer.Option(...,"--output-dir"),count: int=typer.Option(20,"--count",min=1,max=1000)):
    """Generate deterministic synthetic flat-icon cases with injected palette faults."""
    try: emit(generate_synthetic_dataset(output_dir,count))
    except (ValueError,OSError) as exc: fail(exc)

@benchmark_app.command("evaluate")
def benchmark_evaluate(dataset: Path=typer.Option(...,"--dataset"),submission: Path=typer.Option(...,"--submission"),output: Optional[Path]=typer.Option(None,"--output")):
    """Independently measure and score a three-track synthetic comparison."""
    try:
        emit(verify_synthetic_submission(dataset,submission),output)
    except (ValueError,OSError,json.JSONDecodeError) as exc: fail(exc)

@benchmark_app.command("init-submission")
def benchmark_init_submission(dataset: Path=typer.Option(...,"--dataset"),output: Path=typer.Option(...,"--output")):
    """Create a three-track submission skeleton for a benchmark dataset."""
    try:
        submission=create_submission_template(dataset,output)
        emit({"status":"CREATED","path":str(output),"case_count":len(submission["tracks"]["agent_only"]["assets"])})
    except (ValueError,OSError,json.JSONDecodeError) as exc: fail(exc)

@benchmark_app.command("leaderboard-add")
def benchmark_leaderboard_add(result: Path=typer.Option(...,"--result"),leaderboard: Path=typer.Option(...,"--leaderboard"),run_id: str=typer.Option(...,"--run-id")):
    """Add a verified synthetic evaluation to its version-specific local board."""
    try: emit(update_leaderboard(leaderboard,json.loads(result.read_text(encoding="utf-8")),run_id))
    except (ValueError,OSError,json.JSONDecodeError) as exc: fail(exc)

@benchmark_app.command("gallery")
def benchmark_gallery(dataset: Path=typer.Option(...,"--dataset"),submission: Path=typer.Option(...,"--submission"),result: Path=typer.Option(...,"--result"),output: Path=typer.Option(...,"--output")):
    """Create a static, local before/after report for a verified synthetic run."""
    try: emit({"status":"CREATED","path":str(render_gallery(dataset,submission,result,output))})
    except (ValueError,OSError,json.JSONDecodeError) as exc: fail(exc)

def markdown_report(report):
    lines=[f"# Image Review: {report.get('status','UNKNOWN')}","",f"Completeness: **{report.get('completeness','UNKNOWN')}**","",
           f"Coverage: {report.get('coverage',{}).get('completed',0)}/{report.get('coverage',{}).get('required',0)} required checks completed","",
           "| Rule | Feature | Status | Measured | Threshold |","|---|---|---|---:|---:|"]
    for row in report.get("results",[]):
        lines.append(f"| {row.get('rule_id')} | {row.get('feature_id') or 'asset'} | {row.get('status')} | `{json.dumps(row.get('measured'),ensure_ascii=False)}` | `{json.dumps(row.get('threshold'),ensure_ascii=False)}` |")
    return "\n".join(lines)+"\n"

@app.command("inspect")
def inspect_asset(asset: Path):
    try: emit(inspect_image(asset))
    except (ValueError,OSError) as exc: fail(exc)

@manifest_app.command("validate")
def validate_manifest(manifest: Path):
    try:
        data,_=load_manifest(manifest); emit({"status":"VALID","schema_version":data["schema_version"]})
    except (ValueError,OSError) as exc: fail(exc)

@delegate_app.command("preview")
def preview(manifest: Optional[Path]=typer.Option(None,"--manifest"), path: Path=typer.Option(Path("."),"--path")):
    try:
        if manifest:
            data,_=load_manifest(manifest)
            emit({"asset":{"path":data["asset"]["path"],"exists":True},"intent":data.get("intent",{}),"features":[{"id":f["id"],"role":f["role"],"parent_id":f.get("parent_id")} for f in data.get("features",[])],"planned_checks":len(resolve_rules(data))})
        else:
            files=sorted(str(p) for p in path.rglob("*") if p.is_file() and p.suffix.lower() in {".png",".jpg",".jpeg",".webp",".svg"})
            emit({"images":files})
    except (ValueError,OSError) as exc: fail(exc)

@delegate_app.command("rules")
def rules(manifest: Path=typer.Option(...,"--manifest"),rules_file: Optional[Path]=typer.Option(None,"--rules-file")):
    try:
        data,_=load_manifest(manifest); selected=resolve_rules(data); registry={r["algorithm"]:r for r in RULES}
        result={"manifest_schema":data["schema_version"],"resolved_rules":[{**x,**registry.get(x["algorithm"],{})} for x in selected]}
        if rules_file:
            matched=match_project_rules(data,load_project_rules(rules_file))
            result["project_rules"]=[{"id":r.id,"version":r.version,"priority":r.priority,"feature_id":f,"algorithm":r.algorithm.model_dump(),"assertion":r.assertion.model_dump()} for r,f in matched]
        emit(result)
    except (ValueError,OSError) as exc: fail(exc)

@delegate_app.command("packs")
def packs(kind: Optional[str]=typer.Option(None,"--kind")):
    if kind and kind not in RULE_PACKS: raise typer.BadParameter(f"unknown pack {kind}; choose from {', '.join(RULE_PACKS)}")
    emit({key:value for key,value in RULE_PACKS.items() if kind is None or key==kind})

@app.command("plan")
def plan(manifest: Path=typer.Option(...,"--manifest"),rules_file: Optional[Path]=typer.Option(None,"--rules-file")):
    try:
        data,_=load_manifest(manifest); result=plan_review(data)
        if rules_file:
            matched=match_project_rules(data,load_project_rules(rules_file))
            result["project_rules"]=[{"id":r.id,"feature_id":f,"algorithm":r.algorithm.id,"status":"PLANNED"} for r,f in matched]
        emit(result)
        if result["status"]!="READY": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)

@app.command("review")
def review(manifest: Path=typer.Option(...,"--manifest"),output: Optional[Path]=typer.Option(None,"--output"),output_format: str=typer.Option("json","--format"),rules_file: Optional[Path]=typer.Option(None,"--rules-file")):
    if output_format not in {"json","markdown"}: raise typer.BadParameter("--format must be json or markdown")
    try:
        data,root=load_manifest(manifest); policies=load_project_rules(rules_file) if rules_file else []
        result=run_review(data,root,policies)
        rendered=markdown_report(result) if output_format=="markdown" else json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if output: output.write_text(rendered,encoding="utf-8")
        else: typer.echo(rendered.rstrip("\n"))
        if result["status"]!="PASS" or result["completeness"]!="COMPLETE": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)

@app.command("coverage")
def coverage(report: Path=typer.Option(...,"--report")):
    try:
        data=json.loads(report.read_text(encoding="utf-8")); cov=data.get("coverage")
        if not isinstance(cov,dict): raise ValueError("report has no coverage data")
        emit({"completeness":data.get("completeness"),**cov})
        if data.get("completeness")!="COMPLETE": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)

@app.command("explain")
def explain(report: Path):
    try:
        data=json.loads(report.read_text(encoding="utf-8")); typer.echo(f"Overall: {data.get('status','UNKNOWN')}")
        for row in data.get("results",[]): typer.echo(f"{row.get('status')} {row.get('rule_id')} feature={row.get('feature_id')} measured={row.get('measured')} threshold={row.get('threshold')} region={row.get('region')} formula={row.get('formula')}")
    except (ValueError,OSError) as exc: fail(exc)

@app.command("verify")
def verify(before: Path=typer.Option(...,"--before"),after: Path=typer.Option(...,"--after"),report: Optional[Path]=typer.Option(None,"--report"),region: Optional[tuple[int,int,int,int]]=typer.Option(None,"--region")):
    try:
        allowed_mask=None
        if report:
            data=json.loads(report.read_text(encoding="utf-8"))
            if region is None and data.get("allowed_region"): region=tuple(data["allowed_region"])
            if data.get("allowed_mask"): allowed_mask=Path(data["allowed_mask"])
        result=verify_images(before,after,region,allowed_mask); emit(result)
        if result["status"]!="PASS": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)

@app.command("diff")
def diff(before: Path=typer.Option(...,"--before"),after: Path=typer.Option(...,"--after")):
    try:
        result=verify_images(before,after); emit(result)
        if result["status"]!="PASS": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)

@game_app.command("analyze")
def analyze_game_trace(trace: Path=typer.Option(...,"--trace"),policy: Optional[Path]=typer.Option(None,"--policy"),output: Optional[Path]=typer.Option(None,"--output")):
    try:
        game_trace=load_trace(trace); constraints=load_policy(policy)
        result=analyze_trace(game_trace,constraints,trace.resolve().parent); emit(result,output)
        if result["status"]!="PASS" or result["completeness"]!="COMPLETE": raise typer.Exit(1)
    except (ValueError,OSError) as exc: fail(exc)
