# Coffee Time Saver — Local Startup and Testing Guide

## Prerequisites

| Tool | Required Version | Verification Command |
|------|------------------|----------------------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker Desktop | Any recent version | `docker --version` |

---

## 1. First-Time Setup (Run Once)

### Create Docker Containers

```bash
docker run -d --name cts-db -p 5432:5432 \
  -e POSTGRES_DB=coffee_time_saver \
  -e POSTGRES_USER=cts \
  -e POSTGRES_PASSWORD=cts_password \
  pgvector/pgvector:pg16

docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
```

### Initialize the Database

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python seed.py --demo
```

### Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## 2. Startup Flow (Four Terminals)

### Terminal 1 — Database & Redis

```bash
docker start cts-db cts-redis
```

Verify:
```bash
docker ps
# You should see cts-db (5432) and cts-redis (6379) with status Up
```

### Terminal 2 — Backend (FastAPI)

```bash
cd backend
uvicorn main:app --reload
```

Wait for: `Application startup complete.`

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### Terminal 3 — Celery Worker

```bash
cd backend
celery -A tasks worker --loglevel=info --pool=solo
```

Wait for: `celery@... ready.`

> **Must be run from the `backend/` directory.** `--pool=solo` is required on Windows.
>
> The Worker handles: file processing pipeline, email polling, LLM task re-sorting, daily briefing generation. Without the Worker, uploaded files will not produce tasks.

### Terminal 4 — Frontend (React + Vite)

```bash
cd frontend
npm run dev
```

Wait for: `Local: http://localhost:5173`

Open **http://localhost:5173** and log in with `pm@example.com / pm123456`.

---

## 3. Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | admin123456 |
| PM (demo) | pm@example.com | pm123456 |

> **Use the PM account for demos.** All tasks, documents, and emails belong to the PM account. The Admin account will show an empty task list.

---

## 4. Demo Data

### Load Clean Demo Data (Run Before Each Demo)

```bash
cd backend
python seed_showcase.py
```

This **completely wipes** all existing tasks, documents, emails, and projects, then inserts:
- 3 projects (Metro Line 6 Extension, Office Relocation Q3, ERP System Upgrade)
- 10 tasks (7 visible open, 2 completed, 1 hidden via scheduled_at)
- 3 document stubs (processed, with full text for Risk Analysis)
- 2 emails (1 processed, 1 unread)
- No pre-seeded briefing — the LLM generates it live on the first Dashboard load

> Safe to re-run before every demo session.

### Development Data (Non-Demo Use)

```bash
cd backend
python seed_demo.py          # Insert test data tagged [DEMO]
python seed_demo.py --reset  # Clear and re-insert
```

---

## 5. Scheduled Tasks via Celery Beat (Optional)

To enable automatic scheduled tasks (daily briefing generation, daily task re-sorting), open an additional terminal:

```bash
cd backend
celery -A tasks beat --loglevel=info
```

| Task | Schedule (UTC) |
|------|---------------|
| Generate Daily Briefing for all users | Every day at 06:00 |
| Re-sort all user tasks via LLM | Every day at 06:05 |
| Poll email inbox | Every 5 minutes |

> Without Beat running, email polling and daily re-sorting will not trigger automatically. Manual actions (uploading files, creating tasks) still trigger the Worker immediately.

---

## 6. Configure the LLM (Required for AI Features)

The following features require a working LLM configuration: Daily Briefing, Risk Analyzer, Task Sorting, document task extraction.

### Steps

1. Log in as **admin@example.com**
2. Go to **Settings → LLM**
3. Add one entry (the `name` field must be `primary`):

| Field | OpenRouter Example | Local Ollama Example |
|-------|--------------------|----------------------|
| name | `primary` | `primary` |
| provider | `openai` | `ollama` |
| api_url | `https://openrouter.ai/api/v1` | `http://localhost:11434` |
| api_key | `sk-or-v1-xxx` (your key) | (leave blank) |
| model | `google/gemini-flash-3` | `qwen3:8b` |
| is_active | ✅ | ✅ |

> OpenRouter is OpenAI-compatible — set `provider` to `openai`.

### `backend/.env` Strategy Flags

```env
TASK_SORTER_STRATEGY=llm        # hardcoded | llm
BRIEFING_STRATEGY=llm           # template | llm
EMAIL_TASK_STRATEGY=llm         # regex | llm
EMAIL_PROJECT_SUGGESTION=llm    # off | llm
TASK_PROJECT_ASSOCIATION=llm    # manual | llm
```

Restart the backend after changing any value.

---

## 7. Email Bot (Optional)

The email bot is optional. The backend runs normally without IMAP configuration — it simply will not poll for emails.

To enable it, add the following to `backend/.env`:

```env
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your-address@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_OWNER_EMAIL=pm@example.com   # Which user receives imported emails
```

For Gmail, enable two-factor authentication and generate an app-specific password.

The email bot status (configured / connected / unreachable) is shown in the top navigation bar of the UI.

---

## 8. Running Tests

### Unit Tests (No Database Required)

```bash
cd backend
pytest tests/unit/ -v
```

### Full E2E Showcase Test (Requires the Full Stack Running)

```bash
# Make sure the backend, Celery Worker, and frontend are all running
python run_showcase_tests.py
# Results are written to showcase_test_results.md
```

---

## 9. Stop Services

```bash
# Backend / Celery / Frontend: press Ctrl+C in each terminal

# Stop Docker containers (data is preserved)
docker stop cts-db cts-redis

# Permanently remove containers and data (use with caution)
docker rm cts-db cts-redis
```

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Frontend login shows `Network Error` | Backend not running, or CORS mismatch | Confirm the backend is running on port 8000; check that `ALLOWED_ORIGINS` in `.env` includes `http://localhost:5173` |
| Teammate gets `Network Error` on their machine | The frontend API URL is hardcoded to `localhost:8000`, which does not exist on another machine | In `frontend/.env.local`, set `VITE_API_BASE_URL=http://your-ip:8000`; add their access URL to `ALLOWED_ORIGINS` in `.env` |
| Uploaded file produces no tasks | Celery Worker is not running | Make sure Terminal 3 is running the Worker from the `backend/` directory |
| Backend startup: `No module named 'xxx'` | Dependencies not installed | Run `pip install -r requirements.txt -r requirements-dev.txt` |
| Backend startup: `could not connect to server` | PostgreSQL container is not running | Run `docker start cts-db` |
| `alembic upgrade head` fails | DB not ready or URL is wrong | Wait for the container to fully start, then retry; check `DATABASE_URL` in `.env` |
| Tasks page is empty after logging in | Logged in as Admin; tasks belong to the PM account | Log out and log in as `pm@example.com` |
| Risk Analysis keeps spinning | LLM is slow — normal duration is 60–130 seconds | Wait; you can navigate to another page and the result will be saved in the background |

---

## 11. Port Reference

| Service | Port |
|---------|------|
| Frontend (Vite) | 5173 |
| Backend (FastAPI) | 8000 |
| API Docs | 8000/docs |
| PostgreSQL | 5432 |
| Redis | 6379 |
