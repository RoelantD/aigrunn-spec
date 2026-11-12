# You are here: 10 · working

The solver runs live against the real models, the real sandbox and the real website.

## Run it

```powershell
cd backend; uv run uvicorn app.main:get_app --factory --port 8765
cd frontend; npm run dev
```
