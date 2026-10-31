import unittest
import json
import tempfile
from pathlib import Path

from i_mage_not_ai.benchmark import score_findings, score_files, generate_synthetic_dataset, create_submission_template, verify_synthetic_submission, update_leaderboard, render_gallery


class BenchmarkScoringTest(unittest.TestCase):
    def test_scores_rule_level_findings_and_ignores_non_failures(self):
        result = score_findings(
            [{"case_id": "icon-01", "rule_id": "PALETTE"}, {"case_id": "icon-02", "rule_id": "MARGIN"}],
            [
                {"case_id": "icon-01", "rule_id": "PALETTE", "status": "FAIL"},
                {"case_id": "icon-02", "rule_id": "MARGIN", "status": "PASS"},
                {"case_id": "icon-03", "rule_id": "ALIGN", "status": "FAIL"},
            ],
        )
        self.assertEqual((result["true_positives"], result["false_positives"], result["false_negatives"]), (1, 1, 1))
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["f1"], 0.5)

    def test_rejects_duplicate_labeled_findings(self):
        with self.assertRaisesRegex(ValueError, "duplicate expected"):
            score_findings(
                [{"case_id": "icon-01", "rule_id": "PALETTE"}] * 2,
                [],
            )
        with self.assertRaisesRegex(ValueError, "duplicate observed"):
            score_findings([], [
                {"case_id":"icon-01","rule_id":"PALETTE","status":"FAIL"},
                {"case_id":"icon-01","rule_id":"PALETTE","status":"PASS"},
            ])

    def test_empty_prediction_metrics_are_undefined(self):
        result = score_findings([], [])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["f1"])

    def test_versioned_files_preserve_dataset_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            truth = root / "truth.json"
            predictions = root / "predictions.json"
            truth.write_text(json.dumps({"schema_version":"1", "dataset_id":"icon-synthetic", "dataset_version":"0.1.0", "findings":[{"case_id":"a", "rule_id":"COLOR"}]}))
            predictions.write_text(json.dumps({"findings":[{"case_id":"a", "rule_id":"COLOR", "status":"FAIL"}]}))
            result = score_files(truth, predictions)
            self.assertEqual((result["dataset_id"], result["dataset_version"]), ("icon-synthetic", "0.1.0"))
            self.assertEqual(result["f1"], 1.0)
            predictions.write_text(json.dumps({"dataset_id":"other","dataset_version":"9","findings":[{"case_id":"a", "rule_id":"COLOR", "status":"FAIL"}]}))
            with self.assertRaisesRegex(ValueError, "prediction dataset_id"):
                score_files(truth, predictions)

    def test_synthetic_generator_is_reproducible_and_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = generate_synthetic_dataset(root / "data", 3)
            self.assertEqual(len(dataset["cases"]), 3)
            self.assertEqual(len(dataset["findings"]), 3)
            self.assertEqual(dataset["cases"][0]["injected_rule"], "COLOR-001")
            self.assertEqual(dataset["cases"][1]["injected_rule"], "GEOMETRY-002")
            self.assertEqual(generate_synthetic_dataset(root / "again", 3)["findings"], dataset["findings"])

    def test_asset_verification_and_leaderboard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset_dir = root / "dataset"
            dataset = generate_synthetic_dataset(dataset_dir, 2)
            template_path = root / "template.json"
            template = create_submission_template(dataset_dir / "dataset.json", template_path)
            self.assertEqual(len(template["tracks"]["agent_only"]["assets"]), 2)
            submission_dir = root / "run"
            submission_dir.mkdir()
            metadata = {"agent":"test", "model":"test-model", "prompt_version":"1", "environment":"cpu"}
            tracks = {"original":{"metadata":metadata,"assets":{}},"agent_only":{"metadata":metadata,"assets":{}},"agent_plus_tool":{"metadata":metadata,"assets":{}}}
            for case in dataset["cases"]:
                from PIL import Image
                with Image.open(dataset_dir / case["clean_asset"]) as clean:
                    output = submission_dir / f"{case['case_id']}.png"
                    clean.save(output)
                for name in ("agent_only", "agent_plus_tool"):
                    tracks[name]["assets"][case["case_id"]] = output.name
            tracks["original"]["assets"] = {case["case_id"]:case["faulty_asset"] for case in dataset["cases"]}
            submission = submission_dir / "submission.json"
            submission.write_text(json.dumps({"schema_version":"1","dataset_id":dataset["dataset_id"],"dataset_version":dataset["dataset_version"],"protocol":{"prompt_sha256":"a"*64,"attempt_limit":3,"environment_image":"python:3.12","seed":0},"tracks":tracks}))
            result = verify_synthetic_submission(dataset_dir / "dataset.json", submission)
            self.assertEqual(result["status"], "VERIFIED_SYNTHETIC")
            self.assertEqual(result["tracks"]["agent_only"]["recall"], 0.0)
            self.assertEqual(result["tracks"]["agent_plus_tool"]["fix_success_rate"], 1.0)
            board = update_leaderboard(root / "leaderboard.json", result, "run-1")
            self.assertEqual(board["entries"][0]["run_id"], "run-1")
            result_path = root / "result.json"
            result_path.write_text(json.dumps(result))
            gallery = render_gallery(dataset_dir / "dataset.json", submission, result_path, root / "report" / "index.html")
            gallery_text = gallery.read_text(encoding="utf-8")
            self.assertIn("Agent + I-mage-not-AI", gallery_text)
            self.assertIn("Fix success", gallery_text)
            with self.assertRaisesRegex(ValueError, "independently verified"):
                update_leaderboard(root / "bad.json", {"status":"SCORED_UNVERIFIED"}, "run-2")

    def test_synthetic_repair_checks_alpha_and_leaderboard_prioritizes_repairs(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); dataset_dir=root/"dataset"
            dataset=generate_synthetic_dataset(dataset_dir,1)
            case=dataset["cases"][0]
            run=root/"run"; run.mkdir()
            with Image.open(dataset_dir/case["faulty_asset"]) as image:
                image.convert("RGBA").save(run/"unchanged.png")
                transparent=image.convert("RGBA"); transparent.putalpha(0); transparent.save(run/"transparent.png")
            with Image.open(dataset_dir/case["clean_asset"]) as image:
                image.convert("RGBA").save(run/"clean.png")
            metadata={"agent":"test","model":"model","prompt_version":"1","environment":"test"}
            def submission(tool_image):
                return {"schema_version":"1","dataset_id":dataset["dataset_id"],"dataset_version":dataset["dataset_version"],
                    "protocol":{"prompt_sha256":"a"*64,"attempt_limit":1,"environment_image":"test","seed":0},
                    "tracks":{
                        "original":{"metadata":metadata,"assets":{case["case_id"]:case["faulty_asset"]}},
                        "agent_only":{"metadata":metadata,"assets":{case["case_id"]:"clean.png"}},
                        "agent_plus_tool":{"metadata":metadata,"assets":{case["case_id"]:tool_image}},
                    }}
            subpath=run/"submission.json"
            subpath.write_text(json.dumps(submission("transparent.png")))
            transparent_result=verify_synthetic_submission(dataset_dir/"dataset.json",subpath)
            transparent_metrics=transparent_result["tracks"]["agent_plus_tool"]
            self.assertEqual(transparent_metrics["fix_success_rate"],0.0)
            self.assertEqual(transparent_metrics["remaining_violations"],1)
            self.assertGreater(transparent_metrics["changed_pixels"],0)
            self.assertGreater(transparent_metrics["changes_outside_allowed_region"],0)
            self.assertLess(transparent_metrics["preservation_rate"],1.0)

            board_path=root/"leaderboard.json"
            unchanged=verify_synthetic_submission(dataset_dir/"dataset.json",subpath)
            update_leaderboard(board_path,unchanged,"unchanged")
            subpath.write_text(json.dumps(submission("clean.png")))
            repaired=verify_synthetic_submission(dataset_dir/"dataset.json",subpath)
            board=update_leaderboard(board_path,repaired,"repaired")
            self.assertEqual([entry["run_id"] for entry in board["entries"]],["repaired","unchanged"])


if __name__ == "__main__":
    unittest.main()
