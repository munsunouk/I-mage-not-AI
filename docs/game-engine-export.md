# Game engine trace exports

The CLI reads versioned JSON exports and never opens a Godot or Unity project. Both engine wrappers contain the canonical trace defined in [`game-trace.schema.json`](../schemas/game-trace.schema.json); an editor exporter is responsible for sampling engine objects and writing canonical units, coordinate labels, tracks, events, and particle records.

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

These wrappers specify the safe handoff contract, not a native `.tscn`, `.tres`, `.unity`, or `.asset` parser. Native project files and scripts are not evaluated. The editor-side exporter must be versioned and tested against each supported engine release before its output is treated as authoritative.

## Included editor exporters

`engine/godot/imreview_export.gd` is an `EditorScript`: open the target scene in Godot, select **File → Run** for the script, and it writes `res://imreview-godot-export.json` (or the first command-line user argument). It reads keyed 3D position/rotation/scale tracks and method-event timestamps from the first `AnimationPlayer`; it does not instantiate scenes, advance animation, or invoke method tracks.

`engine/unity/Editor/ImreviewTraceExporter.cs` adds **Assets → Export AnimationClip as imreview Trace**. Select an `AnimationClip` and choose the output file. It reads `AnimationUtility` transform curves and event metadata without instantiating a GameObject or invoking animation events.

The Godot exporter was syntax-scanned with Godot 4.6.3. Unity is not installed in the build environment, so the C# exporter still needs compilation and fixture validation in a supported Unity editor before production use. Both tools export keyframed transform evidence; they do not execute arbitrary project callbacks or extract particle simulation state.
