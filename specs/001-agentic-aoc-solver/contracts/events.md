# Event Contract

Every event: `{id, run_id, type, day?, part?, level, message, data, replay, created_at}`.
`message` is a short human-readable sentence derived from the actual action. `data` never
contains secrets, cookies, tokens, or personal puzzle input.

| type | level | data | emitted when |
|------|-------|------|--------------|
| `run.created` / `run.started` / `run.paused` / `run.resumed` / `run.stopped` / `run.completed` / `run.interrupted` / `run.budget_exhausted` | info/success/warning | `{status, reason?}` | run lifecycle |
| `part.state` | info | `{from, to, reason?}` | every PartState transition |
| `aoc.fetch` | info | `{what: calendar\|page\|input, cached: bool}` | website access or cache hit |
| `aoc.previously_completed` | success | `{answer_known: bool}` | account already completed part |
| `model.call.started` | info | `{model_key, deployment, purpose, effort}` | before a model call |
| `model.call.finished` | info | `{model_key, input_tokens, output_tokens, reasoning_tokens, latency_ms, cost_usd}` | after a model call |
| `model.call.retry` | warning | `{model_key, status_code, retry_in_s}` | infra retry |
| `agent.analysis` | info | `{summary, algorithm, complexity}` | understanding produced |
| `agent.code` | info | `{revision, sha256, lines}` | new code revision |
| `test.started` / `test.result` | info / success / error | `{revision, passed, total, failures:[{index, expected, actual, error}]}` | example tests |
| `test.unavailable` | warning | `{reason}` | no reliable examples |
| `agent.repair` | warning | `{attempt, reason}` | repair triggered |
| `agent.escalation` | warning | `{from_model, to_model, reason, attempt}` | escalation |
| `exec.input` | info / error | `{revision, status, duration_ms, answer?}` | real input execution |
| `submit.skipped_duplicate` | warning | `{reason}` | candidate equals rejected/out of bounds |
| `submit.awaiting_approval` | info | `{answer}` | manual mode |
| `submit.sent` | info | `{answer}` | POST about to be sent (after PENDING persisted) |
| `submit.result` | success / warning / error | `{outcome, wait_seconds?, message}` | response classified |
| `submit.cooldown` | warning | `{until}` | cooldown recorded |
| `submit.reconciled` | info | `{verified: bool}` | uncertain submission reconciled |
| `star.earned` | success | `{stars_total}` | CORRECT (drives star animation) |
| `part.unlocked` | success | `{}` | Part 2 now available |
| `budget.warning` | warning | `{spent_usd, limit_usd}` | 80% of budget |
| `error` | error | `{kind: infra\|aoc\|internal, detail}` | unexpected failures (redacted) |

Ordering: `id` is a global monotonically increasing integer; clients resume with `Last-Event-ID`.
Replayed events carry `replay: true` and belong to the replay run.
