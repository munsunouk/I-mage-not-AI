# Complex icon benchmark: Agent Only vs Agent + CLI

## Result

| Measure | Agent Only | Agent + CLI |
|---|---:|---:|
| Diagnosis precision / recall / F1 | 100% / 100% / 100% | 100% / 100% / 100% |
| Repairs satisfying both palette and margin limits | 20/20 | 20/20 |
| Canvas dimensions preserved | 20/20 | 20/20 |
| Exact pixel match to evaluator clean source | 100.00% | 85.72% |

Both conditions found and fixed all injected defects while meeting both numeric
limits. Agent Only restored every icon pixel-for-pixel to the clean source. The
CLI condition met the minimum margin limit but often stopped after the smallest
translation that passed; its outputs therefore remained off-center relative to
the original. Its mean exact pixel match to the clean source was 85.72% overall
(99.91% on palette cases and 71.52% on margin cases). This is a measurable
tradeoff in this run, not evidence that visual judgment is generally superior.

## Protocol and validation

- Two fresh projectless sessions with independent conversation histories and
  the same randomized 20-icon input bundle and per-image limits.
- Agent Only used visual diagnosis. Agent + CLI created a per-image manifest,
  ran `i-mage-not-ai review`, and used its saved JSON measurements to repair.
- Both sessions had one repair attempt per icon. The evaluator held the hidden
  sample-to-label map and clean references.
- Preflight checked all 20 inputs: exactly the injected rule failed and the
  other measured rule passed. The Agent + CLI session's 20 reports were also
  checked against the input hashes and completion status.
- The first prepared batch (`complex-icon-isolated-loop-01`) was stopped before
  submission after preflight found its palette injections did not cross the
  configured limit. Its outputs are excluded. This report uses the corrected
  v1.0.1 batch only.

## Limits

This is one synthetic loop on generated game icons, with explicit palette and
margin rules. It does not score semantic fidelity, style quality, or human
preference. Sessions were isolated by conversation and anonymized IDs, but
filesystem access was not OS-sandboxed. Exact model snapshot, token use, and
API cost were unavailable.

## Artifacts

- `comparison.json`: diagnosis and repair scores, per-icon measurements, and
  session isolation metadata.
- `comparison.html`: before/Agent Only/Agent + CLI gallery with summary table.
- `comparison-contact-sheet.png`: compact visual comparison of all 20 icons.
- `agent-only/` and `agent-cli/`: repaired PNGs and decisions; Agent + CLI also
  has all 20 manifests and original measurement reports under `reports/`.
- `evaluator/preflight-cli-v2/`: independent rule preflight reports, separated
  from the task inputs.
