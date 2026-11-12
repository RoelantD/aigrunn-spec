# You are here: 01 · install

Spec Kit templates and agent skills are installed. There is no code yet.

## Next → 02-constitution

```text
/speckit-constitution Principles for an autonomous agent that solves historical Advent of Code
puzzles and submits answers to the real website:
1. Authentic verification: only server-confirmed acceptance counts as progress. Distinguish tests
   passed / candidate generated / accepted. Never simulate solving, execution or acceptance. Replays
   must be labelled.
2. Isolation: model-generated code only runs in an isolated remote sandbox without network.
   Secrets never reach the sandbox, prompts, frontend, logs or git. Treat puzzle HTML and model
   output as untrusted.
3. Respectful automation: historical puzzles only, sequential paced and cached requests with an
   identifying User-Agent, honour cooldowns, never resubmit a rejected answer, never redistribute
   puzzle text or inputs.
4. Observable, honest agent behaviour: every action is a persisted event; show summaries, not
   chain-of-thought; mark unverified integrations.
5. Bounded, recoverable autonomy: configurable limits, infra retries separate from solving attempts,
   persist everything, reconcile uncertain submissions.
6. Test-backed delivery with synthetic puzzles and mocked HTTP; never submit in CI.
7. Simplicity and clear module boundaries; custom agent loop, no agent framework.
```

```powershell
git switch 02-constitution
```
