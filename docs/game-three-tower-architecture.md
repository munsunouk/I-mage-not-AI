# Game three-tower architecture

Game verification splits into **three independent towers** plus an optional aggregate gate. This is intentional: a single manifest `review` pass cannot prove runtime or rendered pixels.

| Tower | CLI | Manifest `plan` / rule packs |
| --- | --- | --- |
| Trace (static JSON) | `game analyze`, manifest `intent.kind=game_trace` | **`game`**, `motion`, `skeletal_animation`, `vfx`, `sprite` packs in `rules/packs.yaml` |
| Runtime (live samples) | `game runtime-check` | **`game_runtime` pack** — not driven by manifest `features[]` today |
| Render (PNG captures) | `game render-check` | **`game_render` pack** — not driven by manifest `features[]` today |

Use **`game gate`** (and optional `event-bridge.json`, `input-binding.json`, binding flags) to aggregate three **reports** after each tower completes.

Trace-only tasks should stop at trace PASS. Full “on-screen” claims require runtime + render reports and a gate PASS with aligned `scenario_id` (and, when enabled, `evidence_run_id`, event bridge, and input digests).

See [game-policy-reference.md](game-policy-reference.md), [game-engine-export.md](game-engine-export.md), and [game-capture-and-gate.md](../.agents/skills/i-mage-not-ai/game-capture-and-gate.md).
