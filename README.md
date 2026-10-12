# ai-customer-support-agent

AI Customer Support Agent with a FastAPI backend, Next.js frontend, and a mini Telegram bot.

## Structure

- `backend/` — FastAPI API, agent, RAG, Telegram bot
- `frontend/` — Next.js web chat and dashboard

## Quick start

### Backend

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Copy `backend/.env.example` to `backend/.env` and set your database / LLM settings.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Telegram bot

1. Set `TELEGRAM_BOT_TOKEN` in `backend/.env`
2. From `backend/`:

```powershell
uv run python scripts/run_telegram_bot.py
```

### Admin user

```powershell
cd backend
uv run python scripts/create_admin.py
```
