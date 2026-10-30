# Local game project discovery

`imreview project preview` performs bounded, read-only discovery for local Godot and Unity projects. It reports detected project roots, engine versions/name metadata, supported raster/SVG files, file dimensions/alpha where readable, limited static references, Unity sprite mode, scan limits, skipped directories and errors. It does not launch an engine, import assets, follow symlinks, load plugins, execute scripts, infer image semantics, or invent quality thresholds.

```sh
imreview project preview --path <project-or-parent-directory>
imreview project preview --path <directory> --max-files 20000 --max-depth 16
```

The default scan is capped at 20,000 files and 16 directory levels. `.git`, `.godot`, Unity `Library`, build outputs, dependency caches, and common Python/Node caches are skipped. If the result says `INCOMPLETE`, inspect the reported coverage before using the inventory. If more than one project is detected, choose a project root explicitly for the next command.

## Manifest draft

Select one project and one image path relative to its root. Save the output directly in the selected project root so the manifest's relative asset path stays contained:

```sh
imreview project manifest --project <project-root> --asset Assets/Art/hero.png \
  --output <project-root>/review-draft.json
```

The draft pins the selected asset with SHA-256, but has no feature masks or constraints. Add semantically reviewed features and explicit thresholds before running `imreview plan` or `imreview review`. An empty draft is not a quality verdict.

## Engine trace export

Scanning and draft generation never run engine code. Engine export is a distinct opt-in command and requires all selection details plus the `--allow-project-code` acknowledgement. Godot loads the selected scene; Unity starts its editor in batch mode and invokes the installed exporter. These actions can execute project/editor code.

For Godot, select one project-relative scene:

```sh
imreview project export-trace --engine godot --project <godot-root> \
  --engine-executable <Godot-console-executable> --selection scenes/hero.tscn \
  --output <absolute-output.json> --allow-project-code
```

For Unity, install the bundled editor extension once (the command only copies the file and refuses to overwrite an existing one), then select a clip already stored beneath `Assets`:

```sh
imreview project install-exporter --engine unity --project <unity-root>
imreview project export-trace --engine unity --project <unity-root> \
  --engine-executable <Unity-executable> --selection Assets/Animations/hero.anim \
  --output <absolute-output.json> --allow-project-code
```

The emitted JSON is checked against the trace contract. The currently exercised exporters extract keyed transform curves and animation event metadata; they do not simulate gameplay, invoke runtime callbacks, or extract live particle state. See [engine export contract](game-engine-export.md).
