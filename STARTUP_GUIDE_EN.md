# Coffee Time Saver - Local Startup and Testing Guide

## Prerequisites

| Tool | Required Version | Verification Command |
|------|------------------|----------------------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker Desktop | Any recent version | `docker --version` |

---

## 1. Startup Flow (Run Before Each Development Session)

### Step 1 - Start the Database and Redis Containers

```bash
docker start cts-db cts-redis
```

Verify that they are running:

```bash
docker ps
# You should see cts-db (5432) and cts-redis (6379) with status Up
```

> **First time setup?** If the containers do not exist yet, create them first:
> ```bash
> docker run -d --name cts-db -p 5432:5432 \
>   -e POSTGRES_DB=coffee_time_saver \
>   -e POSTGRES_USER=cts \
>   -e POSTGRES_PASSWORD=cts_password \
>   pgvector/pgvector:pg16
>
> docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
> ```
> Then initialize the database once:
> ```bash
> cd backend
> alembic upgrade head
> python seed.py --demo
> ```

---

### Step 2 - Start the Backend (FastAPI)

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# Returns: {"status":"ok"}
```

Backend logs are printed in real time in the terminal. API docs are available at: http://localhost:8000/docs

---

### Step 3 - Start the Frontend (React + Vite)

Open a new terminal:

```bash
cd frontend
npm install        # Only needed the first time or after package.json changes
npm run dev
```

After startup, open: **http://localhost:5173**

---

## 2. Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | admin123456 |
| PM (demo) | pm@example.com | pm123456 |

> If login fails, make sure the database is running and `python seed.py --demo` has been executed.

---

## 3. Run Tests

### Unit Tests (No Database Required)

```bash
cd backend
pytest tests/unit/ -v
# Current result: 31 passed
```

### Integration Tests (DB and Redis Containers Must Be Running)

```bash
cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test
pytest tests/unit/ tests/integration/ -v
```

---

## 4. Stop Services

```bash
# Stop backend/frontend: press Ctrl+C in the corresponding terminal

# Stop Docker containers while keeping data
docker stop cts-db cts-redis

# Permanently remove containers and data (use with caution)
docker rm cts-db cts-redis
```

---

## 5. Seed Demo Data

`seed.py` only creates users and does not include business data. To see the full Dashboard / Daily Briefing / Tasks experience, run the demo seed:

```bash
cd backend
python seed_demo.py
```

This will create:

- 3 projects (Metro Line 6, Office Relocation, ERP Upgrade)
- 12 tasks, including overdue and due-today items
- 3 emails
- 1 prewritten bilingual Daily Briefing

> If the data becomes inconsistent, run `python seed_demo.py --reset` to clear and rebuild it.

Log in with **pm@example.com** to view the complete demo experience.

---

## 6. Configure the LLM (Optional, Enables AI Features)

The following features require a working LLM configuration:

- Daily Briefing (when `BRIEFING_STRATEGY=llm`)
- Risk Analyzer (on the Tools page)
- Task Sorting (when `TASK_SORTER_STRATEGY=llm`)

### Steps

1. Log in with **admin@example.com**
2. Go to **Settings -> LLM**
3. Add one configuration entry:

| Field | OpenRouter Example | Local Ollama Example |
|------|---------------------|----------------------|
| name | `primary` | `primary` |
| provider | `openai` | `ollama` |
| api_url | `https://openrouter.ai/api/v1` | `http://localhost:11434` |
| api_key | `sk-or-v1-xxx` (your key) | (leave blank) |
| model | `google/gemini-2.5-flash` | `qwen3:8b` |
| is_active | ✅ | ✅ |

> OpenRouter is OpenAI-compatible, so set `provider` to `openai`.

### Backend `.env` Strategy Flags

```env
# template = no LLM required (default), llm = requires a configured LLM
BRIEFING_STRATEGY=template
TASK_SORTER_STRATEGY=hardcoded
STRUCTURER_STRATEGY=regex
```

After changing any value to `llm`, restart the backend for it to take effect. Risk Analyzer always uses an LLM and is not controlled by these flags.

---

## 7. Common Troubleshooting

| Symptom | Cause | Fix |
|--------|-------|-----|
| Frontend login shows `Network Error` | CORS mismatch or backend not running | Make sure the backend is running on port 8000; confirm `ALLOWED_ORIGINS` in `.env` includes `http://localhost:5173` |
| Backend startup shows `could not connect to server` | PostgreSQL container is not running | Run `docker start cts-db` |
| `alembic upgrade head` fails | DB is not ready or the URL is wrong | Wait until the container is fully started, then retry; check `DATABASE_URL` in `.env` |
| Port 5432/6379 is already in use | Another local service is using the same port | Run `docker ps -a` to inspect conflicting containers and stop them |

---

## 8. Port Overview

| Service | Port | Notes |
|--------|------|-------|
| Frontend (Vite dev) | 5173 | http://localhost:5173 |
| Backend (FastAPI) | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | `cts-db` container |
| Redis | 6379 | `cts-redis` container |
