# Engine integration fixtures

These temporary editor projects exercise the included Godot and Unity trace exporters. They generate a two-key position track, a two-key rotation track, and one method/animation event, then run the exported wrapper through `imreview game analyze` with explicit fixture thresholds.

The CLI is installed in the repository's `.venv` on E:. Re-run the Godot editor probe with:

```powershell
& 'E:\Godot\4.6.3\Godot_v4.6.3-stable_win64_console.exe' --headless --editor --path 'E:\I-mage-not-AI\integration-fixtures\godot' --quit
```

Re-run the Unity editor probe with:

```powershell
& 'E:\Unity\Editors\6000.3.25f1\Editor\Unity.exe' -batchmode -nographics -projectPath 'E:\I-mage-not-AI\integration-fixtures\unity' -executeMethod ImreviewIntegrationRunner.Run -logFile 'E:\I-mage-not-AI\integration-fixtures\unity\unity-integration.log' -quit
```

Each editor project writes a versioned JSON wrapper. The corresponding `policy.json` and `review.json` files record the CLI analysis. Generated editor caches (`.godot`, `Library`, `Logs`, `Temp`, `UserSettings`) are ignored by Git.
