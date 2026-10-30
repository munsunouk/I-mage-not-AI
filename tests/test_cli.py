import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from imreview.core import _delta_e_2000


class CliWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = Image.new("RGBA", (8, 8), (255, 255, 255, 255))
        self.image.save(self.root / "asset.png")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(["imreview", *map(str, args)], capture_output=True, text=True)

    def write_manifest(self, doc):
        path = self.root / "manifest.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def base(self, constraints=None, features=None):
        return {"schema_version":"0.1", "asset":{"path":"asset.png"},
                "constraints":constraints or {}, "features":features or []}

    def test_manifest_review_and_explain(self):
        manifest = self.write_manifest(self.base({"max_palette_colors":1}))
        self.assertEqual(self.run_cli("manifest", "validate", manifest).returncode, 0)
        rules = json.loads(self.run_cli("delegate", "rules", "--manifest", manifest).stdout)
        self.assertEqual(rules["resolved_rules"][1]["algorithm"], "exact_palette_count")
        report = self.root / "report.json"
        self.assertEqual(self.run_cli("review", "--manifest", manifest, "--output", report).returncode, 0)
        result=json.loads(report.read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completeness"], "COMPLETE")
        self.assertEqual(json.loads(self.run_cli("plan","--manifest",manifest).stdout)["status"],"READY")
        self.assertEqual(json.loads(self.run_cli("coverage","--report",report).stdout)["completeness"],"COMPLETE")
        self.assertEqual(self.run_cli("review","--manifest",manifest,"--format","markdown").returncode,0)
        repeat=json.loads(self.run_cli("review","--manifest",manifest).stdout)
        self.assertEqual(result,repeat)
        self.assertEqual(self.run_cli("explain", report).returncode, 0)

    def test_plan_reports_feature_adapter(self):
        Image.new("L",(8,8),255).save(self.root/"mask.png")
        manifest=self.write_manifest(self.base(features=[
            {"id":"fg","role":"foreground","geometry":{"type":"mask","path":"mask.png"},"properties":{"max_palette_colors":1}}]))
        plan=json.loads(self.run_cli("plan","--manifest",manifest).stdout)
        self.assertEqual(plan["status"],"READY")
        feature_check=next(check for check in plan["checks"] if check["feature_id"]=="fg")
        self.assertIn("raster_mask",feature_check["feature_adapter_ids"])

    def test_verify_uses_allowed_region_from_report(self):
        doc=self.base(); doc["regression"]={"allowed_region":[2,2,6,6]}
        manifest=self.write_manifest(doc); report=self.root/"report.json"
        self.run_cli("review","--manifest",manifest,"--output",report)
        edited=self.image.copy(); edited.putpixel((3,3),(0,0,0,255)); edited.save(self.root/"edited.png")
        result=self.run_cli("verify","--before",self.root/"asset.png","--after",self.root/"edited.png","--report",report)
        self.assertEqual(result.returncode,0)

    def test_verify_uses_allowed_pixel_mask_from_report(self):
        mask=Image.new("L",(8,8),0); mask.putpixel((3,3),255); mask.save(self.root/"edit-mask.png")
        doc=self.base(); doc["regression"]={"allowed_mask":"edit-mask.png"}
        manifest=self.write_manifest(doc); report=self.root/"report.json"
        self.run_cli("review","--manifest",manifest,"--output",report)
        edited=self.image.copy(); edited.putpixel((3,3),(0,0,0,255)); edited.save(self.root/"edited.png")
        result=self.run_cli("verify","--before",self.root/"asset.png","--after",self.root/"edited.png","--report",report)
        self.assertEqual(result.returncode,0)

    def test_hash_mismatch_is_invalid_manifest(self):
        manifest=self.write_manifest({"schema_version":"0.5","asset":{"path":"asset.png","sha256":"0"*64},"features":[]})
        result=self.run_cli("manifest","validate",manifest)
        self.assertEqual(result.returncode,2)
        self.assertIn("SHA-256",result.stderr)

    def test_mask_resolution_and_external_svg_safety(self):
        Image.new("L",(4,4),255).save(self.root/"wrong-mask.png")
        doc=self.base(features=[{"id":"fg","role":"foreground","geometry":{"type":"mask","path":"wrong-mask.png"}}])
        manifest=self.write_manifest(doc)
        result=self.run_cli("manifest","validate",manifest)
        self.assertEqual(result.returncode,2)
        (self.root/"external.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png"/></svg>')
        result=self.run_cli("inspect",self.root/"external.svg")
        self.assertEqual(result.returncode,2)

    def test_project_yaml_rule_resolution_and_conflict(self):
        doc=self.base(); doc["intent"]={"type":"icon","style":"flat"}
        Image.new("L",(8,8),255).save(self.root/"fg.png")
        doc["features"]=[{"id":"fg","role":"foreground","geometry":{"type":"mask","path":"fg.png"}}]
        manifest=self.write_manifest(doc)
        rule='''schema_version: '1'\nrules:\n  - id: P1\n    version: '1'\n    priority: 10\n    match: {asset_type: icon, feature_role: foreground}\n    algorithm: {id: quantized_palette_count, version: '1', parameters: {bin_size: [10,10,10]}}\n    assertion: {operator: less_than_or_equal, value: 0, origin: project_config}\n'''
        rule_path=self.root/"rules.yaml"; rule_path.write_text(rule)
        resolved=json.loads(self.run_cli("delegate","rules","--manifest",manifest,"--rules-file",rule_path).stdout)
        self.assertEqual(resolved["project_rules"][0]["id"],"P1")
        review=self.run_cli("review","--manifest",manifest,"--rules-file",rule_path)
        report=json.loads(review.stdout)
        self.assertEqual(review.returncode,1) # the one-color fixture exceeds the explicit limit of zero colors
        self.assertEqual(next(r for r in report["results"] if r["rule_id"]=="P1")["status"],"FAIL")
        second=rule.replace("P1","P2").replace("value: 0","value: 4")
        rule_path.write_text("schema_version: '1'\nrules:\n"+rule.split("rules:\n",1)[1]+second.split("rules:\n",1)[1])
        result=self.run_cli("delegate","rules","--manifest",manifest,"--rules-file",rule_path)
        self.assertEqual(result.returncode,2)

    def test_masked_feature_rules_and_inconclusive_gradient(self):
        mask = Image.new("L", (8, 8), 0)
        mask.putpixel((1, 1), 255); mask.putpixel((6, 6), 255)
        mask.save(self.root / "mask.png")
        manifest = self.write_manifest(self.base(features=[{
            "id":"subject", "role":"subject", "geometry":{"type":"mask","path":"mask.png"},
            "properties":{"max_connected_components":1,"min_symmetry_iou":0.9,"gradient_allowed":False}
        }]))
        result = json.loads(self.run_cli("review", "--manifest", manifest).stdout)
        states = {row["rule_id"]:row["status"] for row in result["results"]}
        self.assertEqual(states["TOPOLOGY-001"], "FAIL")
        self.assertEqual(states["SYMMETRY-001"], "FAIL")
        self.assertEqual(states["GRADIENT-001"], "INCONCLUSIVE")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["completeness"],"INCOMPLETE")

    def test_verify_detects_changes_outside_allowed_region(self):
        edited = self.image.copy(); edited.putpixel((0,0),(0,0,0,255)); edited.save(self.root / "edited.png")
        args = ("verify", "--before", self.root/"asset.png", "--after", self.root/"edited.png")
        self.assertEqual(self.run_cli(*args, "--region", 4,4,8,8).returncode, 1)
        self.assertEqual(self.run_cli(*args).returncode, 1)
        self.assertEqual(self.run_cli(*args, "--region", 0,0,1,1).returncode, 0)

    def test_svg_rules_and_invalid_asset_path(self):
        (self.root / "asset.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs><path d="M0 0 L1 1" stroke-width="4"/></svg>')
        manifest = self.write_manifest({"schema_version":"0.1", "asset":{"path":"asset.svg"},
             "constraints":{"max_svg_gradients":0,"max_svg_stroke_width":2},"features":[]})
        report = json.loads(self.run_cli("review", "--manifest", manifest).stdout)
        self.assertEqual(report["status"], "FAIL")
        bad = self.write_manifest({"schema_version":"0.1", "asset":{"path":"../outside.png"}, "features":[]})
        self.assertEqual(self.run_cli("manifest", "validate", bad).returncode, 2)

    def test_svg_complex_path_geometry(self):
        (self.root/"asset.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 30"><path id="curve" d="M0 10 C10 -5 20 25 30 10 A5 5 0 0 1 35 15 Z"/></svg>')
        doc={"schema_version":"0.1","asset":{"path":"asset.svg"},"features":[{"id":"mark","role":"foreground","properties":{"svg_path_id":"curve","min_path_segments":3,"min_path_length":30}}]}
        manifest=self.write_manifest(doc)
        details=json.loads(self.run_cli("inspect",self.root/"asset.svg").stdout)
        self.assertEqual(details["paths"][0]["segment_types"], ["CubicBezier","Arc","Line"])
        result=json.loads(self.run_cli("review","--manifest",manifest).stdout)
        path_result=next(row for row in result["results"] if row["rule_id"]=="SVG-003")
        self.assertEqual(path_result["status"],"PASS")
        self.assertGreater(path_result["measured"]["path"]["length"],30)

    def test_rgb_asset_cannot_prove_alpha_centroid(self):
        Image.new("RGB",(8,8),(255,255,255)).save(self.root/"opaque.jpg")
        manifest=self.write_manifest({"schema_version":"0.5","asset":{"path":"opaque.jpg","format":"jpg"},
                                      "constraints":{"max_normalized_centroid_offset":0.2},"features":[]})
        result=json.loads(self.run_cli("review","--manifest",manifest).stdout)
        row=next(x for x in result["results"] if x["rule_id"]=="GEOMETRY-001")
        self.assertEqual(row["status"],"INCONCLUSIVE")
        self.assertEqual(result["completeness"],"INCOMPLETE")

    def test_ciede2000_reference_pair(self):
        # Sharma et al. CIEDE2000 worked example (pair 1): expected ΔE00 ≈ 2.0425.
        self.assertAlmostEqual(_delta_e_2000((50.0,2.6772,-79.7751),(50.0,0.0,-82.7485)),2.0425,places=4)

    def test_lab_uniformity_and_fixed_palette_bins(self):
        im=Image.new("RGBA",(4,2),(200,40,30,255))
        im.putpixel((0,0),(201,40,30,255)); im.save(self.root/"asset.png")
        Image.new("L",(4,2),255).save(self.root/"mask.png")
        feature={"id":"foreground","role":"foreground","geometry":{"type":"mask","path":"mask.png"},
                 "properties":{"surface":"solid","max_delta_e00":0.1,"delta_e_tolerance":0.1,
                               "max_palette_colors":1,"palette_bin_size_lab":[100,100,100]}}
        manifest=self.write_manifest(self.base(features=[feature]))
        result=json.loads(self.run_cli("review","--manifest",manifest).stdout)
        solid=next(row for row in result["results"] if row["algorithm"]=="ciede2000_uniformity")
        palette=next(row for row in result["results"] if row["algorithm"]=="masked_palette_count")
        self.assertEqual(solid["status"],"FAIL")
        self.assertEqual(palette["measured"],1)

    def test_background_and_character_feature_metrics(self):
        Image.new("L", (8,8), 255).save(self.root / "mask.png")
        feature = {"id":"background", "role":"background", "geometry":{"type":"mask","path":"mask.png"},
                   "properties":{"seamless_tile":True,"max_tile_edge_error":0,"min_occupancy_ratio":1,
                                 "max_periodic_energy_ratio":0.5,"max_luma_levels":1,
                                 "max_silhouette_components":1,"max_gradient_fit_r2":0.9}}
        manifest = self.write_manifest(self.base(features=[feature]))
        result = json.loads(self.run_cli("review", "--manifest", manifest).stdout)
        states={item["rule_id"]:item["status"] for item in result["results"]}
        self.assertEqual(states["BACKGROUND-001"],"PASS")
        self.assertEqual(states["BACKGROUND-002"],"PASS")
        self.assertEqual(states["BACKGROUND-003"],"PASS")
        self.assertEqual(states["CHARACTER-001"],"PASS")
        self.assertEqual(states["CHARACTER-002"],"PASS")
        self.assertEqual(states["GRADIENT-002"],"INCONCLUSIVE")

    def test_feature_overlap_constraint(self):
        a=Image.new("L",(8,8),0); b=Image.new("L",(8,8),0)
        for xy in [(2,2),(2,3),(3,2),(3,3)]: a.putpixel(xy,255)
        for xy in [(2,2),(2,3),(3,2),(3,3)]: b.putpixel(xy,255)
        a.save(self.root/"a.png"); b.save(self.root/"b.png")
        doc=self.base(features=[{"id":"face","role":"face","geometry":{"type":"mask","path":"a.png"}},
                                {"id":"hair","role":"hair","geometry":{"type":"mask","path":"b.png"}}])
        doc["overlap_constraints"]=[{"feature_a":"face","feature_b":"hair","max_overlap_ratio":0.2}]
        manifest=self.write_manifest(doc)
        report=json.loads(self.run_cli("review","--manifest",manifest).stdout)
        overlap=next(row for row in report["results"] if row["rule_id"]=="OVERLAP-001")
        self.assertEqual(overlap["status"],"FAIL")
        self.assertEqual(overlap["measured"],1.0)

    def test_game_trace_policy_checks_and_deterministic_output(self):
        trace={"schema_version":"1","timebase":"seconds","random_seed":17,
               "tracks":[{"id":"root","kind":"position","units":"m","coordinate_system":"world",
                          "samples":[{"time":0,"value":[0,0,0]},{"time":1,"value":[1,0,0]}]}],
               "events":[{"id":"hit","event_type":"collision","time":0.8}],
               "particles":[{"id":"spark","spawn_time":0.5,"death_time":1.0}]}
        trace_path=self.root/"trace.json"; trace_path.write_text(json.dumps(trace))
        policy={"max_position_step":1,"max_velocity":1,"max_loop_boundary_difference":1,
                "expected_event_times":{"hit":0.75},"max_event_timing_error":0.1,"max_particle_lifetime":0.6}
        policy_path=self.root/"policy.json"; policy_path.write_text(json.dumps(policy))
        args=("game","analyze","--trace",trace_path,"--policy",policy_path)
        first=self.run_cli(*args); second=self.run_cli(*args)
        self.assertEqual(first.returncode,0,first.stderr)
        self.assertEqual(first.stdout,second.stdout)
        report=json.loads(first.stdout)
        self.assertEqual(report["status"],"PASS")
        self.assertEqual(report["completeness"],"COMPLETE")
        policy["max_velocity"]=0.5; policy_path.write_text(json.dumps(policy))
        failed=self.run_cli(*args)
        self.assertEqual(failed.returncode,1)
        self.assertEqual(json.loads(failed.stdout)["status"],"FAIL")

    def test_game_trace_missing_threshold_and_invalid_timestamps(self):
        trace={"schema_version":"1","timebase":"frames",
               "tracks":[{"id":"root","kind":"position","units":"px","coordinate_system":"screen",
                          "samples":[{"time":0,"value":[0,0]},{"time":1,"value":[2,0]}]}]}
        path=self.root/"trace.json"; path.write_text(json.dumps(trace))
        result=self.run_cli("game","analyze","--trace",path)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        self.assertEqual(report["status"],"INCONCLUSIVE")
        self.assertEqual(report["completeness"],"INCOMPLETE")
        trace["tracks"][0]["samples"][1]["time"]=0
        path.write_text(json.dumps(trace))
        invalid=self.run_cli("game","analyze","--trace",path)
        self.assertEqual(invalid.returncode,2)
        self.assertIn("strictly increasing",invalid.stderr)
        trace["tracks"][0]["samples"][1]["time"]=1; path.write_text(json.dumps(trace))
        bad_policy=self.root/"bad-policy.json"; bad_policy.write_text('{"max_velocity":"fast"}')
        invalid_policy=self.run_cli("game","analyze","--trace",path,"--policy",bad_policy)
        self.assertEqual(invalid_policy.returncode,2)
        self.assertIn("max_velocity must be",invalid_policy.stderr)
        bad_policy.write_text('{"max_alpha_occlusion_ratio":1.1}')
        invalid_ratio=self.run_cli("game","analyze","--trace",path,"--policy",bad_policy)
        self.assertEqual(invalid_ratio.returncode,2)
        self.assertIn("between 0 and 1",invalid_ratio.stderr)

    def test_game_pose_contact_and_particle_bounds(self):
        def track(identity, values, **extra):
            return {"id":identity,"kind":"position","units":"m","coordinate_system":"world",
                    "samples":[{"time":i,"value":value} for i,value in enumerate(values)],**extra}
        trace={"schema_version":"1","timebase":"seconds","tracks":[
            track("root",[[0,0],[0,0],[0,0]]),
            track("foot",[[0,0],[0.1,0],[0.1,0]]),
            track("upper-leg",[[0,1],[0,1],[0,1]],parent_track_id="root",rest_length=1),
            track("spark-path",[[0.5,0.5],[1.1,0.5],[0.5,0.5]])],
            "contacts":[{"id":"left-foot-stance","track_id":"foot","start_time":0,"end_time":2}],
            "particles":[{"id":"spark","spawn_time":0,"death_time":2,"position_track_id":"spark-path"}]}
        trace_path=self.root/"pose-trace.json"; trace_path.write_text(json.dumps(trace))
        policy={"max_position_step":2,"max_bone_length_deviation":0.01,"max_foot_sliding_distance":0.2,
                "max_particle_lifetime":3,"particle_bounds":{"min":[0,0],"max":[1,1],"units":"m","coordinate_system":"world"}}
        policy_path=self.root/"pose-policy.json"; policy_path.write_text(json.dumps(policy))
        result=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        by_algorithm={row["algorithm"]:row for row in report["results"] if "algorithm" in row}
        self.assertEqual(by_algorithm["bone_length_deviation"]["status"],"PASS")
        self.assertEqual(by_algorithm["foot_sliding_distance"]["status"],"PASS")
        self.assertEqual(by_algorithm["particle_emitter_bounds"]["status"],"FAIL")

    def test_game_trace_manifest_review_and_coverage(self):
        manifest=self.root/"game-manifest.json"
        trace=Path(__file__).parent.parent/"examples"/"game"/"motion-trace.json"
        policy=json.loads((trace.parent/"policy.json").read_text())
        doc={"schema_version":"0.5","asset":{"path":str(trace)},"intent":{"kind":"game_trace"},
             "features":[],"game_policy":policy}
        # Keep manifest paths relative so the standard containment checks apply.
        local_trace=self.root/"trace.json"; local_trace.write_bytes(trace.read_bytes())
        doc["asset"]["path"]="trace.json"; manifest.write_text(json.dumps(doc))
        self.assertEqual(self.run_cli("manifest","validate",manifest).returncode,0)
        plan=self.run_cli("plan","--manifest",manifest)
        self.assertEqual(plan.returncode,0,plan.stderr)
        self.assertEqual(json.loads(plan.stdout)["status"],"READY")
        report_path=self.root/"game-report.json"
        review=self.run_cli("review","--manifest",manifest,"--output",report_path)
        self.assertEqual(review.returncode,0,review.stderr)
        report=json.loads(report_path.read_text())
        self.assertEqual(report["status"],"PASS")
        self.assertEqual(report["completeness"],"COMPLETE")
        self.assertEqual(self.run_cli("coverage","--report",report_path).returncode,0)

    def test_game_manifest_marks_missing_planned_track_inconclusive(self):
        (self.root/"trace.json").write_text(json.dumps({"schema_version":"1","timebase":"seconds"}))
        manifest=self.write_manifest({"schema_version":"0.5","asset":{"path":"trace.json"},"intent":{"kind":"game_trace"},
                                      "features":[],"game_policy":{"max_position_step":1}})
        result=self.run_cli("review","--manifest",manifest)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        self.assertEqual(report["completeness"],"INCOMPLETE")
        self.assertIn("trace contains no evidence",report["results"][-1]["formula"])

    def test_game_frame_alpha_weighted_occlusion_and_path_safety(self):
        back=Image.new("RGBA",(4,4),(255,255,255,255)); back.save(self.root/"back.png")
        front=Image.new("RGBA",(8,4),(0,0,0,0)); front.putpixel((0,0),(0,0,0,255)); front.save(self.root/"front.png")
        trace={"schema_version":"1","timebase":"seconds","frames":[{"time":0,"frame_index":0,"layers":[
            {"id":"background","path":"back.png","z_index":0},{"id":"foreground","path":"front.png","region":[0,0,4,4],"z_index":1}]}]}
        trace_path=self.root/"layers.json"; trace_path.write_text(json.dumps(trace))
        policy_path=self.root/"occlusion.json"; policy_path.write_text(json.dumps({"max_alpha_occlusion_ratio":0.05}))
        result=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(result.returncode,1)
        finding=next(row for row in json.loads(result.stdout)["results"] if row.get("algorithm")=="alpha_weighted_occlusion")
        self.assertAlmostEqual(finding["measured"]["occlusion_ratio"],0.0625)
        self.assertEqual(finding["status"],"FAIL")
        trace["frames"][0]["layers"][0]["path"]="../outside.png"; trace_path.write_text(json.dumps(trace))
        unsafe=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(unsafe.returncode,2)

    def test_game_local_transform_hierarchy_composes_before_measurement(self):
        trace={"schema_version":"1","timebase":"seconds","tracks":[
            {"id":"root","kind":"position","units":"m","coordinate_system":"world","samples":[
                {"time":0,"value":[10,0]},{"time":1,"value":[20,0]}]},
            {"id":"socket","kind":"position","units":"m","coordinate_system":"world","coordinate_space":"local",
             "parent_track_id":"root","basis_matrix":[[0,-1],[1,0]],"samples":[
                {"time":0,"value":[0,1]},{"time":1,"value":[0,1]}]}]}
        trace_path=self.root/"hierarchy.json"; trace_path.write_text(json.dumps(trace))
        policy_path=self.root/"hierarchy-policy.json"; policy_path.write_text('{"max_position_step":100,"max_velocity":5}')
        result=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        socket_velocity=next(row for row in report["results"] if row.get("id")=="VELOCITY:socket")
        self.assertEqual(socket_velocity["status"],"FAIL")
        self.assertEqual(socket_velocity["measured"]["max"],10)

    def test_game_time_varying_parent_rotation_and_scale(self):
        trace={"schema_version":"1","timebase":"seconds","tracks":[
            {"id":"root","kind":"position","units":"m","coordinate_system":"world","samples":[
                {"time":0,"value":[0,0],"basis_matrix":[[1,0],[0,1]]},
                {"time":1,"value":[0,0],"basis_matrix":[[0,-1],[1,0]]}]},
            {"id":"child","kind":"position","units":"m","coordinate_system":"world","coordinate_space":"local","parent_track_id":"root",
             "samples":[{"time":0,"value":[1,0]},{"time":1,"value":[1,0]}]}]}
        trace_path=self.root/"moving-transform.json"; trace_path.write_text(json.dumps(trace))
        policy_path=self.root/"moving-transform-policy.json"; policy_path.write_text('{"max_position_step":10,"max_velocity":1.3}')
        result=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        velocity=next(row for row in report["results"] if row.get("id")=="VELOCITY:child")
        self.assertAlmostEqual(velocity["measured"]["max"],2**0.5)
        self.assertEqual(velocity["status"],"FAIL")

    def test_game_rotation_pose_anchor_and_derivative_algorithms(self):
        trace={"schema_version":"1","timebase":"seconds","tracks":[
            {"id":"root","kind":"position","units":"m","coordinate_system":"world","samples":[
                {"time":0,"value":[0,0]},{"time":1,"value":[1,0]},{"time":2,"value":[4,0]},{"time":3,"value":[9,0]}]},
            {"id":"target","kind":"position","units":"m","coordinate_system":"world","samples":[
                {"time":0,"value":[0.1,0]},{"time":1,"value":[1.1,0]},{"time":2,"value":[4.1,0]},{"time":3,"value":[9.1,0]}]},
            {"id":"facing","kind":"rotation","units":"quaternion","coordinate_system":"world","samples":[
                {"time":0,"value":[0,0,0,1]},{"time":1,"value":[0,0,0.70710678,0.70710678]}]},
            {"id":"pose","kind":"pose","units":"m","coordinate_system":"world","samples":[
                {"time":0,"value":{"hip":[0,0],"knee":[1,0]}},{"time":1,"value":{"hip":[1,0],"knee":[1,0]}}]}],
            "anchors":[{"id":"weapon-tip","track_a":"root","track_b":"target"}]}
        trace_path=self.root/"metrics.json"; trace_path.write_text(json.dumps(trace))
        policy={"max_position_step":20,"max_velocity":10,"max_acceleration":2.1,"max_jerk":0.1,
                "max_rotation_step_degrees":45,"max_pose_loop_boundary_distance":0.5,"max_anchor_distance":0.2}
        policy_path=self.root/"metrics-policy.json"; policy_path.write_text(json.dumps(policy))
        result=self.run_cli("game","analyze","--trace",trace_path,"--policy",policy_path)
        self.assertEqual(result.returncode,1)
        by_algorithm={row["algorithm"]:row for row in json.loads(result.stdout)["results"] if row.get("algorithm")}
        self.assertEqual(by_algorithm["acceleration_magnitude"]["status"],"PASS")
        self.assertEqual(by_algorithm["jerk_magnitude"]["status"],"PASS")
        self.assertEqual(by_algorithm["rotation_distance"]["status"],"FAIL")
        self.assertEqual(by_algorithm["pose_boundary_distance"]["status"],"FAIL")
        self.assertEqual(by_algorithm["anchor_distance"]["status"],"PASS")

    def test_engine_tagged_export_wrappers_and_adapter_selection(self):
        canonical=json.loads((Path(__file__).parent.parent/"examples"/"game"/"motion-trace.json").read_text())
        policy=json.loads((Path(__file__).parent.parent/"examples"/"game"/"policy.json").read_text())
        policy_path=self.root/"engine-policy.json"; policy_path.write_text(json.dumps(policy))
        for engine,version in (("godot","4.3"),("unity","2022.3")):
            wrapper=self.root/f"{engine}.json"
            wrapper.write_text(json.dumps({"format":f"imreview.{engine}-export/1","engine_version":version,"trace":canonical}))
            result=self.run_cli("game","analyze","--trace",wrapper,"--policy",policy_path)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report["engine"],engine)
            self.assertEqual(report["engine_version"],version)
            manifest=self.root/f"{engine}-manifest.json"
            manifest.write_text(json.dumps({"schema_version":"0.5","asset":{"path":wrapper.name,"engine":engine},
                "intent":{"kind":"game_trace"},"features":[],"game_policy":policy}))
            plan=self.run_cli("plan","--manifest",manifest)
            self.assertEqual(plan.returncode,0,plan.stderr)
            self.assertEqual(json.loads(plan.stdout)["checks"][0]["adapter_ids"],[f"{engine}_trace"])


if __name__ == "__main__":
    unittest.main()
