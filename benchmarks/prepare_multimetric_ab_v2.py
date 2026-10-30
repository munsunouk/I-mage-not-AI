"""Package the same blind task, fixed policies, CLI preflight and clean controls."""
from __future__ import annotations
import json, random, shutil, subprocess, sys
from pathlib import Path
from PIL import Image
from prepare_multimetric_icon_dataset_v2 import DATA, RULES, policy, sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"benchmarks/results/icon-multimetric-isolated-loop-05"

def run_review(manifest:Path,output:Path)->dict:
    output.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([sys.executable,"-m","i_mage_not_ai","review","--manifest",str(manifest),"--output",str(output)],cwd=ROOT,capture_output=True,text=True)
    if result.returncode not in (0,1,2) or not output.is_file(): raise RuntimeError(f"CLI failed: {manifest}: {result.stderr}")
    return json.loads(output.read_text(encoding="utf-8"))

def write(path:Path,obj:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")

def main()->None:
    ds=json.loads((DATA/"dataset.json").read_text(encoding="utf-8"));cases=ds["cases"]
    ordered=list(cases);random.Random(72031).shuffle(ordered); specs={}
    for arm in ("agent-only","agent-cli"):
        base=OUT/"sessions"/arm;(base/"inputs").mkdir(parents=True,exist_ok=True);(base/"outputs").mkdir(exist_ok=True)
        task="""# Icon audit repair task v2

You have 24 randomized 128x128 RGBA icons. They include clean examples, single faults and compound faults; some are AI-generated game icons. For each: inspect image and manifest, identify every registered failure, return rule IDs with concise evidence, and make one repair attempt only when a defect is supported. Leave clean icons untouched. Save one PNG per case and structured decisions.json with sample ID, diagnosed rule IDs, evidence and action. Keep edits targeted. Do not inspect clean references, evaluator files, or the other arm folder. Thresholds are shared by clean/single/compound variants of each source design.

The supplied mask is for the visible silhouette only; there are no semantic part masks. For the generated icons, only alpha centroid/margins, whole-image exact palette and silhouette connectivity/occupancy/bounds are available. Do not claim a semantic, symmetry, overlap, masked color, aesthetic or prompt-faithfulness check without evidence for it.
"""
        if arm=="agent-only":task+="\nCondition: visual reasoning only. Do not run CLI, scripts, numerical measurement or another diagnostic tool.\n"
        else:task+="\nCondition: before diagnosis or edit, run `.venv/Scripts/python.exe -m i_mage_not_ai review --manifest <sample manifest> --output <outputs/cli-reports/sample-NN.json>`. Use saved JSON plus visual inspection; save all 24 complete reports.\n"
        (base/"task-spec.md").write_text(task,encoding="utf-8");specs[arm]={}
        for i,row in enumerate(ordered,1):
            sid=f"sample-{i:02d}";inp=base/"inputs"/sid;(inp/"masks").mkdir(parents=True,exist_ok=True)
            shutil.copyfile(DATA/row["faulty_asset"],inp/"asset.png");shutil.copyfile(DATA/row["mask"],inp/"masks/silhouette.png")
            m=policy(sha(inp/"asset.png"),row["thresholds"],"masks/silhouette.png");write(inp/"manifest.json",m)
            specs[arm][sid]={"case_id":row["case_id"],"condition":row["condition"],"kind":row["kind"],"expected_rules":row["expected_rules"],"sha256":row["input_sha256"],"clean_asset":row["clean_asset"],"clean_sha256":row["clean_sha256"],"thresholds":row["thresholds"]}
            if arm=="agent-cli":
                report=run_review(inp/"manifest.json",base/"outputs/cli-reports"/(sid+".json"))
                found=sorted({x["rule_id"] for x in report["results"] if x["status"]=="FAIL"});expected=sorted(row["expected_rules"])
                if report.get("completeness")!="COMPLETE" or found!=expected:raise RuntimeError(f"preflight mismatch {sid}: expected {expected}; got {found}")
    controls=[]
    for kind in sorted({x["kind"] for x in cases}):
        row=next(x for x in cases if x["kind"]==kind and x["condition"]=="normal");p=OUT/"evaluator/clean-controls"/kind;(p/"masks").mkdir(parents=True,exist_ok=True)
        shutil.copyfile(DATA/row["clean_asset"],p/"asset.png");shutil.copyfile(DATA/row["mask"],p/"masks/silhouette.png")
        write(p/"manifest.json",policy(sha(p/"asset.png"),row["thresholds"],"masks/silhouette.png"))
        r=run_review(p/"manifest.json",p/"report.json")
        if r.get("completeness")!="COMPLETE" or any(x["status"]!="PASS" for x in r["results"]):raise RuntimeError(f"clean control failed {kind}")
        controls.append(kind)
    write(OUT/"evaluator/ground-truth-map.json",{"samples":specs["agent-only"]})
    write(OUT/"protocol.json",{"version":"2.0.0","samples":24,"clean_controls_preflighted":controls,"conditions":sorted(RULES),"same_randomized_inputs":True,"fault_label_dependent_thresholds":False,"agent_diagnosis_scored_from_same_structured_output":True,"filesystem_isolation":"procedural only; not OS-enforced","human_quality_ratings":"not yet collected"})
    write(OUT/"evaluator/preflight-summary.json",{"cases":24,"by_condition":{c:sum(x["condition"]==c for x in cases) for c in RULES},"input_cli_reports_complete":24,"preflight_matches_expected_rules":True,"all_clean_controls_pass":len(controls)})
    print(json.dumps({"output":str(OUT),"cases":24,"conditions":{c:sum(x["condition"]==c for x in cases) for c in RULES},"controls":controls,"cli_reports":24},indent=2))

if __name__=="__main__":main()
