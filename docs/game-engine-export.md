# Game engine trace exports

The trace analyzer reads versioned JSON exports and does not open an engine project. A separate, explicitly invoked `imreview project export-trace` command can launch Godot or Unity against a user-selected scene/clip. Both engine wrappers contain the canonical trace defined in [`game-trace.schema.json`](../schemas/game-trace.schema.json); an exporter is responsible for sampling engine objects and writing canonical units, coordinate labels, tracks, events, and particle records.

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
imreview project export-trace --engine godot --project <project-root> \
  --engine-executable <godot-console-executable> --selection scenes/hero.tscn \
  --output <absolute-trace.json> --allow-project-code

# Install the Unity Editor extension once, then select an existing .anim under Assets.
imreview project install-exporter --engine unity --project <project-root>
imreview project export-trace --engine unity --project <project-root> \
  --engine-executable <Unity-executable> --selection Assets/Animations/hero.anim \
  --output <absolute-trace.json> --allow-project-code
```

Unity exporter installation is explicit and refuses to overwrite an existing file. Scanning and exporter installation do not launch the project. The engine invocation can run project/editor code; use it only for projects you trust. Output files are validated against the shared trace schema before the command reports success.

The Godot exporter was run inside the Godot 4.6.3 headless editor against a temporary fixture scene; it exported position/rotation samples and a method event, and the resulting wrapper passed `imreview game analyze` with explicit fixture thresholds. The Unity exporter compiled and ran inside Unity 6000.3.25f1 batch mode; the test verified the registered Assets menu path, generated a clip with transform curves and an event, and passed the same CLI analysis. The local integration fixtures and outputs are under [`integration-fixtures`](../integration-fixtures/). These checks cover keyframed transform evidence; they do not execute arbitrary project callbacks or extract particle simulation state.
