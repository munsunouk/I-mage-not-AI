# Isolated icon benchmark: Agent Only vs Agent + CLI

## Result

| Metric | Agent Only | Agent + CLI | Delta (CLI - Only) |
|---|---:|---:|---:|
| Diagnosis precision / recall / F1 | 100% / 100% / 100% | 100% / 100% / 100% | 0 pp |
| Repair success | 20/20 (100%) | 20/20 (100%) | 0 pp |
| Regressions | 0/20 | 0/20 | 0 |
| Preservation | 100% | 100% | 0 pp |
| Changed pixels | 970 | 970 | 0 |
| Changes outside allowed regions | 0 | 0 | 0 |

The CLI condition produced no measurable improvement on this loop. Both agents
diagnosed and repaired all 20 injected synthetic defects. This is a single
exploratory run, not evidence that either method is generally better.

## Protocol

- Two separate, projectless Codex conversations with independent conversation
  histories. The same 20 randomized sample IDs and task specification were used.
- Agent Only could inspect and edit images visually. Agent + CLI had access to
  `imreview` reports and was instructed to use them to guide edits.
- Each session had one attempt per asset. The evaluator alone held the mapping
  from randomized sample IDs to dataset case IDs and injected rules.
- All 20 Agent + CLI reports were checked for complete status and input SHA-256.
- Both output sets were re-evaluated with the benchmark evaluator. Diagnosis
  scores are independently calculated from each session's `decisions.json`;
  repair metrics come from `verified-result.json`.

## Limits

- Only 20 simple, fault-injected synthetic flat icons were included; the agents
  received no clean controls, so false-positive rates on clean art are unknown.
- The sessions were isolated at the conversation level, but filesystem access
  was not OS-sandboxed. Mapping secrecy was procedural.
- Exact model snapshot, token usage, and API cost were unavailable. Session
  durations include setup and CLI manifest debugging and are not comparable
  inference times.
- The earlier same-session loop is retained as exploratory material and is
  superseded by this isolated run for the Agent Only vs Agent + CLI comparison.

## Artifacts

- `comparison.json`: diagnosis, repair, and delta scores.
- `verified-result.json`: result from the repository benchmark evaluator.
- `comparison.html`: scored before/after gallery, including the independent
  pre-repair diagnosis scores.
- `comparison-contact-sheet.png`: all 20 inputs and both repaired outputs.
- `agent-only/` and `agent-cli/`: submitted outputs and decisions; the CLI
  folder also contains per-sample manifests and reports.
- `evaluator/ground-truth-map.json`: evaluator-only randomized ID mapping.
