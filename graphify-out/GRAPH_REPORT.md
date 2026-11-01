# Graph Report - I-mage-not-AI  (2026-10-30)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 661 nodes · 1298 edges · 47 communities (43 shown, 4 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3aff015`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 46

## God Nodes (most connected - your core abstractions)
1. `CliWorkflowTest` - 35 edges
2. `review()` - 26 edges
3. `fail()` - 25 edges
4. `emit()` - 24 edges
5. `internal_error()` - 19 edges
6. `load_manifest()` - 17 edges
7. `analyze_trace()` - 16 edges
8. `discover_projects()` - 14 edges
9. `load_trace()` - 13 edges
10. `ImreviewTraceExporter` - 12 edges

## Surprising Connections (you probably didn't know these)
- `ProjectDiscoveryTest` --uses--> `FeatureManifest`  [INFERRED]
  tests/test_project_discovery.py → imreview/models.py
- `PluginApiTest` --uses--> `PluginDescriptor`  [INFERRED]
  tests/test_plugins.py → imreview/plugins.py
- `PluginApiTest` --uses--> `PluginRegistry`  [INFERRED]
  tests/test_plugins.py → imreview/plugins.py
- `main()` --calls--> `review()`  [EXTRACTED]
  benchmarks/benchmark_review.py → imreview/core.py
- `load_manifest()` --uses--> `FeatureManifest`  [INFERRED]
  imreview/core.py → imreview/models.py

## Import Cycles
- None detected.

## Communities (47 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (25): asset_path(), _bbox_list(), _delta_e_2000(), _delta_e_2000_array(), inspect_image(), ManifestError, _mask_metrics(), plan_review() (+17 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (30): load_manifest(), load_trace(), load_project_rules(), analyze_game_trace(), benchmark_evaluate(), benchmark_gallery(), benchmark_generate_synthetic(), benchmark_init_submission() (+22 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (6): Curves, ImreviewTraceExporter, ImreviewIntegrationProbe, ImreviewIntegrationRunner, Curves, ImreviewTraceExporter

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (12): main(), run_engine_export(), create_project_manifest(), discover_projects(), _find_projects(), _image_info(), install_unity_exporter(), _references() (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (20): analyze_trace(), AnchorPair, ContactInterval, _dist(), _finding(), _flatten_pose(), FrameLayer, GameFrame (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (6): AlgorithmPlugin, PluginDescriptor, PluginRegistry, verify_plugin_file(), ExampleAlgorithm, PluginApiTest

### Community 7 - "Community 7"
Cohesion: 0.14
Nodes (10): create_submission_template(), generate_synthetic_dataset(), render_gallery(), image_ref(), score_files(), score_findings(), update_leaderboard(), validate_submission() (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (25): additionalProperties, delta_e_tolerance, gradient_allowed, luma_bin_width, max_channel_range, max_connected_components, max_delta_e00, max_exceedance_ratio (+17 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (21): minLength, type, items, maxItems, minItems, type, items, maxItems (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (4): AdapterDescriptor, FeatureAdapter, MaskFeatureAdapter, SourceAdapter

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (16): asset, format, path, sha256, attack_hit, features, game_policy, expected_event_times (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (11): AssetRef, EventTrack, Evidence, Feature, FeatureGeometry, FeatureManifest, ParticleTrack, Provenance (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (16): type, type, enum, type, type, properties, algorithm, algorithm_version (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (14): type, type, type, minLength, type, properties, type, evidence (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (13): type, type, enum, properties, asset, asset_id, completeness, rule_registry_version (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (12): additionalProperties, properties, type, type, enum, intent, kind, origin (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (12): type, type, properties, required, type, type, checks, completed (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (11): additionalProperties, type, additionalProperties, type, type, properties, constraints, game_policy (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (11): properties, minimum, type, minimum, type, maximum, minimum, type (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (10): type, maxItems, minItems, type, allowed_mask, allowed_region, regression, additionalProperties (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (10): additionalProperties, properties, required, type, enum, asset, engine, sha256 (+2 more)

### Community 22 - "Community 22"
Cohesion: 0.20
Nodes (10): items, maxItems, minItems, type, required, type, allowed_region, results (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.28
Nodes (9): items, items, type, additionalProperties, minimum, required, type, items (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (8): type, additionalProperties, type, properties, minimum, type, expected_event_times, max_particle_lifetime

### Community 25 - "Community 25"
Cohesion: 0.29
Nodes (7): properties, required, type, type, geometry, path, type

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (5): additionalProperties, required, $schema, title, type

### Community 27 - "Community 27"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 28 - "Community 28"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, max_alpha_occlusion_ratio

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, max_normalized_centroid_offset

### Community 30 - "Community 30"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, max_overlap_ratio

### Community 31 - "Community 31"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, max_rotation_loop_difference_degrees

### Community 32 - "Community 32"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, max_rotation_step_degrees

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (3): minimum, type, max_acceleration

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (3): minimum, type, max_anchor_distance

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (3): minimum, type, max_bone_length_deviation

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (3): minimum, type, max_event_timing_error

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (3): minimum, type, max_foot_sliding_distance

### Community 39 - "Community 39"
Cohesion: 0.67
Nodes (3): minimum, type, max_jerk

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (3): minimum, type, max_loop_boundary_difference

### Community 41 - "Community 41"
Cohesion: 0.67
Nodes (3): minimum, type, max_pose_loop_boundary_distance

### Community 42 - "Community 42"
Cohesion: 0.67
Nodes (3): minimum, type, max_position_step

### Community 43 - "Community 43"
Cohesion: 0.67
Nodes (3): minimum, type, max_svg_stroke_width

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (3): minimum, type, max_velocity

## Knowledge Gaps
- **1 isolated node(s):** `imreview`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 252 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `Community 18` to `Community 16`, `Community 20`, `Community 21`, `Community 23`, `Community 26`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **What connects `imreview` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Why does `properties` connect `Community 24` to `Community 32`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 42`, `Community 9`, `Community 44`, `Community 18`, `Community 28`, `Community 31`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13642960812772134 - nodes in this community are weakly interconnected._
- **Why does `CliWorkflowTest` connect `Community 5` to `Community 0`, `Community 3`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09082125603864734 - nodes in this community are weakly interconnected._