# Friendly Debt Tracker — Backend

FastAPI + SQLAlchemy REST API. No accounts, no PII: every request is scoped by
an anonymous device UUID sent in the `X-Device-UUID` header.

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell/Git Bash: .venv/Scripts/python.exe)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## Test

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Configuration (env vars)

| Variable        | Default                                  | Notes                                   |
|-----------------|------------------------------------------|-----------------------------------------|
| `DATABASE_URL`  | `sqlite:///./friendly_debt_tracker.db`   | Set to a Postgres DSN in production      |
| `CORS_ORIGINS`  | `*`                                      | Comma-separated allowed origins          |

No SQLite-only SQL is used, so switching to Postgres only requires changing
`DATABASE_URL` (and running migrations — `create_all` is used for the MVP).

## Endpoints

- `POST /device/register` — idempotent device registration
- `GET/POST /friends`, `GET/PATCH/DELETE /friends/{id}`, `POST /friends/{id}/settle`
- `GET/POST /entries`, `GET/PATCH/DELETE /entries/{id}`
- `GET /stats/summary`, `GET /stats/timeline?days=30`
- `GET /health`

All balances are **computed** from entries, never stored, so they can never
drift out of sync.
