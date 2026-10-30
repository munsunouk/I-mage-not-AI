import hashlib
import tempfile
import unittest
from pathlib import Path

from imreview.plugins import PluginDescriptor, PluginRegistry, verify_plugin_file


class ExampleAlgorithm:
    plugin_id="org.example.metrics"
    algorithm_id="example.mean"
    version="1.0"
    capabilities=frozenset({"numeric_values"})
    def supports(self,evidence_type,requirements): return evidence_type=="values" and requirements<=self.capabilities
    def measure(self,evidence,parameters): return {"mean":sum(evidence["values"])/len(evidence["values"])}


class PluginApiTest(unittest.TestCase):
    def test_explicit_digest_allowlist_and_execution_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"plugin.py"; source.write_text("# reviewed plugin source\n")
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(verify_plugin_file(source,"org.example.metrics",{"org.example.metrics":digest}),digest)
            registry=PluginRegistry({"org.example.metrics":digest},frozenset({"builtin.algorithm"}))
            descriptor=PluginDescriptor(plugin_id="org.example.metrics",algorithm_id="example.mean",version="1.0",sha256=digest,
                                        capabilities=frozenset({"numeric_values"}))
            registry.register(descriptor,ExampleAlgorithm())
            result=registry.measure("example.mean","values",{"values":[2,4,6]}, {},frozenset({"numeric_values"}))
            self.assertEqual(result["measured"],{"mean":4})
            self.assertEqual(registry.registered_algorithms,("example.mean",))

    def test_plugin_default_denial_digest_and_output_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"plugin.py"; source.write_text("pass\n")
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,"not allowlisted"):
                verify_plugin_file(source,"org.example.metrics",{})
            with self.assertRaisesRegex(ValueError,"does not match"):
                verify_plugin_file(source,"org.example.metrics",{"org.example.metrics":"0"*64})
            registry=PluginRegistry()
            with self.assertRaisesRegex(ValueError,"not allowlisted"):
                registry.register(PluginDescriptor(plugin_id="org.example.metrics",algorithm_id="example.mean",version="1.0",sha256=digest),ExampleAlgorithm())

    def test_plugin_results_reject_non_finite_values(self):
        class BadAlgorithm(ExampleAlgorithm):
            def measure(self,evidence,parameters): return {"value":float("nan")}
        digest="a"*64
        registry=PluginRegistry({"org.example.metrics":digest})
        registry.register(PluginDescriptor(plugin_id="org.example.metrics",algorithm_id="example.mean",version="1.0",sha256=digest,
                                           capabilities=frozenset({"numeric_values"})),BadAlgorithm())
        with self.assertRaisesRegex(ValueError,"finite JSON"):
            registry.measure("example.mean","values",{"values":[1]}, {},frozenset({"numeric_values"}))


if __name__=="__main__": unittest.main()
