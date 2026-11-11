# ADR 0005: SQLite, persisted event bus, SSE with resume

- **Status**: accepted (2026-11-11)
- **Context**: The dashboard must show what really happened, survive reconnects without gaps or
  duplicates, and support replay (FR-030, FR-031, FR-039).
- **Decision**:
  - Every event is written to SQLite first. Its autoincrement `id` is the global order. Only then
    is it fanned out to in-process subscribers.
  - The SSE endpoint subscribes before it reads history. It then streams history after
    `Last-Event-ID` or `after_id`, followed by live events, and drops any id it has already sent.
  - Timestamps are serialised with an explicit UTC offset.
  - Replay copies a recorded run's events into a new `mode=replay` run at a compressed speed. Every
    copied event has `replay: true`. A replay calls no services.
- **Consequences**: One process and one file, which suits a single presenter laptop. Replays are
  exact. A SQLite WAL with a busy timeout handles the concurrent API and orchestrator sessions.
