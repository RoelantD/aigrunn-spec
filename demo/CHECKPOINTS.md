# Walkthrough steps (branches) and checkpoints (tags)

On stage you step through **branches** `00-start` … `10-working` in worktree B (`aps-walkthrough`).
Each branch holds **exactly the content of a real development stage**, plus a `NEXT_STEP.md` with the
prompt that leads to the next branch. This works like a cooking show: you show the prompt (paste it
into Copilot Chat, but don't send it), then switch to the branch that holds the recorded result.
Nothing is generated live, so the talk is predictable.

```powershell
.\scripts\show-checkpoint.ps1 -List          # all steps, current one marked
.\scripts\show-checkpoint.ps1 02-constitution  # or: 2, or: constitution
.\scripts\show-checkpoint.ps1 -Next          # one step forward (-Previous: back)
.\scripts\return-to-complete.ps1             # back to 10-working
```

| Step branch | Content = real stage | Prompt in its `NEXT_STEP.md` (leads to the next step) | Show on stage |
|-------------|----------------------|------------------------------------------------------|---------------|
| `00-start` | new root: title page only | `specify init` (install Spec Kit) | `README.md`, the ASCII title |
| `01-install` | tag `demo/00-initial` | `/speckit-constitution …` | `.specify/`, `.github/skills/speckit-*` |
| `02-constitution` | tag `demo/01-constitution` | `/speckit-specify …` | `.specify/memory/constitution.md` |
| `03-specify` | tag `demo/02-specify` | `/speckit-clarify` | `spec.md` (user stories, FR-019) |
| `04-clarify` | tag `demo/03-clarify` | `/speckit-plan …` (tech stack) | `spec.md` → `## Clarifications` |
| `05-plan` | tag `demo/04-plan` | `/speckit-checklist …` then `/speckit-tasks` | `plan.md`, `research.md`, `contracts/aoc-client.md` |
| `06-tasks` | commit `66357b8` | `/speckit-analyze`, then apply remediation | `tasks.md`, `checklists/submission-safety.md` |
| `07-analyze` | tag `demo/05-tasks` | `/speckit-implement` | `analysis.md` (2 HIGH findings) |
| `08-implement` | tag `demo/06-implement` | `/speckit-converge` ⇄ `/speckit-implement` | `orchestrator.py` `_submit()` |
| `09-converge` | tag `demo/07-complete` | live verification (`azd provision`, preflight, live tests) | `tasks.md` Phases 11–12, `traceability.md` |
| `10-working` | `main` when the branches were built | run it: preflight + `start-live-app.ps1` | `docs/TESTING.md` |

## What differs from the original history

- **The tags `demo/00` … `demo/07` are the original, untouched commits.** They are the provenance.
  The step branches are a separate linear chain whose *trees* reproduce those stages.
- **`00-start` is new.** The original repo started directly with `specify init`.
- **Copilot skills are present from `01-install` onwards.** That way `/speckit-…` autocompletes in
  Copilot Chat at every step. In the original run, the Copilot integration was installed during
  convergence.
- **The prompts in `NEXT_STEP.md` are the commands to type.** The stages were produced in Claude Code.
  The `/speckit-specify` text is the recorded feature input, and the other prompts restate what was
  asked. A model won't reproduce the output byte for byte, which is why each next branch holds the
  recorded result.

## Rebuilding the branches

The branches are generated, so rebuild them after `main` changes. This updates `10-working`:

```powershell
git -C ..\aps-walkthrough checkout --detach     # free the branch the walkthrough is on
python scripts\walkthrough\build_walkthrough.py
.\scripts\show-checkpoint.ps1 00-start -Force
```

Spec Kit tracks the active feature in `.specify/feature.json`, separately from the branch. That file
is git-ignored, so `show-checkpoint.ps1` writes
`{"feature_directory": "specs/001-agentic-aoc-solver"}` whenever the step contains the spec.
