# Rule authoring

Rules must be based on explicit user or project constraints. Do not create a failure threshold from an agent's visual inference. A feature's `provenance.origin` may be `user_spec`, `project_config`, `source_native`, or `agent_inferred`; inferred facts can guide diagnostics but do not establish a mandatory quality policy.

The manifest can carry constraints inline or load project rules with `--rules-file`. `imreview/rules/algorithms.yaml` declares algorithm versions, source adapters, and required capabilities; `imreview/rules/packs.yaml` groups supported algorithms by asset type. `imreview delegate rules --manifest FILE --rules-file RULES.yaml` shows the resolved mapping; `imreview plan --manifest FILE --rules-file RULES.yaml` shows required capabilities and readiness. All independent matching constraints execute. Unsupported checks appear as missing/inconclusive and must not silently disappear.

Example feature policy:

```json
{
  "id": "background",
  "role": "background",
  "geometry": {"type": "mask", "path": "masks/background.png"},
  "properties": {"surface": "solid", "max_channel_range": 2},
  "provenance": {"origin": "user_spec"}
}
```

Project YAML policy example:

```yaml
schema_version: "1"
rules:
  - id: ICON-PALETTE
    version: "1.0"
    priority: 100
    match: {asset_type: icon, style: flat, feature_role: foreground}
    requires: [raster_pixels, feature_mask]
    algorithm:
      id: quantized_palette_count
      version: "1.0"
      parameters: {bin_size: [10, 10, 10]}
    assertion: {operator: less_than_or_equal, value: 6, origin: project_config}
    on_missing: inconclusive
    severity: error
```

Priority resolves competing rules with the same match, feature, algorithm, and parameters. Equal-priority contradictory assertions are rejected. Only registered algorithms execute.

Keep algorithm version, units, formula, threshold, source hash, feature, and region in the result. Use `INCONCLUSIVE` when inputs are absent or semantics cannot be established. See [manifest schema](../schemas/feature-manifest.schema.json).
