"""JSON Schema contracts and property checks for deterministic metrics."""
from __future__ import annotations

import json
import hashlib
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, settings, strategies as st
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
import numpy as np
from PIL import Image

from imreview.core import _delta_e_2000, _delta_e_2000_array, _rgb_array_lab, review


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


class SchemaContractTest(unittest.TestCase):
    def load_schema(self, name: str) -> dict:
        schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return schema

    def test_manifest_and_game_trace_examples_validate(self):
        manifest_schema = self.load_schema("feature-manifest.schema.json")
        manifest = json.loads((ROOT / "examples" / "icon-manifest.json").read_text(encoding="utf-8"))
        manifest["schema_version"] = "0.5"
        Draft202012Validator(manifest_schema).validate(manifest)
        manifest_without_hash={**manifest,"asset":{key:value for key,value in manifest["asset"].items() if key!="sha256"}}
        with self.assertRaises(ValidationError):
            Draft202012Validator(manifest_schema).validate(manifest_without_hash)

        trace_schema = self.load_schema("game-trace.schema.json")
        trace = json.loads((ROOT / "examples" / "game" / "motion-trace.json").read_text(encoding="utf-8"))
        Draft202012Validator(trace_schema).validate(trace)
        invalid_trace=deepcopy(trace)
        invalid_trace["tracks"][0]["basis_matrix"]=[[1,0,0],[0,1,0]]
        with self.assertRaises(ValidationError):
            Draft202012Validator(trace_schema).validate(invalid_trace)
        for engine, version in (("godot", "4.6.3"), ("unity", "6000.3.25f1")):
            wrapper = {"format": f"imreview.{engine}-export/1", "engine_version": version, "trace": trace}
            Draft202012Validator(trace_schema).validate(wrapper)

    def test_review_report_matches_schema(self):
        report_schema = self.load_schema("review-result.schema.json")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new("RGBA", (4, 4), (20, 30, 40, 255)).save(root / "asset.png")
            digest=hashlib.sha256((root / "asset.png").read_bytes()).hexdigest()
            manifest = {"schema_version": "0.5", "asset": {"path": "asset.png", "sha256": digest}, "features": []}
            result = review(manifest, root)
        Draft202012Validator(report_schema).validate(result)


class DeterministicMetricProperties(unittest.TestCase):
    @settings(max_examples=100, deadline=None)
    @given(
        st.tuples(st.floats(0, 100), st.floats(-128, 127), st.floats(-128, 127)),
        st.tuples(st.floats(0, 100), st.floats(-128, 127), st.floats(-128, 127)),
    )
    def test_delta_e00_is_symmetric_and_nonnegative(self, first, second):
        forward = _delta_e_2000(first, second)
        reverse = _delta_e_2000(second, first)
        self.assertGreaterEqual(forward, 0)
        self.assertAlmostEqual(forward, reverse, places=8)
        self.assertAlmostEqual(_delta_e_2000(first, first), 0, places=8)

    @settings(max_examples=80, deadline=None)
    @given(
        st.lists(st.tuples(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)), min_size=1, max_size=32),
        st.tuples(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
    )
    def test_vectorized_delta_e_matches_scalar_reference(self, samples, reference):
        lab_samples = _rgb_array_lab(np.asarray(samples, dtype="uint8"))
        lab_reference = _rgb_array_lab(np.asarray(reference, dtype="uint8").reshape(1, 3))[0]
        actual = _delta_e_2000_array(lab_samples, lab_reference)
        expected = [_delta_e_2000(sample, lab_reference) for sample in lab_samples]
        for result, baseline in zip(actual, expected):
            self.assertAlmostEqual(float(result), baseline, places=8)


if __name__ == "__main__":
    unittest.main()
