# Replay guide

Replay plays back a **genuine recorded run** from `aps-data\solver.db`. It is a safety net for when
something you want to show did not happen live: a repair, an escalation or a rejected answer.

## What a replay is

- It copies the source run's persisted events into a new run with `mode = replay` and plays them at
  1–100× speed. Gaps between events are capped at 2 s.
- It calls **no** external service: no Advent of Code, no Foundry, no sandbox. An automated test
  checks this (`backend/tests/e2e/test_replay.py`).
- Every replayed event carries `replay: true`.
- Every view shows a persistent orange banner: **"REPLAY of recorded run #N — not live"**.
- The runs list marks it `replay of #N`.
- The code inspector only shows revisions that the replay timeline has reached.

## Recording a backup

A backup is simply a real run you did earlier, for example during the preflight test start. Prefer a
run that contains a repair or an escalation. Check this with the activity feed or with
`GET /api/runs/<id>/events`. Nothing needs exporting: the recording lives in `solver.db`.

## Using it on stage

1. Dashboard → **Runs**.
2. On the recorded live run, click **Replay**. It starts at 10× speed.
3. Say it out loud: *"This is a replay of a run recorded on <date>; the live run is still going in the
   other tab."*
4. To return, open **Runs**, then the live run, or go to `/present/<live run id>`.

API equivalent: `POST /api/runs/<id>/replay {"speed": 10}`.

Replays can be deleted from the runs list. That removes only local data.
