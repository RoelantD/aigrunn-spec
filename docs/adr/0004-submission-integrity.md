# ADR 0004: Submission integrity

- **Status**: accepted (2026-11-11)
- **Context**: Submissions are real, irreversible and rate-limited. Wrong answers trigger growing
  waits. A crash or network loss can leave it unknown whether the website received an answer
  (FR-017–FR-022).
- **Decision**:
  1. A `Submission` row with outcome `PENDING` is committed **before** the POST is sent.
  2. `AocClient.submit` never retries.
     - If the connection could not be established, the answer was not sent: the run pauses.
     - A transport error after sending marks the submission `UNCERTAIN`.
  3. On startup, `PENDING` rows become `UNCERTAIN`. Before any further submission for that part,
     the orchestrator re-reads the day page and looks for "Your puzzle answer was". This step never
     POSTs.
     - If the part shows as solved, it is marked VERIFIED.
     - If not, one resubmission of the same answer is allowed after a safety wait of 60 s.
  4. An account-wide ledger stores rejected answers and the bounds learned from "too high" and
     "too low". Candidates that are already rejected or out of bounds are never submitted, and are
     fed back to the model instead.
  5. Cooldowns are stored per account and year (`AccountState.cooldown_until`). The run waits for
     them with an interruptible sleep. A cooldown reply does not count as a judged submission.
  6. A part allows at most `max_submissions_per_part` judged submissions (default 3).
- **Consequences**: A restart can never cause a double submission. There is a tested path for every
  response category. The ledger survives a "reset local data" on purpose.
