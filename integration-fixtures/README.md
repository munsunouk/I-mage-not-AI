# Engine integration fixtures

These temporary editor projects exercise static exporters and runtime probes. Static exporters generate transform tracks and declared event metadata. Runtime probes play the Godot method track / Unity `AnimationEvent` and sample live particle state under fixed fixture conditions. The observed report is evaluated by `imreview game runtime-check` against explicit `runtime-policy.json` limits.

The CLI is installed in the repository's `.venv` on E:. Re-run the Godot editor probe with:

```powershell
& 'E:\Godot\4.6.3\Godot_v4.6.3-stable_win64_console.exe' --headless --editor --path 'E:\I-mage-not-AI\integration-fixtures\godot' --quit
```

Re-run the Unity editor probe with:

```powershell
& 'E:\Unity\Editors\6000.3.25f1\Editor\Unity.exe' -batchmode -noUpm -projectPath 'E:\I-mage-not-AI\integration-fixtures\unity' -executeMethod ImreviewIntegrationRunner.Run -logFile 'E:\I-mage-not-AI\integration-fixtures\unity\unity-integration.log'
```

Each engine fixture writes static exporter JSON and separate runtime-evidence JSON. `policy.json`/`review.json` cover static traces; `runtime-policy.json`/`runtime-review.json` cover observed runtime behavior. Generated editor caches (`.godot`, `Library`, `Logs`, `Temp`, `UserSettings`) are ignored by Git.

For Godot runtime evidence, use the real Vulkan renderer rather than `--headless`; headless mode returned an empty GPU particle capture on the tested machine. The fixed seed, fixed FPS, callback, and bounds policy make the fixture repeatable on this Godot/renderer setup. Unity runtime evidence is emitted by `ImreviewIntegrationRunner.Run` after it enters Play Mode; Play Mode animation events are required because edit-mode `Animator.Update()` did not invoke them. After either engine writes evidence, run the `game runtime-check` command shown in `docs/game-engine-export.md` with that engine's `runtime-policy.json`.
