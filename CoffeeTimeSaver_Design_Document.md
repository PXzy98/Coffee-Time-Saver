# Coffee Time Saver — System Design Document

## 1. Project Overview

### 1.1 Vision
Coffee Time Saver is a web application for Project Managers that consolidates key activity from meetings, emails, chats, and task lists into a single daily assistant. The system helps PMs quickly understand what happened, what requires follow-up, and what to prepare next — without navigating multiple tools.

### 1.2 Target Users
- **Admin**: System administrator who configures LLM endpoints, manages projects, and controls data visibility across users.
- **PM (Project Manager)**: Day-to-day user who manages projects, reviews daily briefings, tracks tasks, uploads documents, and uses analytical tools.

### 1.3 Phased Delivery
- **Phase 1 — Daily PM Assistant**: Dashboard, task management, file ingestion, daily briefing, email bot, bilingual support (EN/FR).
- **Phase 2 — Project Risk Analyzer**: Unified risk modelling, cross-document inconsistency detection, and downloadable risk report with confidence scores.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────┐     ┌──────────────────────────────────┐     ┌────────────────┐
│                  │     │          BACKEND (FastAPI)        │     │                │
│   FRONTEND       │◄───►│                                  │◄───►│  PostgreSQL    │
│   React + TS     │ WS  │  ┌─────────┐  ┌──────────────┐  │     │  + pgvector    │
│                  │ REST│  │ Auth    │  │ Module       │  │     │                │
│  - Dashboard     │     │  │ (RBAC)  │  │ Registry     │  │     └────────────────┘
│  - TodoList      │     │  ├─────────┤  ├──────────────┤  │
│  - Projects      │     │  │ File    │  │ LLM Unified  │  │     ┌────────────────┐
│  - Tools         │     │  │ Ingest  │  │ Gateway      │  │     │  IMAP Email    │
│  - Settings      │     │  ├─────────┤  ├──────────────┤  │◄────│  Server        │
│  - Upload        │     │  │ Email   │  │ Embedding    │  │     └────────────────┘
│                  │     │  │ Bot     │  │ Service      │  │
└─────────────────┘     │  └─────────┘  └──────────────┘  │
                        └──────────────────────────────────┘
```

### 2.2 Deployment Stack (Docker Compose)

| Container         | Image / Base       | Port  | Purpose                          |
|-------------------|--------------------|-------|----------------------------------|
| `frontend`        | node:20-alpine     | 3000  | React dev server / Nginx prod    |
| `backend`         | python:3.12-slim   | 8000  | FastAPI application server       |
| `db`              | postgres:16        | 5432  | PostgreSQL + pgvector extension  |
| `redis`           | redis:7-alpine     | 6379  | Task queue broker, cache, pub/sub|
| `celery-worker`   | (same as backend)  | —     | Async task processing            |
| `celery-beat`     | (same as backend)  | —     | Scheduled tasks (email polling)  |

### 2.3 Key Technology Choices

| Layer       | Technology              | Rationale                                       |
|-------------|-------------------------|-------------------------------------------------|
| Frontend    | React 18 + TypeScript   | Component model, ecosystem, user preference     |
| State Mgmt  | Zustand                 | Lightweight, no boilerplate                     |
| i18n        | react-i18next           | Mature EN/FR bilingual support                  |
| Backend     | FastAPI (Python 3.12)   | Async-native, auto OpenAPI docs, modular        |
| ORM         | SQLAlchemy 2.0 + Alembic| Async support, mature migration system          |
| Task Queue  | Celery + Redis          | Async heavy processing (LLM, OCR, file parsing) |
| Realtime    | WebSocket (FastAPI)     | Dashboard push updates, task status changes     |
| Database    | PostgreSQL 16 + pgvector| Single DB for relational + vector data          |
| Auth        | JWT (access+refresh)    | Stateless, OAuth-ready token structure          |

---

## 3. Authentication & Authorization

### 3.1 RBAC Model

```
┌─────────┐       ┌──────────┐       ┌──────────────┐
│  User   │──M:N──│  Role    │──M:N──│  Permission  │
└─────────┘       └──────────┘       └──────────────┘
```

**Roles (Phase 1):**
- `admin` — Full system access, LLM config, project visibility control, user management.
- `pm` — Access own projects, tasks, upload files, use tools, view shared data.

**Permission Examples:**
- `project:read:own`, `project:read:shared`, `project:write:own`
- `settings:llm:write` (admin only)
- `tools:risk_simulator:execute`
- `admin:user:manage`

### 3.2 Auth Flow (Phase 1 — JWT)

```
[Login Form] → POST /api/auth/login (email+password)
            ← { access_token (15min), refresh_token (7d) }

[Every Request] → Authorization: Bearer <access_token>
               → Backend validates JWT, extracts user_id + roles

[Token Refresh] → POST /api/auth/refresh (refresh_token)
               ← { new access_token }
```

### 3.3 OAuth Upgrade Path (Phase 2+)

The JWT structure already uses standard claims (`sub`, `roles`, `exp`). To add OAuth:
1. Add `/api/auth/oauth/{provider}/callback` endpoints.
2. Map OAuth provider identity to internal User record.
3. Issue same internal JWT after OAuth flow completes.
4. No frontend changes needed — token format remains identical.

**Prepared abstractions:**
- `AuthProvider` interface in backend: `LocalAuthProvider` (Phase 1), `OAuthProvider` (future).
- User table has `auth_provider` and `external_id` columns from day one.

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- Users & Auth
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),          -- NULL if OAuth-only
    display_name    VARCHAR(100) NOT NULL,
    preferred_lang  VARCHAR(2) DEFAULT 'en',  -- 'en' or 'fr'
    auth_provider   VARCHAR(20) DEFAULT 'local',
    external_id     VARCHAR(255),          -- for OAuth
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE roles (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL  -- 'admin', 'pm'
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id INT REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE permissions (
    id   SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL  -- 'project:read:own'
);

CREATE TABLE role_permissions (
    role_id       INT REFERENCES roles(id),
    permission_id INT REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- Projects
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    status          VARCHAR(20) DEFAULT 'active',  -- active, on_hold, completed, archived
    owner_id        UUID REFERENCES users(id),
    is_shared       BOOLEAN DEFAULT FALSE,  -- admin-controlled visibility
    metadata        JSONB DEFAULT '{}',     -- flexible project attributes
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_members (
    project_id UUID REFERENCES projects(id),
    user_id    UUID REFERENCES users(id),
    role       VARCHAR(20) DEFAULT 'member',  -- 'lead', 'member', 'viewer'
    PRIMARY KEY (project_id, user_id)
);

-- Tasks / Todo
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) NOT NULL,
    project_id      UUID REFERENCES projects(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    priority        INT DEFAULT 50,          -- 0-100, computed by sorting module
    due_date        DATE,
    is_completed    BOOLEAN DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    source          VARCHAR(20) DEFAULT 'manual',  -- manual, email, briefing, meeting
    sort_score      FLOAT,                   -- computed by TodoSorter module
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Documents & Ingestion
-- Original files are deleted immediately after text extraction.
-- Only the extracted full_text and derived chunks/embeddings are retained.
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    uploaded_by     UUID REFERENCES users(id),
    filename        VARCHAR(500) NOT NULL,     -- original filename (for display only)
    mime_type       VARCHAR(100),
    file_size_bytes BIGINT,
    full_text       TEXT,                      -- ★ complete extracted plain text (sole source of truth)
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    source          VARCHAR(20) DEFAULT 'upload',   -- upload, email
    doc_type        VARCHAR(20) DEFAULT 'general',  -- general, plan, meeting_transcript, scope, report
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    content_text    TEXT NOT NULL,
    content_lang    VARCHAR(2),               -- detected: 'en' or 'fr'
    structured_data JSONB,                    -- parsed structured output
    embedding       vector(1536),             -- pgvector column
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Daily Briefings
CREATE TABLE daily_briefings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    date        DATE NOT NULL,
    content_en  TEXT,
    content_fr  TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Emails (original body text and HTML are always preserved)
CREATE TABLE emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      VARCHAR(500) UNIQUE,      -- IMAP message ID
    from_address    VARCHAR(255),
    to_addresses    TEXT[],
    cc_addresses    TEXT[],
    subject         VARCHAR(1000),
    body_text       TEXT,                      -- ★ original plain text body (never discarded)
    body_html       TEXT,                      -- ★ original HTML body (never discarded)
    received_at     TIMESTAMPTZ,
    processed       BOOLEAN DEFAULT FALSE,
    project_id      UUID REFERENCES projects(id),  -- auto-linked if detected
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Email Attachments (track each attachment separately, link to documents pipeline)
CREATE TABLE email_attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id        UUID REFERENCES emails(id) ON DELETE CASCADE,
    document_id     UUID REFERENCES documents(id),  -- links to file processing pipeline
    filename        VARCHAR(500) NOT NULL,
    mime_type       VARCHAR(100),
    file_size_bytes BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    action      VARCHAR(100) NOT NULL,    -- 'file.upload', 'settings.llm.update', 'module.invoke'
    entity_type VARCHAR(50),              -- 'document', 'task', 'project', etc.
    entity_id   VARCHAR(255),
    details     JSONB DEFAULT '{}',
    ip_address  INET,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);

-- LLM Configuration (admin-managed)
CREATE TABLE llm_configs (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,  -- 'primary', 'embedding', 'fallback'
    provider    VARCHAR(20) NOT NULL,          -- 'openai', 'claude', 'ollama'
    api_url     VARCHAR(500) NOT NULL,
    api_key     VARCHAR(500),                  -- encrypted at rest
    model       VARCHAR(100) NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Module Registry (for dynamic "Other Tools" page)
CREATE TABLE tool_modules (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(100) UNIQUE NOT NULL,  -- 'risk-simulator', 'scope-drift'
    name_en     VARCHAR(200) NOT NULL,
    name_fr     VARCHAR(200) NOT NULL,
    description_en TEXT,
    description_fr TEXT,
    icon        VARCHAR(50),                   -- icon identifier
    api_endpoint VARCHAR(200) NOT NULL,        -- '/api/tools/risk-simulator'
    is_enabled  BOOLEAN DEFAULT TRUE,
    sort_order  INT DEFAULT 0,
    config      JSONB DEFAULT '{}',            -- module-specific settings
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 Core Tables Overview

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | id, email, password_hash, preferred_lang, auth_provider |
| `roles` / `user_roles` | RBAC role assignments | name (admin, pm), user_id, role_id |
| `permissions` / `role_permissions` | Fine-grained permissions | code (project:read:own), role_id |
| `projects` | Project records | name, status, owner_id, is_shared, metadata (JSONB) |
| `project_members` | User-project associations | project_id, user_id, role (lead/member/viewer) |
| `tasks` | Todo items | title, priority, due_date, is_completed, sort_score, source |
| `documents` | Ingested file metadata + full text | filename, full_text, status, source, doc_type |
| `document_chunks` | Parsed text chunks + embeddings | content_text, content_lang, embedding (vector), structured_data |
| `daily_briefings` | Cached daily briefings | user_id, date, content_en, content_fr |
| `emails` | Ingested emails | message_id, subject, body_text, body_html, project_id |
| `email_attachments` | Email attachment tracking | email_id, document_id, filename |
| `audit_logs` | System-wide audit trail | action, entity_type, entity_id, details (JSONB) |
| `llm_configs` | LLM endpoint settings | provider, api_url, api_key (encrypted), model |
| `tool_modules` | Dynamic tool registry | slug, name_en, name_fr, api_endpoint, is_enabled |

### 4.3 Vector Index

The `document_chunks` table includes a pgvector column (`vector(1536)`) with an IVFFlat index using cosine similarity. This enables semantic search across all ingested documents for risk analysis, scope drift detection, and smart briefing generation.

### 4.4 Key Design Notes

- All primary keys are UUID for distributed-readiness and security (non-sequential).
- JSONB columns (`metadata`, `details`, `config`) provide schema flexibility for evolving requirements.
- Bilingual content stored in paired columns (`content_en`/`content_fr`, `name_en`/`name_fr`).
- Soft delete via `is_active` / `status` fields rather than hard DELETE.
- Timestamps use `TIMESTAMPTZ` for timezone-aware storage.
- Original files are not retained on disk — `documents.full_text` is the sole source of truth after extraction.

---

## 5. Backend Architecture

### 5.1 Project Structure

```
backend/
├── main.py                         # FastAPI app entry, CORS, lifespan
├── config.py                       # Settings via pydantic-settings
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
│
├── core/                           # Shared infrastructure
│   ├── auth/
│   │   ├── jwt.py                  # Token creation/validation
│   │   ├── dependencies.py         # get_current_user, require_role()
│   │   ├── providers.py            # AuthProvider interface + LocalAuth
│   │   └── password.py             # bcrypt hashing
│   ├── database.py                 # Async SQLAlchemy engine + session
│   ├── models/                     # SQLAlchemy ORM models (all tables)
│   ├── logging.py                  # Structured logging + audit trail
│   ├── websocket.py                # WS connection manager + broadcast
│   └── exceptions.py               # Custom exception handlers
│
├── modules/                        # ★ MODULAR BUSINESS LOGIC ★
│   ├── __init__.py                 # Module registry auto-discovery
│   ├── base.py                     # BaseModule abstract class
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── router.py               # GET /api/dashboard
│   │   ├── service.py              # Aggregate data for dashboard
│   │   └── schemas.py              # Pydantic response models
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── router.py               # CRUD /api/tasks
│   │   ├── service.py              # Task business logic
│   │   ├── sorter.py               # ★ SWAPPABLE: hardcoded → LLM sort
│   │   └── schemas.py
│   │
│   ├── projects/
│   │   ├── __init__.py
│   │   ├── router.py               # CRUD /api/projects
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   ├── briefing/
│   │   ├── __init__.py
│   │   ├── router.py               # GET /api/briefing/today
│   │   ├── service.py              # ★ SWAPPABLE: template → LLM gen
│   │   └── schemas.py
│   │
│   ├── file_processing/
│   │   ├── __init__.py
│   │   ├── router.py               # POST /api/files/upload
│   │   ├── service.py              # Orchestrates parse → ingest → store
│   │   ├── parsers/                # ★ SWAPPABLE parser implementations
│   │   │   ├── base.py             # FileParser interface
│   │   │   ├── pdf_parser.py       # PyMuPDF → future: OCR/LLM
│   │   │   ├── docx_parser.py      # python-docx
│   │   │   ├── xlsx_parser.py      # openpyxl
│   │   │   └── text_parser.py      # Plain text / markdown
│   │   └── schemas.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── service.py              # Text → structured data pipeline
│   │   ├── chunker.py              # Text splitting strategy
│   │   ├── structurer.py           # ★ SWAPPABLE: regex → LLM extraction
│   │   ├── embedder.py             # Generate vector embeddings
│   │   └── language_detect.py      # EN/FR detection (langdetect lib)
│   │
│   ├── email_bot/
│   │   ├── __init__.py
│   │   ├── service.py              # IMAP polling + processing
│   │   ├── imap_client.py          # IMAP connection handling
│   │   ├── processor.py            # Parse email → extract tasks/docs
│   │   └── schemas.py
│   │
│   ├── llm_gateway/
│   │   ├── __init__.py
│   │   ├── service.py              # ★ Unified LLM interface
│   │   ├── providers/
│   │   │   ├── base.py             # LLMProvider abstract class
│   │   │   ├── openai_provider.py  # OpenAI-compatible API
│   │   │   ├── claude_provider.py  # Anthropic API
│   │   │   └── ollama_provider.py  # Ollama local API
│   │   └── schemas.py              # Unified request/response models
│   │
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── router.py               # GET/PUT /api/settings
│   │   └── service.py
│   │
│   └── tools/                      # ★ DYNAMICALLY REGISTERED TOOLS
│       ├── __init__.py             # Tool registry + auto-discovery
│       ├── base.py                 # BaseTool abstract class
│       └── risk_analyzer/          # Phase 2 — single merged module
│           ├── __init__.py
│           ├── router.py           # POST run, GET status, GET download
│           ├── schemas.py          # RiskItem, InconsistencyItem, RiskReport
│           ├── analyzer.py         # ★ ALL risk logic in ONE file (iterable)
│           └── report_generator.py # Format report as PDF/DOCX for download
│
├── tasks/                          # Celery async tasks
│   ├── __init__.py                 # Celery app config
│   ├── file_tasks.py               # Async file processing
│   ├── email_tasks.py              # Periodic IMAP polling
│   ├── briefing_tasks.py           # Daily briefing generation
│   └── embedding_tasks.py          # Async vectorization
│
└── migrations/                     # Alembic migrations
    └── versions/
```

### 5.2 Module System Design

Every business module implements a standard interface:

```python
# modules/base.py
from abc import ABC, abstractmethod
from fastapi import APIRouter

class BaseModule(ABC):
    """All backend modules extend this."""

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier, e.g. 'tasks', 'risk-simulator'."""

    @property
    @abstractmethod
    def router(self) -> APIRouter:
        """FastAPI router with this module's endpoints."""

    @abstractmethod
    async def initialize(self) -> None:
        """Called on app startup. Load config, warm caches, etc."""

    @abstractmethod
    async def health_check(self) -> dict:
        """Return module health status."""
```

**Auto-discovery on startup:**
```python
# main.py (simplified)
for module_dir in Path("modules").iterdir():
    if module_dir.is_dir() and (module_dir / "__init__.py").exists():
        mod = importlib.import_module(f"modules.{module_dir.name}")
        if hasattr(mod, "module_instance"):
            app.include_router(mod.module_instance.router)
            await mod.module_instance.initialize()
```

### 5.3 Swappable Component Pattern

Each module that needs future upgrades uses a **Strategy Pattern**:

```python
# modules/tasks/sorter.py

class TaskSorterStrategy(ABC):
    @abstractmethod
    async def sort(self, tasks: list[Task], user: User) -> list[Task]: ...

class HardcodedSorter(TaskSorterStrategy):
    """Phase 1: Priority + due date + source weight."""
    async def sort(self, tasks, user):
        return sorted(tasks, key=lambda t: (
            -t.priority,
            t.due_date or date.max,
            SOURCE_WEIGHTS.get(t.source, 0)
        ))

class LLMSorter(TaskSorterStrategy):
    """Phase 2: LLM-evaluated priority."""
    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway

    async def sort(self, tasks, user):
        prompt = build_sort_prompt(tasks, user)
        result = await self.llm.complete(prompt)
        return parse_sorted_tasks(result)

# Config determines which is active:
# TASK_SORTER_STRATEGY=hardcoded | llm
```

**Same pattern applies to:**
- `file_processing/parsers/` — PyMuPDF today → OCR/LLM tomorrow
- `ingestion/structurer.py` — regex today → LLM extraction tomorrow
- `briefing/service.py` — template today → LLM generation tomorrow

**Swappable Component Summary:**

| Component | Phase 1 Strategy | Future Strategy | Config Key |
|-----------|-----------------|-----------------|------------|
| Task Sorting | HardcodedSorter (priority + due date) | LLMSorter (AI evaluation) | `TASK_SORTER_STRATEGY` |
| File Parsing (PDF) | PyMuPDF text extraction | OCR + LLM vision model | `PDF_PARSER_STRATEGY` |
| File Parsing (DOCX) | python-docx extraction | LLM document understanding | `DOCX_PARSER_STRATEGY` |
| Text Structuring | Regex + rule-based | LLM structured extraction | `STRUCTURER_STRATEGY` |
| Briefing Generation | Template-based | LLM-generated narrative | `BRIEFING_STRATEGY` |

### 5.4 LLM Unified Gateway

```python
# modules/llm_gateway/service.py

class LLMGateway:
    """Single interface for all modules to call LLMs."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        All internal modules call this. They never care about
        which provider is behind it.
        """
        config = await self._get_active_config(request.config_name)
        provider = self._get_provider(config.provider)  # openai/claude/ollama
        return await provider.complete(request, config)

    async def embed(self, texts: list[str], config_name="embedding") -> list[list[float]]:
        """Generate embeddings via active provider."""
        config = await self._get_active_config(config_name)
        provider = self._get_provider(config.provider)
        return await provider.embed(texts, config)

# Unified request (what modules send):
class LLMRequest(BaseModel):
    messages: list[Message]         # [{"role": "user", "content": "..."}]
    config_name: str = "primary"    # which llm_configs row to use
    temperature: float = 0.7
    max_tokens: int = 2000
    response_format: str | None = None  # "json" for structured output

# Unified response (what modules receive):
class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    provider: str
```

**Provider mapping (internal, transparent to callers):**

| Provider | API Style       | Endpoint Example                  |
|----------|-----------------|-----------------------------------|
| openai   | OpenAI SDK      | `https://api.openai.com/v1/`      |
| claude   | Anthropic SDK   | `https://api.anthropic.com/v1/`   |
| ollama   | OpenAI-compat   | `http://localhost:11434/v1/`       |

### 5.5 File Processing Pipeline

```
[Upload / Email Attachment]
        │
        ▼
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────────┐
│  File Parser     │────►│  Ingestion       │────►│  Database Storage     │
│  (pdf/docx/xlsx/ │     │  Module          │     │                      │
│   txt → text)    │     │                  │     │  - full_text (TEXT)  │
│                  │     │  - chunk text    │     │  - chunk rows        │
│  Strategy:       │     │  - detect lang   │     │  - embeddings        │
│  PyMuPDF (now)   │     │  - structure     │     │  - structured_data   │
│  OCR/LLM (later) │     │  - embed vectors │     │                      │
└─────────────────┘     └─────────────────┘     └──────────────────────┘
                                                         │
                                                         ▼
                                                 [Original file deleted
                                                  from temp storage]
```

**Data preservation principle:** The complete extracted plain text is stored in `documents.full_text` and is the sole source of truth. Original files are deleted from temporary storage immediately after successful text extraction — they are not retained on disk. Chunks, embeddings, and structured data are derived from `full_text` and can be re-generated if strategies are upgraded (e.g., switching from regex structurer to LLM structurer).

**Pipeline steps (async via Celery):**

1. **Parse** — Convert file to raw text using format-specific parser (PDF, DOCX, XLSX, TXT). Store complete text in `documents.full_text`.
2. **Chunk** — Split text into overlapping chunks (default 1000 tokens, 200 token overlap).
3. **Detect Language** — Classify each chunk as English or French (`langdetect` library).
4. **Structure** — Extract structured data (key entities, dates, action items) from chunks. Store in `document_chunks.structured_data` (JSONB).
5. **Embed** — Generate vector embeddings via LLM Gateway and store in `document_chunks.embedding`.
6. **Notify** — Push WebSocket event to frontend with processing status update.
7. **Cleanup** — Delete original file from temporary storage.

**Supported formats (Phase 1):**
- PDF → PyMuPDF (fitz)
- DOCX → python-docx
- XLSX/CSV → openpyxl / pandas
- TXT/MD → direct read

**Upgrade path:** Each parser implements `FileParser` interface. To switch PDF parsing to an OCR model, create `OcrPdfParser(FileParser)` and update config — no other code changes needed.

### 5.6 Email Bot

```python
# Celery Beat schedule: every 5 minutes
@celery_app.task
def poll_emails():
    """
    1. Connect IMAP, fetch unseen emails
    2. For each email:
       a. Store in emails table
       b. Extract attachments → file_processing pipeline
       c. Extract action items → tasks (via LLM or regex)
       d. Auto-link to project (if detectable from subject/body)
       e. Mark as processed
    3. Push WebSocket notification to affected users
    """
```

**IMAP Configuration (admin-managed via settings):**
- `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`
- `IMAP_FOLDER` (default: INBOX)
- `IMAP_POLL_INTERVAL_SECONDS` (default: 300)

### 5.7 Audit Logging

Every significant action is logged:

```python
# core/logging.py
async def audit_log(
    user_id: UUID,
    action: str,          # "file.upload", "settings.llm.update", "module.risk_simulator.invoke"
    entity_type: str,     # "document", "llm_config", "task"
    entity_id: str,
    details: dict = {},
    ip_address: str = None
):
    """Insert into audit_logs table. Also emit structured log."""
```

**Logged events include:**
- File uploads and processing results
- Settings changes (LLM config, IMAP config, project visibility)
- Module invocations (which tool, by whom, input summary)
- Auth events (login, logout, token refresh, failed attempts)
- Task CRUD operations
- Email bot processing results

---

## 6. Frontend Architecture

### 6.1 Page Structure

```
App
├── AuthLayout (login page)
│
└── MainLayout (authenticated)
    ├── Sidebar Navigation
    │   ├── Dashboard        (/dashboard)
    │   ├── Tasks            (/tasks)
    │   ├── Projects         (/projects)
    │   ├── Tools            (/tools)
    │   ├── Upload           (/upload)
    │   └── Settings         (/settings)      [admin sees extra tabs]
    │
    ├── TopBar
    │   ├── Language Toggle (EN/FR)
    │   ├── Notifications Bell
    │   └── User Menu (profile, logout)
    │
    └── Content Area (routed pages)
```

### 6.2 Page Details

#### Dashboard (`/dashboard`)
- **Daily Briefing Card** — Generated on first login, persists as visible card all day. Shows today's tasks, upcoming meetings, pending follow-ups, carried-over incomplete tasks from yesterday. Bilingual (rendered in user's preferred language).
- **Key Metrics** — Active projects count, overdue tasks, files processed today, unread emails.
- **Recent Activity Feed** — Real-time via WebSocket. Shows file uploads, task completions, email arrivals.
- **Quick Actions** — Add task, upload file, jump to project.

#### Tasks (`/tasks`)
- **Today's Task List** — Sorted by `sort_score` (computed by backend `TaskSorter` module). Includes tasks from: manual entry, email extraction, meeting follow-ups, yesterday's incomplete tasks.
- **Checkbox to complete** — Marks as done, triggers re-sort of remaining tasks.
- **Add New Task** — Inline form. On submit, backend re-sorts and pushes updated list via WebSocket.
- **Filters** — By project, by source, by priority.

#### Projects (`/projects`)
- **My Projects List** — All projects where user is a member.
- **Shared Projects** — Projects marked `is_shared=true` by admin (read-only for non-members).
- **Project Detail View** — Documents, tasks, team members, timeline, risk indicators (Phase 2).

#### Tools (`/tools`)
- **Dynamic Module Grid** — Fetches from `GET /api/tools/registry`. Each registered tool module appears as a card with icon, name, description (bilingual).
- **Clicking a card** opens the tool's UI (each tool provides its own React component or is rendered via a standard form template).
- **Phase 2 tools:** Risk Simulator, Scope Drift Detector.

#### Upload (`/upload`)
- **Multi-file dropzone** — Drag & drop or browse. Accepts PDF, DOCX, XLSX, CSV, TXT, MD.
- **Project selector** — Assign uploaded files to a project.
- **Upload progress** — Per-file progress bar.
- **Processing status** — After upload, shows real-time status (pending → processing → completed/failed) via WebSocket.

#### Settings (`/settings`)
- **Profile tab** — Display name, preferred language, password change.
- **Admin-only tabs:**
  - **LLM Configuration** — Add/edit LLM endpoints (provider, API URL, API key, model name). Test connection button.
  - **Email Bot Configuration** — IMAP host, port, credentials, polling interval. Test connection button.
  - **Project Visibility** — Toggle `is_shared` per project.
  - **User Management** — List users, assign roles.
  - **Module Management** — Enable/disable tool modules.

### 6.3 Real-Time Updates (WebSocket)

```
Frontend connects: ws://backend:8000/ws?token=<jwt>

Server pushes events:
{
  "type": "task.updated",
  "payload": { "tasks": [...sorted list...] }
}
{
  "type": "dashboard.refresh",
  "payload": { "metrics": {...}, "activity": [...] }
}
{
  "type": "file.status_changed",
  "payload": { "document_id": "...", "status": "completed" }
}
```

### 6.4 i18n Strategy

- All UI strings in `/src/locales/en.json` and `/src/locales/fr.json`.
- User's `preferred_lang` stored in DB and synced to frontend on login.
- Language toggle in TopBar updates both frontend locale and backend preference.
- Dashboard briefing content is generated in both languages and stored in `daily_briefings` table (`content_en`, `content_fr`).
- Tool module names/descriptions stored bilingually in `tool_modules` table.

### 6.5 Frontend Project Structure

```
frontend/
├── public/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes.tsx                  # React Router config
│   │
│   ├── api/                        # API client layer
│   │   ├── client.ts               # Axios instance with JWT interceptor
│   │   ├── auth.ts
│   │   ├── tasks.ts
│   │   ├── projects.ts
│   │   ├── dashboard.ts
│   │   ├── files.ts
│   │   ├── tools.ts
│   │   └── settings.ts
│   │
│   ├── store/                      # Zustand stores
│   │   ├── authStore.ts
│   │   ├── taskStore.ts
│   │   ├── projectStore.ts
│   │   └── uiStore.ts
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WS connection + event handling
│   │   ├── useAuth.ts
│   │   └── useTasks.ts
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── MainLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
│   │   ├── dashboard/
│   │   │   ├── BriefingCard.tsx
│   │   │   ├── MetricsGrid.tsx
│   │   │   └── ActivityFeed.tsx
│   │   ├── tasks/
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskItem.tsx
│   │   │   └── AddTaskForm.tsx
│   │   ├── projects/
│   │   ├── tools/
│   │   │   ├── ToolGrid.tsx
│   │   │   └── ToolCard.tsx
│   │   ├── upload/
│   │   │   ├── FileDropzone.tsx
│   │   │   └── UploadProgress.tsx
│   │   └── settings/
│   │       ├── LLMConfigForm.tsx
│   │       ├── EmailBotConfig.tsx
│   │       └── UserManagement.tsx
│   │
│   ├── locales/
│   │   ├── en.json
│   │   └── fr.json
│   │
│   └── types/
│       └── index.ts                # Shared TypeScript types
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## 7. API Endpoints Summary

### 7.1 Auth
| Method | Endpoint                    | Auth    | Description                  |
|--------|-----------------------------|---------|------------------------------|
| POST   | `/api/auth/login`           | Public  | Email + password login       |
| POST   | `/api/auth/refresh`         | Refresh | Refresh access token         |
| POST   | `/api/auth/logout`          | JWT     | Invalidate refresh token     |
| GET    | `/api/auth/me`              | JWT     | Current user profile         |

### 7.2 Dashboard
| Method | Endpoint                    | Auth | Description                  |
|--------|-----------------------------|------|------------------------------|
| GET    | `/api/dashboard`            | JWT  | Aggregated dashboard data    |
| GET    | `/api/briefing/today`       | JWT  | Today's daily briefing       |
| WS     | `/ws`                       | JWT  | Real-time event stream       |

### 7.3 Tasks
| Method | Endpoint                    | Auth | Description                  |
|--------|-----------------------------|------|------------------------------|
| GET    | `/api/tasks`                | JWT  | List user's tasks (sorted)   |
| POST   | `/api/tasks`                | JWT  | Create task + trigger re-sort|
| PATCH  | `/api/tasks/{id}`           | JWT  | Update task (complete, edit) |
| DELETE | `/api/tasks/{id}`           | JWT  | Delete task                  |

### 7.4 Projects
| Method | Endpoint                    | Auth  | Description                 |
|--------|-----------------------------|-------|-----------------------------|
| GET    | `/api/projects`             | JWT   | User's projects + shared    |
| GET    | `/api/projects/{id}`        | JWT   | Project detail              |
| POST   | `/api/projects`             | Admin | Create project              |
| PATCH  | `/api/projects/{id}`        | Admin | Update project              |
| PATCH  | `/api/projects/{id}/share`  | Admin | Toggle shared visibility    |

### 7.5 Files
| Method | Endpoint                    | Auth | Description                  |
|--------|-----------------------------|------|------------------------------|
| POST   | `/api/files/upload`         | JWT  | Upload files (multipart)     |
| GET    | `/api/files`                | JWT  | List user's uploaded files   |
| GET    | `/api/files/{id}/status`    | JWT  | Processing status            |

### 7.6 Tools
| Method | Endpoint                    | Auth | Description                  |
|--------|-----------------------------|------|------------------------------|
| GET    | `/api/tools/registry`       | JWT  | List enabled tool modules    |
| POST   | `/api/tools/{slug}/execute` | JWT  | Execute a tool module        |

### 7.7 Risk Analyzer (Phase 2)
| Method | Endpoint                                           | Auth | Description                          |
|--------|----------------------------------------------------|------|--------------------------------------|
| POST   | `/api/tools/risk-analyzer/run`                     | JWT  | Trigger full risk analysis           |
| GET    | `/api/tools/risk-analyzer/status/{report_id}`      | JWT  | Check analysis progress              |
| GET    | `/api/tools/risk-analyzer/report/{report_id}`      | JWT  | Get report data as JSON              |
| GET    | `/api/tools/risk-analyzer/report/{report_id}/download` | JWT | Download report as PDF/DOCX     |

### 7.8 Settings (Admin)
| Method | Endpoint                    | Auth  | Description                 |
|--------|-----------------------------|-------|-----------------------------|
| GET    | `/api/settings/llm`         | Admin | List LLM configurations     |
| PUT    | `/api/settings/llm/{id}`    | Admin | Update LLM config           |
| POST   | `/api/settings/llm/test`    | Admin | Test LLM connection         |
| GET    | `/api/settings/email`       | Admin | Email bot configuration     |
| PUT    | `/api/settings/email`       | Admin | Update email bot config     |
| GET    | `/api/settings/users`       | Admin | List all users              |
| PATCH  | `/api/settings/users/{id}`  | Admin | Update user role            |

---

## 8. Phase 2 — Project Risk Analyzer

### 8.1 Overview

The Project Risk Analyzer is a **single, self-contained tool module** located at `modules/tools/risk_analyzer/`. It consolidates all risk-related functionality (risk modelling, scope drift detection, cross-document inconsistency detection) into one code file for easy iteration. It is invoked via a single API endpoint and produces a downloadable report.

**Design principle:** All risk analysis logic lives in `modules/tools/risk_analyzer/analyzer.py` — one file that can be rewritten, swapped, or upgraded independently without affecting any other module. The router and schemas are thin wrappers around this core file.

### 8.2 Module Structure

```
modules/tools/risk_analyzer/
├── __init__.py             # Module registration (BaseTool implementation)
├── router.py               # POST /api/tools/risk-analyzer/run
│                           # GET  /api/tools/risk-analyzer/report/{id}/download
├── schemas.py              # Input/output Pydantic models
├── analyzer.py             # ★ CORE: All risk analysis logic in ONE file
│                           #   - Step 1: gather_project_data()
│                           #   - Step 2: risk_modelling()
│                           #   - Step 3: inconsistency_detection()
│                           #   - Step 4: generate_report()
└── report_generator.py     # Format final report as downloadable PDF/DOCX
```

### 8.3 Execution Flow

**Input:** `{ project_id: UUID, include_web_search: bool (optional, default false) }`

The analyzer runs two sequential steps, then generates a combined report:

```
┌─────────────────────────────────────────────────────────┐
│                  Step 0: Data Gathering                  │
│                                                         │
│  Retrieve from DB for the given project_id:             │
│  - All documents (full_text + chunks + embeddings)      │
│  - All emails (body_text + attachments' full_text)      │
│  - All tasks (title, description, status)               │
│  - Document types (plan, meeting_transcript, scope, etc)│
│                                                         │
│  ★ Uses original preserved text, NOT just vectors       │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Step 1: Risk Modelling (LLM)               │
│                                                         │
│  Feed project context (documents, emails, tasks) to LLM │
│  Prompt asks LLM to identify:                           │
│  - Risk factors (technical, schedule, resource, scope)  │
│  - Likelihood (1-5 scale)                               │
│  - Impact (1-5 scale)                                   │
│  - Suggested mitigation for each risk                   │
│  - Confidence score per risk (0.0 - 1.0)               │
│                                                         │
│  Optional: If include_web_search=true AND the LLM       │
│  Gateway supports tool_use / function_calling, provide  │
│  a web_search tool to the LLM so it can look up         │
│  industry benchmarks, known vendor issues, regulatory   │
│  changes, etc. If not supported, skip gracefully.       │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│        Step 2: Inconsistency Detection (LLM)            │
│                                                         │
│  Compare ALL saved materials for this project:          │
│  - Plan docs vs. meeting transcripts                    │
│  - Scope docs vs. recent emails                         │
│  - Earlier docs vs. later docs (chronological drift)    │
│  - Task descriptions vs. document content               │
│                                                         │
│  Use vector similarity to find related passage pairs,   │
│  then LLM evaluates each pair:                          │
│  - Consistent / Contradictory / Scope extension         │
│  - Specific quotes from both sides                      │
│  - Confidence score per inconsistency (0.0 - 1.0)      │
│                                                         │
│  Also detect:                                           │
│  - Commitments in meetings not reflected in plans       │
│  - Deadlines mentioned in emails that conflict w/ tasks │
│  - Scope items in plans not discussed in any meeting    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Step 3: Report Generation                    │
│                                                         │
│  Combine results into structured report:                │
│                                                         │
│  1. Executive Summary                                   │
│     - Overall risk level (Low / Medium / High / Critical)│
│     - Overall confidence score (0.0 - 1.0)             │
│     - Top 3 risks at a glance                          │
│                                                         │
│  2. Risk Register                                       │
│     Per risk:                                           │
│     - Description                                       │
│     - Category (technical/schedule/resource/scope)      │
│     - Likelihood × Impact → Risk Score                 │
│     - Confidence (0.0 - 1.0)                           │
│     - Source references (which documents/emails)        │
│     - Suggested mitigation                              │
│                                                         │
│  3. Inconsistency Report                                │
│     Per finding:                                        │
│     - Document A passage vs. Document B passage         │
│     - Type (contradiction / drift / gap)                │
│     - Confidence (0.0 - 1.0)                           │
│     - Recommendation                                    │
│                                                         │
│  4. Appendix                                            │
│     - Documents analyzed (list with dates)              │
│     - Methodology notes                                 │
│     - Confidence scoring explanation                    │
│                                                         │
│  Output formats: PDF (default) or DOCX                  │
│  ★ Downloadable via GET /report/{id}/download           │
└─────────────────────────────────────────────────────────┘
```

### 8.4 API Endpoints

| Method | Endpoint                                        | Auth | Description                          |
|--------|-------------------------------------------------|------|--------------------------------------|
| POST   | `/api/tools/risk-analyzer/run`                  | JWT  | Trigger analysis (returns report_id) |
| GET    | `/api/tools/risk-analyzer/status/{report_id}`   | JWT  | Check analysis progress              |
| GET    | `/api/tools/risk-analyzer/report/{report_id}`   | JWT  | Get report data as JSON              |
| GET    | `/api/tools/risk-analyzer/report/{report_id}/download` | JWT | Download report as PDF/DOCX  |

### 8.5 Report Output Schema

```python
class RiskItem(BaseModel):
    id: str
    description: str
    category: str                    # technical, schedule, resource, scope
    likelihood: int                  # 1-5
    impact: int                      # 1-5
    risk_score: float                # likelihood × impact, normalized 0-1
    confidence: float                # 0.0 - 1.0
    source_documents: list[str]      # document/email IDs referenced
    source_quotes: list[str]         # relevant excerpts from original text
    mitigation: str

class InconsistencyItem(BaseModel):
    id: str
    type: str                        # contradiction, drift, gap
    document_a: str                  # source doc ID
    passage_a: str                   # original text excerpt
    document_b: str
    passage_b: str
    explanation: str
    confidence: float                # 0.0 - 1.0
    recommendation: str

class RiskReport(BaseModel):
    report_id: UUID
    project_id: UUID
    generated_at: datetime
    overall_risk_level: str          # low, medium, high, critical
    overall_confidence: float        # 0.0 - 1.0 (weighted avg of all items)
    executive_summary: str
    risks: list[RiskItem]
    inconsistencies: list[InconsistencyItem]
    documents_analyzed: list[str]    # list of document filenames + dates
    methodology_notes: str
```

### 8.6 Web Search Integration (Optional)

The risk modelling step can optionally invoke web search to enrich risk analysis with external context. This is implemented as a **best-effort feature**:

- If the LLM Gateway's active provider supports function calling / tool use (OpenAI, Claude), the analyzer passes a `web_search` tool definition in the LLM request. The LLM can choose to search for industry-specific risks, vendor status, regulatory changes, etc.
- If the provider does not support tool use (e.g., some Ollama models), web search is silently skipped and the analysis proceeds using only internal project data.
- The user can disable this via `include_web_search: false` in the request.
- All web search queries and results are logged in audit_logs for transparency.

### 8.7 Iterability Design

The `analyzer.py` file is intentionally kept as **one self-contained file** with clear function boundaries:

```python
# modules/tools/risk_analyzer/analyzer.py

async def gather_project_data(project_id: UUID, db: AsyncSession) -> ProjectContext:
    """Collect all documents, emails, tasks, chunks for a project.
    Returns original text + embeddings + metadata."""

async def risk_modelling(context: ProjectContext, llm: LLMGateway,
                         web_search: bool = False) -> list[RiskItem]:
    """LLM-based risk identification from project materials.
    Optionally uses web search for external context."""

async def inconsistency_detection(context: ProjectContext,
                                   llm: LLMGateway) -> list[InconsistencyItem]:
    """Cross-compare all saved materials. Uses vector similarity
    to find related passages, then LLM evaluates consistency."""

async def generate_report(project_id: UUID, risks: list[RiskItem],
                          inconsistencies: list[InconsistencyItem],
                          context: ProjectContext) -> RiskReport:
    """Combine all findings into final report with overall confidence."""

async def run_full_analysis(project_id: UUID, db: AsyncSession,
                            llm: LLMGateway, web_search: bool = False) -> RiskReport:
    """Main entry point. Orchestrates all steps sequentially."""
    context = await gather_project_data(project_id, db)
    risks = await risk_modelling(context, llm, web_search)
    inconsistencies = await inconsistency_detection(context, llm)
    return await generate_report(project_id, risks, inconsistencies, context)
```

To iterate on the risk analysis approach, a developer only needs to modify `analyzer.py`. The router, schemas, and report generator remain stable.

---

## 9. Docker Compose Configuration

**Service Summary:**

| Service | Depends On | Volumes | Key Environment |
|---------|-----------|---------|-----------------|
| `frontend` | backend | — | `VITE_API_URL`, `VITE_WS_URL` |
| `backend` | db (healthy), redis | — | `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` |
| `db` | — | pgdata | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| `redis` | — | — | — |
| `celery-worker` | backend, redis | — | `DATABASE_URL`, `REDIS_URL` |
| `celery-beat` | backend, redis | — | `DATABASE_URL`, `REDIS_URL` |

The database uses the `pgvector/pgvector:pg16` image which includes the pgvector extension pre-installed. Health checks ensure the backend only starts after PostgreSQL is ready. No persistent file storage volume is needed since original files are deleted after text extraction.

```yaml
version: "3.9"

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000/ws
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://cts:cts_password@db:5432/coffee_time_saver
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=change-me-in-production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=coffee_time_saver
      - POSTGRES_USER=cts
      - POSTGRES_PASSWORD=cts_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cts -d coffee_time_saver"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://cts:cts_password@db:5432/coffee_time_saver
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - backend
      - redis

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://cts:cts_password@db:5432/coffee_time_saver
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - backend
      - redis

volumes:
  pgdata:
```

---

## 10. Development Roadmap

### Phase 1 — Daily PM Assistant (Weeks 1-8)

| Week | Milestone                                                    |
|------|--------------------------------------------------------------|
| 1-2  | Project scaffolding, Docker Compose, DB schema, Auth (RBAC+JWT) |
| 3    | File upload + parsing pipeline (PDF/DOCX/XLSX/TXT)          |
| 4    | Ingestion module (chunking, structuring, embedding, lang detect) |
| 5    | LLM Gateway + Admin settings UI for LLM/Email config        |
| 6    | Tasks module (CRUD, hardcoded sorting, WebSocket push)       |
| 7    | Dashboard + Daily Briefing generation + Email bot            |
| 8    | i18n (EN/FR), polish, integration testing, Docker optimization |

### Phase 2 — Risk Analyzer (Weeks 9-12)

| Week | Milestone                                                    |
|------|--------------------------------------------------------------|
| 9    | Document type classification (plan/transcript/scope) + data gathering layer |
| 10   | Risk modelling engine (analyzer.py: risk_modelling + optional web search) |
| 11   | Inconsistency detection engine (analyzer.py: cross-document comparison) |
| 12   | Report generation (PDF/DOCX download), frontend UI, end-to-end testing |

---

## 11. Key Design Decisions Summary

| Decision                    | Choice              | Reason                                          |
|-----------------------------|---------------------|-------------------------------------------------|
| Backend framework           | FastAPI             | Async-native, WebSocket support, auto-docs, modular |
| Database                    | PostgreSQL+pgvector | Single DB for relational + vector, simplifies ops |
| Vector storage              | pgvector extension  | No separate service to manage                   |
| Data preservation           | full_text in DB, originals deleted | Original files deleted after extraction; full_text is sole source of truth |
| Task queue                  | Celery + Redis      | Mature, handles heavy LLM/file processing async |
| Real-time                   | WebSocket           | True push for dashboard, task updates           |
| File parsing                | Python libs (Phase 1)| PyMuPDF, python-docx, openpyxl — swap to OCR later |
| Module pattern              | Strategy + Registry | Swap implementations without touching other code |
| Risk analysis               | Single analyzer.py file | All risk logic in one iterable file; router/schemas are stable wrappers |
| Auth                        | JWT with OAuth hooks| Works now, upgrades cleanly                     |
| i18n                        | react-i18next       | Mature, supports interpolation, lazy loading    |
| Deployment                  | Docker Compose      | Single command dev/demo setup                   |

---

## 12. For Claude Code: Implementation Notes

When implementing this system with Claude Code, follow these guidelines:

1. **Start with `docker-compose.yml`** and get all services booting before writing business logic.
2. **Database first**: Run Alembic migrations to create all tables before building API routes.
3. **Build modules independently**: Each module in `backend/modules/` should work in isolation. Test with `pytest` per module.
4. **Use the Strategy Pattern** for any component marked ★ SWAPPABLE in the directory tree. Always code to the interface, never the implementation.
5. **LLM Gateway is critical path**: Build it early (Week 5) since briefing, ingestion, and Phase 2 tools all depend on it.
6. **WebSocket events**: Define event types as an enum. Use Redis pub/sub so Celery workers can push events to the WebSocket manager.
7. **File processing is async**: Upload endpoint returns immediately with `document.id`. Processing happens in Celery. Frontend polls or listens via WebSocket.
8. **Tool registration**: Adding a new tool = create a new directory under `modules/tools/`, implement `BaseTool`, restart server. No manual wiring.
9. **Environment variables**: All secrets and configurable values via `pydantic-settings`. Never hardcode.
10. **Audit everything**: Wrap all write endpoints with the `audit_log()` helper.
