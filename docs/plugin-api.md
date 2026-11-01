# Plugin API v1

The standard CLI does not discover or import Python plugins. Project YAML can already select registered built-in algorithms; it cannot execute arbitrary code. An embedding host may opt into the in-process API in `i_mage_not_ai.plugins` after reviewing and allowlisting a plugin's SHA-256 digest.

An algorithm object implements `plugin_id`, `algorithm_id`, `version`, `capabilities`, `supports(evidence_type, requirements)`, and `measure(evidence, parameters)`. Register it with a `PluginDescriptor` whose IDs, API version, version, digest, and capabilities exactly match the object. `PluginRegistry` rejects untrusted IDs, digest mismatches, duplicate or built-in algorithm IDs, missing capabilities, unsupported evidence, and non-finite/non-JSON results.

The host must call `verify_plugin_file(path, plugin_id, trusted_hashes)` before it imports plugin code. This checks a regular, non-symlink source file against a digest in the host's explicit trust map. Registration executes no discovery and no imports; calling `PluginRegistry.measure` executes the already imported algorithm in the host process. Therefore only reviewed, trusted code belongs in that allowlist. The API does not claim to sandbox a plugin. Use a separate OS-level sandbox before accepting code from untrusted authors.

Plugins return measurements only. They do not choose pass/fail thresholds, read or write assets, access networks, or modify reports. The host remains responsible for policy evaluation and provenance.
