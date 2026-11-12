# Specification Analysis Report (captured output of `/speckit-analyze`)

> `/speckit-analyze` is read-only; this file is the report it produced on 2026-11-11, saved
> verbatim afterwards so the analysis is visible at checkpoint `demo/05-tasks`. Remediation was
> applied in a separate, explicit step (see "Remediation applied" at the end).

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F1 | Inconsistency | HIGH | plan.md "Solving state machine" vs spec.md FR-016 | Plan marks a part BLOCKED with `infra_error` when model/sandbox retries are exhausted and pauses the run; FR-016 says after BLOCKED the run continues with the next day. An outage would cascade BLOCKED across all remaining days. | Treat exhausted infra retries as a run-level pause: the part keeps a resumable state with `status_reason=infra_error`; BLOCKED is reserved for problem/dependency causes. |
| D1 | Constitution Alignment | HIGH | constitution I ("hardcoding known answers is forbidden"); plan Constitution Check row I; tasks.md | The plan cites a "static check for answer literals" but no task implements it; only the prompt forbids hardcoding. | Add a guard in the solver: reject code whose `solve` returns a constant independent of input (detected by executing on two different example inputs and the real input yielding identical answers where examples expect different values) and flag literal-return patterns. |
| E1 | Coverage Gap | MEDIUM | spec.md SC-006; tasks.md | No task asserts the per-day website request budget (~10 requests, paced). | Extend T023 to assert request count and spacing against the fake site. |
| E2 | Coverage Gap | MEDIUM | spec.md FR-038 | No task explicitly ensures hidden reasoning is neither requested nor displayed. | Note in T030/T056 that reasoning/thinking items are discarded and never persisted; add assertion in adapter tests. |
| F2 | Inconsistency | LOW | plan.md Constraints ("max 220 s"); contracts/rest-api.md (`exec_timeout_max_s=120`) | Two different "maximum" timeouts. | Clarify: platform ceiling 220 s; configured default maximum 120 s (operator may raise up to 220 s). |
| E3 | Coverage Gap | LOW | spec.md SC-004 | SSE tests check ordering/resume but not the 2 s latency target. | Add a latency assertion (event published → received) in T042. |
| B1 | Ambiguity | LOW | spec.md SC-010 / tasks T053 | "Legible from 10 m" not translated into concrete sizes in the task. | T053: presentation body text ≥ 24 px, star count ≥ 96 px. |
| A1 | Duplication | LOW | spec.md FR-025 / FR-028 | Reset local data appears in both. | Acceptable: FR-028 refines FR-025; no action. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | Yes | T040, T066 | |
| FR-002 | Yes | T040, T066 | |
| FR-003 | Yes | T063, T066 | |
| FR-004 | Yes | T005, T066 | |
| FR-005 | Yes | T028, T040, T041 | |
| FR-006 | Yes | T026, T028 | |
| FR-007 | Yes | T028 | |
| FR-008 | Yes | T028, T038 | |
| FR-009 | Yes | T026, T034 | |
| FR-010 | Yes | T036 | |
| FR-011 | Yes | T037, T038 | |
| FR-012 | Partial | T036, T037 | see D1 |
| FR-013 | Yes | T036, T037 | |
| FR-014 | Yes | T056, T057 | |
| FR-015 | Yes | T009, T038 | |
| FR-016 | Yes | T038 | see F1 |
| FR-017 | Yes | T027 | |
| FR-018 | Yes | T027, T038 | |
| FR-019 | Yes | T035 | |
| FR-020 | Yes | T038, T059 | |
| FR-021 | Yes | T064, T060 | |
| FR-022 | Yes | T038 | |
| FR-023 | Yes | T033, T078 | |
| FR-024 | Yes | T032, T033 | |
| FR-025 | Yes | T063, T066 | |
| FR-026 | Yes | T009, T010 | |
| FR-027 | Yes | T064, T061 | |
| FR-028 | Yes | T063 | |
| FR-029 | Yes | T038, T065 | |
| FR-030 | Yes | T011 | |
| FR-031 | Yes | T044, T046 | |
| FR-032 | Yes | T051, T052 | |
| FR-033 | Yes | T048 | |
| FR-034 | Yes | T050 | |
| FR-035 | Yes | T058 | |
| FR-036 | Yes | T053 | |
| FR-037 | Yes | T031, T045 | |
| FR-038 | Partial | T030, T056 | see E2 |
| FR-039 | Yes | T068, T069 | |
| FR-040 | Yes | T028 | |
| FR-041 | Yes | T007 | |
| FR-042 | Yes | T005, T006, T081 | |
| FR-043 | Yes | T036 | |
| FR-044 | Yes | T005, T028 | |
| FR-045 | Yes | T004 | |
| FR-046 | Yes | T071, T076 | |
| FR-047 | Yes | T073–T075 | |
| FR-048 | Yes | T079 | |
| SC-003 | Yes | T025, T059 | |
| SC-004 | Partial | T042 | see E3 |
| SC-005 | Yes | T061 | |
| SC-006 | No | — | see E1 |
| SC-007 | Yes | T075 | |
| SC-008 | Yes | T071 | |
| SC-009 | Yes | T081 | |
| SC-010 | Partial | T053 | see B1 |

(SC-001 and SC-002 are live-outcome measures, excluded from buildable coverage.)

**Constitution Alignment Issues:** D1 (Principle I enforcement relies only on prompting).

**Unmapped Tasks:** none (T001–T004, T078–T083 are setup/polish).

**Metrics:**

- Total Requirements: 48 FR + 8 buildable SC = 56
- Total Tasks: 83
- Coverage % (requirements with ≥1 task): 98% (55/56; SC-006 uncovered)
- Ambiguity Count: 1
- Duplication Count: 1
- Critical Issues Count: 0

## Next Actions

- No CRITICAL issues: implementation may proceed after addressing the two HIGH findings (F1, D1),
  which are cheap plan/task edits.
- Suggested edits: update plan.md state-machine notes (F1); amend T037 (D1), T023 (E1), T030/T056
  (E2), T042 (E3), T053 (B1); clarify timeout maximum in plan.md (F2).

## Remediation applied

The operator's standing instruction was to proceed autonomously and make reasonable decisions
without re-confirmation, so the agent approved and applied the suggested remediation for F1, D1,
E1, E2, E3, B1 and F2 by manual edits to `plan.md` and `tasks.md` (no Spec Kit command was used
for these edits). A1 was accepted as-is.
