# Architecture Decision Records

These ADRs were written by the implementing agent (Claude Code) during `/speckit-implement` and
`/speckit-converge`. Each expands a decision in [research.md](../../specs/001-agentic-aoc-solver/research.md)
or [plan.md](../../specs/001-agentic-aoc-solver/plan.md).

| ADR | Decision |
|-----|----------|
| [0001](0001-custom-agent-loop.md) | Custom orchestration loop, no agent framework |
| [0002](0002-rest-adapters.md) | Plain REST adapters (httpx) for both Foundry model APIs |
| [0003](0003-sandbox-harness.md) | Dynamic Sessions with a marker-based harness; no local executor |
| [0004](0004-submission-integrity.md) | PENDING-before-POST, reconciliation, account-wide answer ledger |
| [0005](0005-events-sqlite-sse.md) | SQLite + persisted event bus + SSE with resume |
| [0006](0006-input-privacy.md) | Personal input is never sent to models (shape preview only) |
| [0007](0007-two-worktrees.md) | Two git worktrees + external data directory for the talk |
