# Game engine trace exports

The trace analyzer reads versioned JSON exports and does not open an engine project. A separate, explicitly invoked `i-mage-not-ai project export-trace` command can launch Godot or Unity against a user-selected scene/clip. Both engine wrappers contain the canonical trace defined in [`game-trace.schema.json`](../schemas/game-trace.schema.json); an exporter is responsible for sampling engine objects and writing canonical units, coordinate labels, tracks, events, and particle records.

Godot 4 exports use:

```json
{
  "format": "imreview.godot-export/1",
  "engine_version": "4.3",
  "trace": {
    "schema_version": "1",
    "timebase": "seconds",
    "tracks": [],
    "events": [],
    "particles": []
  }
}
```

Unity exports use `"format": "imreview.unity-export/1"` and the Unity editor version. The `trace` payload follows the same canonical schema. Position tracks may carry local coordinates, a `parent_track_id`, and a static 2D/3D `basis_matrix`; samples may override that matrix to record time-varying rotation and scale. Hierarchy samples must be synchronized, and parent/child units and coordinate labels must match. Rotation tracks use normalized or normalizable `[x, y, z, w]` quaternions. The reader rejects unrecognized wrapper fields and reports the engine/version in review evidence.

The read-only `project preview` command recognizes project markers and inspects bounded text metadata/references; it does not execute importers, scripts, plugins, or editor processes. It is not a complete parser for native `.tscn`, `.tres`, `.unity`, or `.asset` formats. `project export-trace` is a separate execution boundary: the user must supply an explicit project, selection, engine executable, output path, and `--allow-project-code`. Loading a chosen Godot scene or invoking a Unity editor can execute code in that project. Exporters must be versioned and tested against each supported engine release before their output is treated as authoritative.

## Included editor exporters

`engine/godot/imreview_export.gd` is an `EditorScript`: open the target scene in Godot, select **File → Run** for the script, and it writes `res://imreview-godot-export.json` (or the first command-line user argument). It reads keyed 3D position/rotation/scale tracks and method-event timestamps from the first `AnimationPlayer`; it does not instantiate scenes, advance animation, or invoke method tracks.

`engine/unity/Editor/ImreviewTraceExporter.cs` adds **Assets → Export AnimationClip as imreview Trace**. Select an `AnimationClip` and choose the output file. It reads `AnimationUtility` transform curves and event metadata without instantiating a GameObject or invoking animation events.

The CLI exporter uses the same Godot script and Unity C# exporter:

```sh
# Godot selection is a project-relative .tscn path.
i-mage-not-ai project export-trace --engine godot --project <project-root> \
  --engine-executable <godot-console-executable> --selection scenes/hero.tscn \
  --output <absolute-trace.json> --allow-project-code

# Install the Unity Editor extension once, then select an existing .anim under Assets.
i-mage-not-ai project install-exporter --engine unity --project <project-root>
i-mage-not-ai project export-trace --engine unity --project <project-root> \
  --engine-executable <Unity-executable> --selection Assets/Animations/hero.anim \
  --output <absolute-trace.json> --allow-project-code
```

Unity exporter installation is explicit and refuses to overwrite an existing file. Scanning and exporter installation do not launch the project. The engine invocation can run project/editor code; use it only for projects you trust. Output files are validated against the shared trace schema before the command reports success.

## Runtime evidence

`i-mage-not-ai game runtime-check --evidence <runtime-evidence.json> --policy <runtime-policy.json>` analyzes an engine-produced `imreview.runtime-evidence/1` record. It compares observed callback invocation counts/times and particle sample times, active counts (when exposed), and live particle bounds with explicit numeric policy limits. The checker does not execute engine code and ignores engine-authored `checks` booleans; it recomputes each finding from the observation arrays.

The Godot 4.6.3 fixture runs a scene under Vulkan Forward+ at fixed 60 FPS, advances an `AnimationPlayer` method track to invoke the callback, and samples `GPUParticles2D.capture_rect()` with a fixed seed. A dummy/headless renderer does not provide the GPU particle buffer needed for this measurement, so this check must run with a renderer. Godot exposes the current particle AABB here, not a live particle count or each particle's state.

The Unity 6000.3.25f1 fixture enters Play Mode, plays an `Animator` clip containing an `AnimationEvent`, and simulates a seeded `ParticleSystem`; it records active particles through `GetParticles()` and measures their positions. These fixtures demonstrate actual engine observations for the included deterministic scenarios. Arbitrary projects still need a callback instrumentation component or project-specific adapter and an explicit scenario that triggers the relevant emitters. A fixed seed does not guarantee bit-identical GPU pixels across different renderer/driver versions; this runtime check measures declared engine state, not visual semantics.

Example for the Godot fixture:

```powershell
& 'E:\Godot\4.6.3\Godot_v4.6.3-stable_win64_console.exe' --path integration-fixtures/godot --scene res://runtime_scene.tscn --fixed-fps 60 --rendering-method forward_plus
.venv\Scripts\python.exe -m i_mage_not_ai game runtime-check --evidence integration-fixtures/godot/runtime-evidence.json --policy integration-fixtures/godot/runtime-policy.json
```

Runtime evidence and review reports are separate from static animation exports, preserving the distinction between declared events and events actually observed during playback.
