# Metrics ledger — every number on a résumé has a row here

Rename to `metrics-ledger.md` once filled in. A number may appear in `content-pool.tex`, a base,
or a tailored résumé only if it has a row below with a method someone could repeat. `status`:
`measured` (script or log, reproducible) · `counted` (countable in a repo or report) · `stated`
(your own figure, method still to be written down) · `retired` (do not use). The skill may add
`measured` and `counted` rows with evidence; `stated` rows need your method before they are
relied on in an interview. The rows below are examples, replace them.

## <Project A>
| value | what it measures | how measured | date | n | status | say it like this |
|---|---|---|---|---|---|---|
| 0 model calls per replay | LLM calls made while replaying a recorded run | sum of `provider_calls` over `evidence/replay-*/result.json` | <YYYY-MM-DD> | 16 runs | measured | Replay never calls a model; the engine asserts it. |
| 140 tests | collected test cases | `pytest --collect-only` | <YYYY-MM-DD> | - | counted | Re-collect before quoting if the repo changes. |

## <Employer B>
| value | what it measures | how measured | date | n | status | say it like this |
|---|---|---|---|---|---|---|
| roughly 40% shorter turnaround | the whole assign-to-feedback cycle | your own estimate, not timed | <YYYY> | - | stated | Say "roughly". Never sharpen a stated figure. |
