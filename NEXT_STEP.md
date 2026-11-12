# You are here: 09 · converge

The spec and the code agree. Every requirement traces to code and to a test.

## Next → 10-working

```powershell
azd provision
cd backend
uv run python cli.py preflight --days 1-5
uv run pytest -m live_azure tests/live
```

```powershell
git switch 10-working
```
