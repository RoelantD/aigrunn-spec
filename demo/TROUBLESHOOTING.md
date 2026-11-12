# Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Preflight `aoc: session cookie is not logged in` | `AOC_SESSION` expired or was copied wrong | Log in again in the browser, copy the `session` cookie into `aps-data\.env`, restart the backend window |
| Run paused: "Advent of Code session expired or invalid" | Same as above, mid-run | Update `.env`, restart the backend (`start-live-app.ps1`), click **Resume** |
| `workhorse: HTTP 401/403` | Missing role or wrong tenant | `az login` with the operator account; check the *Cognitive Services OpenAI User* role on the account |
| `escalation: HTTP 404` | Wrong `ESCALATION_DEPLOYMENT` or base URL | Base URL must be `https://<res>.services.ai.azure.com/anthropic`; the deployment name is the name you chose, not the model id |
| `escalation` fails at deployment time | Subscription not eligible for Claude, or region | `azd env set DEPLOY_CLAUDE false`, then run without escalation, or choose an eligible subscription/region |
| Model note "structured output not accepted … used JSON-in-text fallback" | The Foundry Claude endpoint rejected `output_config.format` | Informational only; the adapter switched automatically |
| `sandbox authorization failed … Session Executor` | Missing *Azure ContainerApps Session Executor* role on the pool | Assign the role (it is in `infra/modules/roles.bicep`); allow ~5 min for propagation |
| Preflight `outbound network is ALLOWED` | Pool created with egress enabled | Recreate the pool with `sessionNetworkConfiguration.status = EgressDisabled` (as in `infra/`) |
| Run paused "model service unavailable … (HTTP 429)" | Foundry quota or TPM exhausted | Raise capacity, wait, then **Resume**; no solving attempt was consumed |
| Part shows **Waiting for cooldown** | The website asked us to wait after an answer | Nothing to do; the run continues on its own at the deadline (hourglass on the cell) |
| Part **FAILED** "submission limit reached" | 3 judged wrong answers | Pause, click **Retry Dn Pn** (resets counters; rejected answers stay blocked), Resume |
| Run paused "unexpected submission response" | Website wording changed or there was an error page | Check `GET /api/runs/<id>/submissions`; reconcile by opening the day page in the browser; then Resume |
| `Port 8765 is already in use` | App already running, or a stale process | `Get-NetTCPConnection -LocalPort 8765` → `Stop-Process -Id <pid>` |
| Dashboard wifi icon red | SSE disconnected (backend restarted) | It reconnects automatically and resumes from the last event id; refresh if needed |
| `show-checkpoint.ps1` asks to type `discard` | You edited files in the walkthrough | Type `discard` (changes are stashed, not lost) or cancel and commit them elsewhere |
| Cost shows $0.00 | Prices not configured | Set `*_PRICE_*_PER_MTOK` in `.env` (verify current Foundry pricing) |
| Backend crashed or laptop slept | — | `start-live-app.ps1` → run shows *paused (interrupted)* → **Resume**; uncertain submissions are reconciled first |

Logs: the backend window prints structured JSON with secrets redacted. All state is in
`aps-data\solver.db` (SQLite). Puzzle text and inputs are in `aps-data\cache\`.
