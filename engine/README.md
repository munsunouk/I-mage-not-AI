# Canonical engine adapters

Godot (`.gd`) and Unity (`.cs`) scripts in this directory are the source of truth for bundled exporters and capture runners.

The installable package copies them into `i_mage_not_ai/engine_resources/` for setuptools `package-data`. After editing files here, run:

```sh
python scripts/sync_engine_resources.py
```

CI runs `python scripts/sync_engine_resources.py --check` so packaged copies cannot drift silently.
