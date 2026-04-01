# Coffee Time Saver — AI-Powered Daily PM Assistant

> **Course project addressing User Story 1 (The Daily Project Manager) and User Story 2 (The Project Risk Checker)**

---

## Project Context

This prototype was built in response to the following government challenge:

> *"Large organizations face a unique mix of bureaucratic, security, architectural, and organizational constraints that make AI adoption fundamentally more difficult than in the private sector. The assistant cannot rely on clean, real-time, unified data sources — unstructured and fragmented data is locked in Word documents, emails, PDFs, images, and more."*

Our team chose to address **two user stories**:

### User Story 1 — The Daily Project Manager
> *"As a Project Manager, I want a daily assistant that consolidates key activity from meetings, emails, chats, and task lists so that I can quickly understand what happened, what requires follow-up, and what to prepare next — without navigating multiple tools."*

### User Story 2 — The Project Risk Checker
> *"As a Technical Authority, I want a 'Project Risk Simulator' that identifies risk not just from documentation, by reading transcripts and detecting inconsistencies between what is written in project plans and what is said in meetings, so that I can uncover risk that may not appear in formal status reports."*

---

## What the System Does

**Coffee Time Saver** is a bilingual (EN/FR) web application that acts as an AI-powered daily assistant for Project Managers working in document-heavy environments. It ingests unstructured data from multiple sources — uploaded files, emails, and meeting notes — and surfaces a prioritized, consolidated view every morning.

### Addressing User Story 1

| Capability | How it works |
|---|---|
| **Daily AI Briefing** | Every morning, the system reads all current tasks and emails, then calls an LLM to write a natural-language narrative summary in English and French — not a template, but genuine AI-generated prose |
| **Unified Task View** | Tasks from manual entry, uploaded documents, meeting minutes, and emails all appear in a single ranked list |
| **LLM Task Prioritization** | Every time a task changes, the LLM re-reads all task titles, deadlines, and sources and re-ranks the list by actual importance — not just a numeric field |
| **Email Pipeline** | The system polls a configured inbox via IMAP, extracts action items from email bodies using LLM, and creates tasks automatically with `source=email` |
| **Document Pipeline** | Uploaded PDFs, DOCX, XLSX, and TXT files are parsed, chunked, and processed by an LLM that extracts action items as tasks with `source=document` |
| **Scheduled Task Visibility** | Tasks can be set to appear only after a future date (e.g. a go-live checklist that surfaces 30 days before cutover) |
| **WebSocket Notifications** | When a file finishes processing or a project match is suggested, a real-time notification appears in the UI without requiring a page refresh |

### Addressing User Story 2

| Capability | How it works |
|---|---|
| **Risk Analysis** | The Risk Analyzer reads all documents, emails, and tasks for a project, then runs a layered LLM pipeline: chunk-level summarization → document-level aggregation → risk identification from a structured evidence pack |
| **Inconsistency Detection** | Document summaries are compared pairwise using the LLM to surface contradictions, scope drift, and undocumented gaps between what is written in project plans and what is described in meeting minutes or emails |
| **Evidence Traceability** | Every identified risk includes `source_documents` and `source_quotes` — the direct passages from source material that support the finding |
| **Confidence Scoring** | Each risk carries an LLM self-reported confidence score, then adjusted by evidence density (how many document chunks corroborate the finding) |
| **Exportable Report** | The full report can be downloaded as a PDF or DOCX for steering committee distribution |

---

## Architecture

```
Browser (React 18 + TypeScript)
        │  REST + WebSocket
        ▼
FastAPI Backend (Python 3.12)
        │
        ├── PostgreSQL 16 + pgvector   (structured data + vector embeddings)
        ├── Redis                       (cache + Celery message broker)
        └── Celery Workers              (async: file parsing, LLM calls, email polling)
```

### Backend Modules

| Module | Responsibility |
|---|---|
| `modules/briefing` | Daily briefing generation (template → LLM strategy) |
| `modules/tasks` | Task CRUD + LLM-powered sorting |
| `modules/file_processing` | PDF / DOCX / XLSX / TXT parsing pipeline |
| `modules/ingestion` | Chunking, language detection, embedding generation |
| `modules/email_bot` | IMAP polling, email parsing, task extraction |
| `modules/tools/risk_analyzer` | Multi-stage risk analysis pipeline |
| `modules/llm_gateway` | Unified LLM interface (OpenAI / Claude / Ollama) |
| `modules/dashboard` | Metrics aggregation for the daily dashboard |

### Key Design Decisions

- **Strategy Pattern** — Task sorting, briefing generation, text structuring, and email intelligence each have a hardcoded/regex fallback and an LLM-powered implementation, switchable via `.env` flags. The system degrades gracefully if no LLM is configured.
- **Async-first** — All LLM calls, file parsing, and email polling run through Celery workers. FastAPI endpoints return immediately and push results via WebSocket.
- **No file storage** — Uploaded files are deleted after text extraction. The extracted text is the sole source of truth, avoiding compliance concerns around document retention.
- **Auditable** — All write operations are logged to an `audit_logs` table. Every risk finding includes direct quotes from source documents.
- **Bilingual** — All AI-generated content (briefings, risk summaries) is produced in both English and French.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Zustand, react-i18next |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL 16, pgvector (1536-dim embeddings) |
| Queue | Celery + Redis |
| LLM | Configurable: OpenAI-compatible (OpenRouter), Claude, or Ollama |
| Auth | JWT (access + refresh tokens), RBAC |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker Desktop

### Quick Start

**1. Start the database and Redis:**
```bash
docker run -d --name cts-db -p 5432:5432 \
  -e POSTGRES_DB=coffee_time_saver \
  -e POSTGRES_USER=cts \
  -e POSTGRES_PASSWORD=cts_password \
  pgvector/pgvector:pg16

docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
```

**2. Set up and start the backend:**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python seed.py --demo
uvicorn main:app --reload
```

**3. Start the Celery worker** (required for file processing and email pipelines):
```bash
# In a new terminal, from the backend/ directory:
celery -A tasks worker --loglevel=info --pool=solo
```

**4. Start the frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and log in with `pm@example.com / pm123456`.

**5. Configure LLM** (required for AI features):

Log in as `admin@example.com / admin123456`, go to **Settings → LLM**, and add a configuration with `name=primary`. OpenRouter (OpenAI-compatible) is recommended.

> For the full setup guide, see [`STARTUP_GUIDE_EN.md`](STARTUP_GUIDE_EN.md).
> For demo instructions, see [`DEMO_HANDBOOK.md`](DEMO_HANDBOOK.md).

---

## Demo Data

To load clean, realistic demo data before a presentation:

```bash
cd backend
python seed_showcase.py
```

This resets the database and inserts 3 projects, 10 tasks, 3 documents, and 2 emails. The Daily Briefing is generated live by the LLM on the first Dashboard load.

---

## Accounts

| Role | Email | Password |
|---|---|---|
| Project Manager | pm@example.com | pm123456 |
| Admin | admin@example.com | admin123456 |

> All tasks, documents, and emails belong to the PM account. Log in as PM to see the full demo.

---

## Repository Structure

```
├── backend/
│   ├── core/               # Auth (JWT/RBAC), DB engine, WebSocket, exceptions
│   ├── modules/            # Business logic — one directory per feature
│   ├── tasks/              # Celery async task definitions
│   ├── migrations/         # Alembic schema migrations
│   ├── seed.py             # Creates admin + PM users
│   ├── seed_showcase.py    # Loads clean demo data (wipes existing)
│   └── main.py             # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios API client layer
│   │   ├── components/     # UI components
│   │   ├── pages/          # Page-level components
│   │   ├── store/          # Zustand global state
│   │   └── locales/        # i18n strings (en.json, fr.json)
│   └── index.html
├── STARTUP_GUIDE_EN.md     # Full setup instructions
├── DEMO_HANDBOOK.md        # Demo script and talking points
└── README.md               # This file
```
