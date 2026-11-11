# ADR 0001: Custom orchestration loop

- **Status**: accepted (2026-11-11)
- **Context**: The brief requires an observable, persisted state machine whose states (FETCHING …
  VERIFIED) are visible to the audience. It also requires clean separation of inference, sandbox,
  website access and persistence (Constitution VII).
- **Decision**: `app/agents/orchestrator.py` owns the per-part state machine and submission logic.
  `app/agents/solver.py` owns the understand/generate/test/repair/escalate attempt loop.
  `app/agents/policy.py` holds the pure escalation policy, and `app/agents/control.py` the
  cooperative pause/stop control. All side effects go through injected services.
- **Consequences**: Every transition is explicit, persisted and emitted as an event. Recovery after
  a restart is deterministic. The core can be tested with fakes (scripted models, fake website,
  fake executor) without network access. The cost is that retries and checkpoints had to be written
  by hand.
- **Rejected**: agent frameworks. They would hide the loop that the talk is about and add
  dependencies the audience would need to understand.
