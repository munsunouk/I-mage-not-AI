# Rule authoring

Rules must be based on explicit user or project constraints. Do not create a failure threshold from an agent's visual inference. A feature's `provenance.origin` may be `user_spec`, `project_config`, `source_native`, or `agent_inferred`; inferred facts can guide diagnostics but do not establish a mandatory quality policy.

The manifest can carry constraints inline or load project rules with `--rules-file`. `imreview/rules/algorithms.yaml` declares algorithm versions, source adapters, and required capabilities; `imreview/rules/packs.yaml` groups supported algorithms by asset type. `i-mage-not-ai delegate rules --manifest FILE --rules-file RULES.yaml` shows the resolved mapping; `i-mage-not-ai plan --manifest FILE --rules-file RULES.yaml` shows required capabilities and readiness. All independent matching constraints execute. Unsupported checks appear as missing/inconclusive and must not silently disappear.

## Project defaults, asset profiles, and exceptions

Keep algorithm definitions and their mathematical semantics fixed. Set project-wide conventions once (such as color space, units, coordinate system, and timebase), then author policy rules for asset classes with selectors such as `asset_type`, `style`, and `feature_role`. Use `feature_id` only for a justified asset-specific exception. The CLI does not infer numeric thresholds or semantic feature masks.

Use increasing priorities for progressively narrower rules (project-wide, asset type, type plus style/role, then feature ID). Rules that target the same measurement resolve to the highest priority. Equal-priority rules with different assertions or parameters are rejected. Palette algorithms share one target because they both write the palette-count contract; `svg_path_geometry` targets include the selected metric. Do not define multiple same-target variants expecting both assertions or parameter sets to apply. For `mask_intersection_ratio`, the feature pair is the target.

Suggested lifecycle:

1. At project setup, record the source of each project-wide convention and write only numeric limits grounded in user specifications or project configuration.
2. Add profiles as selector-based rules for real asset classes (for example `asset_type: sprite` plus a role). Leave unsupported checks out; never make a placeholder threshold.
3. Per asset, select the matching intent type/style, provide approved masks and trace anchors, and use the project rules file. Add a feature-ID exception only with an explicit reason and source.
4. Inspect the resolved rule plan and coverage. A missing mask, capability, or threshold is not a pass.

Example hierarchy (thresholds are illustrative and must be replaced by project requirements):

```yaml
schema_version: "1"
rules:
  - id: PROJECT-CENTER
    version: "1.0"
    priority: 0
    match: {}
    algorithm: {id: alpha_centroid_offset, version: "1.0"}
    assertion: {operator: less_than_or_equal, value: 0.08, origin: project_config}
  - id: SPRITE-ROLE-PALETTE
    version: "1.0"
    priority: 20
    match: {asset_type: sprite, feature_role: body}
    algorithm:
      id: quantized_palette_count
      version: "1.0"
      parameters: {bin_size: [10, 10, 10]}
    assertion: {operator: less_than_or_equal, value: 8, origin: project_config}
  - id: SPECIAL-BODY-PALETTE
    version: "1.0"
    priority: 40
    match: {asset_type: sprite, feature_id: special_body}
    algorithm:
      id: quantized_palette_count
      version: "1.0"
      parameters: {bin_size: [10, 10, 10]}
    assertion: {operator: less_than_or_equal, value: 12, origin: user_spec}
```

Replace all example IDs, limits, roles, and profile selectors with approved project values before using this as policy.

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

Priority resolves competing rules for the same measurement target. Equal-priority contradictory assertions or parameter sets are rejected. Only registered algorithms execute.

Keep algorithm version, units, formula, threshold, source hash, feature, and region in the result. Use `INCONCLUSIVE` when inputs are absent or semantics cannot be established. See [manifest schema](../schemas/feature-manifest.schema.json).
