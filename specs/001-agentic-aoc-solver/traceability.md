# Traceability: requirement → implementation → tests

Produced for T082 (Constitution VI). Paths are relative to the repository root.
`be/` = `backend/`, `fe/` = `frontend/src/`, `t/` = `backend/tests/`.

| Req | Implementation | Tests |
|-----|----------------|-------|
| FR-001 run from URL/year + range | `be/app/api/runs.py` `CreateRunBody`; `fe/components/StartRunDialog.tsx` | `t/integration/test_api.py::test_create_requires_authorization` |
| FR-002 run-level authorization | `CreateRunBody._check`; StartRunDialog authorization checkbox | `test_api.py::test_create_requires_authorization` |
| FR-003 manual approval mode | `orchestrator._await_approval`, `run_manager.approve`, RunControls | `t/e2e/test_recovery.py::test_manual_approval_mode` |
| FR-004 limits | `be/app/config.py` `RunConfig`; `solver` extended timeout | `t/unit/test_security.py::test_run_config_bounds`, `t/e2e/test_final_day_and_timeouts.py::test_real_input_timeout_retries_with_configured_maximum` |
| FR-005 session validated | `AocClient.validate_session`, `create_run`, `_prepare` | `test_api.py::test_connections_verify_invalid_session` |
| FR-006 discovery | `aoc/parser.py` `parse_calendar_stars`, `parse_day_page` | `t/unit/test_aoc_parsing.py` |
| FR-007 fetch + cache | `AocClient.day_page/input` (cache dir) | `t/integration/test_aoc_client.py::test_pacing_cache_and_headers` |
| FR-008 no Part 2 before Part 1 | `_process_part` (refresh only after P1 VERIFIED) | `test_progression.py::test_part1_accepted_unlocks_part2_and_advances` |
| FR-009 examples, whitespace | `verification/examples.py` | `t/unit/test_verification.py` |
| FR-010 Part 1 context | `orchestrator._build_work`, `prompts.build_user_prompt` | `test_progression.py` (prompt assertion) |
| FR-011 distinct steps | `solver._one_attempt`, `orchestrator` states | e2e suite (event assertions) |
| FR-012 solve() contract, no hardcoding | `prompts.SYSTEM_PROMPT`, `harness.py`, `ledger.looks_hardcoded` | `test_repair.py::test_hardcoded_answer_is_rejected`, `test_verification.py::test_hardcode_guard` |
| FR-013 repair feedback | `solver._test_feedback` | `test_repair.py::test_failed_example_triggers_repair` |
| FR-014 escalation | `agents/policy.py`, `models/messages_adapter.py`, `solver.find_candidate` | `t/e2e/test_escalation.py`, `test_verification.py::test_policy_defaults` |
| FR-015 three success levels | `PartProgress.tests_passed/candidate_answer/accepted_answer`; `api/runs.ui_state` | `test_api.py` (ui_state), `fe` `components.test.tsx` star rule |
| FR-016 FAILED/BLOCKED + continue | `orchestrator._fail`, `_process_part` | `test_escalation.py::test_attempt_limit_marks_failed_and_blocks_part2_then_continues` |
| FR-017 response classification | `aoc/responses.py` | `test_aoc_parsing.py::test_classification*` |
| FR-018 acceptance only from response or state | `classify_submission`, `reconcile` | `test_aoc_parsing.py::test_http_200_alone_is_not_acceptance` |
| FR-019 never resubmit rejected / bounds | `verification/ledger.py`, `solver` ledger check | `test_wrong_answer.py`, `test_verification.py::test_ledger_duplicates_and_bounds` |
| FR-020 cooldowns | `orchestrator._wait_for_cooldown`, `Store.set_cooldown` | `test_recovery.py::test_cooldown_is_respected_then_same_answer_resubmitted` |
| FR-021 reconcile uncertain | `orchestrator.reconcile`, `run_manager.recover` | `test_recovery.py::test_connection_lost_after_send_*`, `test_restart_with_inflight_submission_reconciles` |
| FR-022 advance, Day 25 | `orchestrator._verified`, `_final_day_claim` | `test_progression.py`, `test_final_day_and_timeouts.py::test_day25_*` |
| FR-023 isolated sandbox | `execution/dynamic_sessions.py`, `infra/modules/sessionpool.bicep` (EgressDisabled), `preflight.check_sandbox` | `test_adapters.py::test_dynamic_sessions_*` (no secrets in code) |
| FR-024 structured exec result | `execution/base.ExecutionOutcome`, `harness.py` | `test_verification.py::test_harness_roundtrip_without_execution`, `test_adapters.py` |
| FR-025 controls | `run_manager.py`, `api/runs.py`, `fe/components/RunPanels.tsx` | `test_recovery.py::test_operator_pause_and_stop` |
| FR-026 persistence | `persistence/tables.py`, `repo.py` | entire e2e suite |
| FR-027 restart/resume | `run_manager.recover`, `orchestrator._prepare` | `test_recovery.py::test_restart_with_inflight_submission_reconciles` |
| FR-028 reset notice | `api/runs.delete_run`, `reset_local` | `test_api.py` (delete notice) |
| FR-029 run end conditions, no artificial delay | `orchestrator.run` | `test_recovery.py` (budget, outage) |
| FR-030 events | `events/bus.py`, `contracts/events.md` | all e2e (event assertions) |
| FR-031 realtime + resume | `api/events.py`, `fe/hooks/useRunStream.ts` | `test_api.py::test_full_run_over_http_with_sse_and_resume` |
| FR-032 dashboard summary | `fe/components/RunPanels.tsx` `StatusHeader` | manual visual check (see docs/TESTING.md) |
| FR-033 calendar states + stars | `fe/components/Calendar.tsx`, `api/runs.ui_state` | `fe/tests/components.test.tsx` |
| FR-034 code inspector | `fe/components/CodeInspector.tsx`, `/revisions` | `test_api.py` (revisions) |
| FR-035 escalation visible | `fe/components/Banners.tsx` `EscalationBanner` | `components.test.tsx` |
| FR-036 presentation view | `fe/pages/Presentation.tsx` | manual visual check |
| FR-037 metrics | `models/pricing.py`, `api/runs.metrics` | `test_api.py` (metrics), `test_recovery.py::test_budget_exhaustion_stops_run` |
| FR-038 no chain-of-thought | adapters discard reasoning/thinking | `test_adapters.py::test_responses_request_and_usage`, `test_messages_request_shape_and_thinking_discarded` |
| FR-039 replay | `be/app/replay.py`, `ReplayBanner` | `t/e2e/test_replay.py`, `components.test.tsx` |
| FR-040 respectful traffic | `AocClient` (lock, pacing, UA, Retry-After, backoff) | `test_aoc_client.py` |
| FR-041 allowlist + redirects | `security.py`, `AocClient(follow_redirects=False)` | `test_security.py::test_service_url_allowlist`, `test_aoc_client.py::test_redirects_are_not_followed` |
| FR-042 secrets backend-only | `config.Settings` (SecretStr), `logsetup` redaction, `EventBus` redaction | `test_security.py::test_redaction`, `test_api.py` (SC-009 scan, log scan) |
| FR-043 untrusted content separated | `agents/prompts.py` | `test_verification.py::test_prompt_separates_untrusted_content` |
| FR-044 private data outside Git | `.gitignore`, `APS_DATA_DIR` | `test_progression.py::test_personal_input_never_sent_to_models` (related) |
| FR-045 author stance documented | `README.md` | — (documentation) |
| FR-046 preflight | `be/cli.py`, `be/app/preflight.py`, `scripts/preflight.ps1` | `test_api.py::test_connections_verify_*` |
| FR-047 checkpoint walkthrough | `scripts/setup-demo.ps1`, `show-checkpoint.ps1`, `return-to-complete.ps1`, `demo.sh` | script verification log in docs/TESTING.md |
| FR-048 presenter docs | `demo/*.md` | — (documentation) |
| SC-003 | ledger + cooldown | `test_wrong_answer.py`, `test_recovery.py` |
| SC-004 | SSE | `test_api.py` (< 2 s per event) |
| SC-005 | recovery | `test_recovery.py::test_restart_*` |
| SC-006 | AocClient caching | `test_progression.py` (≤ 10 requests per day) |
| SC-009 | redaction | `test_api.py` secret scans |

Constitution: I (`ui_state`, star rule, replay flags), II (no local executor, sandbox only),
III (`AocClient`), IV (events, TESTING.md), V (`RunConfig`, recovery), VI (this matrix, test suites),
VII (module layout, ADR 0001).
