# Preflight checklist

None of the steps below submit an answer or request a locked Part 2.

## The day before

- [ ] `git -C <parent>\agentic-puzzle-solver tag --list "demo/*"` shows all 8 tags.
- [ ] `.\scripts\setup-demo.ps1` has run. `aps-live` is at `demo/07-complete` and `aps-walkthrough` exists.
- [ ] `aps-data\.env` is filled in: `AOC_SESSION`, `AOC_CONTACT`, endpoints, deployment names, prices.
- [ ] `az login` works on the presenter laptop with the account that holds the role assignments.
- [ ] `.\scripts\preflight.ps1 -Days <range>` ends in **PASS**, and shows each of these:
  - `aoc` reports logged in, plus the unsolved days.
  - `workhorse` and `escalation` replied.
  - `sandbox` shows "egress blocked".
  - `range` shows that unsolved parts exist.
- [ ] Optional: `-Preload` to cache pages and inputs that are already accessible. This is paced and
      never fetches a locked Part 2.
- [ ] Foundry quota: Global Standard TPM is enough. The defaults are 100k for Sol and 25k for Opus.
- [ ] Do a full test start: `.\scripts\start-live-app.ps1`, start a run for **one** unsolved day,
      watch it reach "Advent of Code accepted the answer", then **Pause**. This uses up a real
      unsolved part, so choose the demo range around it. That run becomes your **backup recording**
      for replay.
- [ ] Checkpoint dry-run: `show-checkpoint.ps1` through every step, then `return-to-complete.ps1`,
      while the solver keeps running.
- [ ] The `AOC_SESSION` cookie expires roughly monthly. Re-copy it if preflight fails.

## Forty-five minutes before

- [ ] Laptop on power. Sleep is disabled. The display scale suits the projector, and `/present`
      reads well at 100%.
- [ ] `.\scripts\preflight.ps1 -Days <range>` → PASS.
- [ ] `.\scripts\start-live-app.ps1` (if it is not already running). Both windows are open; leave
      them alone.
- [ ] Browser tab 1: the dashboard. Tab 2: `/present`. Fullscreen works.
- [ ] VS Code is open on `aps-walkthrough` at `demo/00-initial` (`show-checkpoint.ps1 initial`).
      Copilot Chat is signed in.
- [ ] Notifications are muted. The `.env` window is closed: the session cookie must never be on screen.

## Must not happen

- Running during an active Advent of Code event.
- Showing `aps-data\.env`, the DevTools cookie panel, or `az account get-access-token` output on screen.
