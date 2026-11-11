# ADR 0007: Two git worktrees and an external data directory

- **Status**: accepted (2026-11-11)
- **Context**: During the talk the solver keeps running while the presenter checks out historical
  checkpoints. Switching branches in the running app's directory would change its source files
  under the running process.
- **Decision**:
  - `scripts/setup-demo.ps1` creates two worktrees and a data directory as siblings of the repo:
    - `aps-live` is detached at `demo/07-complete` and runs on ports 8765 and 5175.
    - `aps-walkthrough` is moved between the `demo/NN-*` tags by `show-checkpoint.ps1`.
    - `aps-data` holds SQLite, the cache and `.env` (passed as `APS_ENV_FILE`).
  - Checkpoint switching stashes uncommitted changes, after asking for confirmation, before it
    switches. It also rewrites the git-ignored `.specify/feature.json`.
- **Consequences**: The walkthrough cannot affect the live process or its data. Both worktrees
  share one object store, so the tags always point at the original commits.
