# Showcase Preparation Plan

## 1. Current State Assessment

### Database Contents (as of 2026-04-01)

| Entity | Count | Issues |
|---|---|---|
| Users | 2 | OK — admin + demo PM |
| Projects | 5 | `test1` and `ASM Gate 2 Review` are leftover test data; 3 demo projects have `[DEMO]` prefix |
| Tasks | 30 | 12 tagged `[DEMO]`, 18 auto-extracted from documents (no prefix, inconsistent style) |
| Documents | 17 | Mix of demo stubs and real uploaded test files |
| Emails | 3 | All tagged `[DEMO]` |
| Briefings | 7 | Multiple dates, may be stale |

### Problems for a Live Demo

1. **`[DEMO]` prefix on everything** — immediately signals fake data to the audience
2. **`test1` project** — meaningless name visible in project list and task dropdowns
3. **`ASM Gate 2 Review`** — orphaned test project with no clear relationship to other data
4. **Document-extracted tasks** have different naming style than demo tasks — looks incoherent
5. **Dates are stale** — `seed_demo.py` uses `date.today()` at seed time; if seeded days ago, due dates are already overdue in ways that don't tell a good story
6. **Dashboard metrics are weak** — numbers are low and unbalanced, not enough to impress
7. **Only 1 briefing for "today"** — if today doesn't match the seed date, briefing page is empty

---

## 2. Showcase Data Plan

### 2.1 Cleanup Strategy

Create `seed_showcase.py` that:

1. Deletes all tasks, documents, emails, briefings, and projects (except user accounts and system tables like roles/permissions)
2. Re-inserts clean, realistic data with no `[DEMO]` prefix
3. Is idempotent — safe to run multiple times
4. Uses `date.today()` so dates are always fresh relative to the demo day

### 2.2 Projects (3)

| Project | Status | Owner | Shared | Story |
|---|---|---|---|---|
| Metro Line 6 Extension | active | admin | yes | Large infrastructure — high stakes, overdue items, contractor pressure |
| Office Relocation Q3 | active | pm | no | Internal ops — medium complexity, clear timeline |
| ERP System Upgrade | paused | admin | yes | Stalled vendor dependency — shows multi-status support |

Three projects is enough to demonstrate filtering, multi-project views, and different statuses without clutter.

### 2.3 Tasks (10 pre-seeded + live-demo additions)

**Pre-seeded tasks — already in the database when the demo starts:**

**Metro Line 6 Extension (3 tasks)**

| Title | Priority | Due | Source | Status | Notes |
|---|---|---|---|---|---|
| Approve revised ventilation specs (ECO-2241) | 75 | today +1 | meeting | open | |
| Send weekly progress report to city liaison | 50 | today -1 | manual | open (overdue) | |
| Confirm concrete pour schedule with contractor | 95 | today | email | completed | |

**Office Relocation Q3 (3 tasks)**

| Title | Priority | Due | Source | Status | Notes |
|---|---|---|---|---|---|
| Finalize floor plan with interior design team | 70 | today +2 | meeting | open | |
| Collect quotes from three moving companies | 55 | today +5 | manual | open | |
| Notify all staff of move timeline | 40 | today +7 | manual | completed | |

**ERP System Upgrade (2 tasks)**

| Title | Priority | Due | Source | Status | Notes |
|---|---|---|---|---|---|
| Follow up with SAP on delayed license renewal | 85 | today -2 | email | open (overdue) | |
| Reschedule data migration dry-run | 65 | today +10 | manual | open | |

**Personal — no project (2 tasks)**

| Title | Priority | Due | Source | Status | Notes |
|---|---|---|---|---|---|
| Prepare Q2 PM team capacity plan | 72 | today +9 | manual | open | |
| Prepare go-live checklist for ERP cutover | 85 | today +45 | manual | open | `scheduled_at = today +30` — invisible now, surfaces later |

**Pre-seed totals: 10 tasks** — 7 visible open (2 overdue), 2 completed, 1 hidden (scheduled_at in future)

**Tasks that will appear live during the demo (not pre-seeded):**

These are created by the system in real-time as the audience watches:

| Trigger | What happens | Source |
|---|---|---|
| Upload a PDF/DOCX file | LLM extracts action items → new tasks appear with `source=document` | document_intelligence.extract_tasks() |
| Upload a PDF/DOCX file | LLM suggests which project the file belongs to → WebSocket notification | document_intelligence.suggest_project() |
| Email arrives with attachment | Attachment saved as Document, ingestion pipeline runs | email_bot processor |
| Email arrives with meeting invite / action items | LLM extracts meeting events / action items → new tasks with `source=email` | email_intelligence.extract_tasks_from_email() |

This is far more impressive than pre-seeding these tasks — the audience sees the AI pipeline working end to end.

### 2.4 Documents (3 pre-seeded stubs + 1 live upload)

**Pre-seeded:**

| Filename | Project | Status | Type |
|---|---|---|---|
| geotechnical_survey_station3.pdf | Metro Line 6 | completed | report |
| ventilation_ECO2241_rev3.docx | Metro Line 6 | completed | specification |
| office_floorplan_v4.xlsx | Office Relocation | completed | general |

These give the dashboard a baseline "files processed" count and provide document context for risk analysis.

**Live during demo:**

- Upload a real PDF or DOCX (prepare one beforehand with clear action items in the text)
- The file processes → tasks appear → project suggestion notification pops up
- Audience sees the full pipeline in action

### 2.5 Emails (2 pre-seeded + live demo)

**Pre-seeded:**

| Subject | From | Project | Processed |
|---|---|---|---|
| RE: Concrete pour schedule — urgent confirmation needed | j.tremblay@tunnelcorp.ca | Metro Line 6 | yes |
| SAP license renewal — action required | licensing@sap.com | ERP Upgrade | no |

One processed (drives task context), one unprocessed (drives "unread emails" metric).

**Live during demo:**

To demonstrate the email → task pipeline, send a test email to the configured IMAP mailbox before/during the demo. The email should contain:

1. **An attachment** (PDF/DOCX) — demonstrates: email received → attachment extracted → document created in DB → ingestion pipeline runs
2. **A meeting invitation or clear action items in the body** — demonstrates: email body → LLM extracts tasks → tasks appear in task list with `source=email`

Example email to prepare:

```
Subject: Project Kickoff Meeting — April 15 Action Items
From: (your test sender)

Hi team,

Following today's kickoff meeting for the Office Relocation project, here are the action items:

1. Please confirm the server room decommission date by April 5
2. Schedule a walkthrough of the new building with facilities by next Monday
3. Follow up with the landlord on the early termination clause

The next meeting is scheduled for April 8 at 2:00 PM.

Regards
```

When Celery picks this up:
- Email row created in DB
- If attachment present: Document created, file pipeline runs, tasks extracted from document
- LLM extracts 3 tasks from the body → appear in task list
- LLM suggests project match (Office Relocation) → WebSocket notification
- Dashboard metrics update in real-time

### 2.6 Daily Briefing (LLM-generated)

The briefing is **not pre-seeded as static text**. Instead, `seed_showcase.py` does NOT insert a briefing row for today. When the PM first visits the Dashboard, `BriefingService.get_or_create_today()` finds no existing briefing and generates one on the fly.

With `BRIEFING_STRATEGY=llm`:
1. `TemplateBriefingStrategy` gathers the current tasks and emails into a structured list
2. `LLMBriefingStrategy` sends that list to the LLM, which rewrites it as a natural-language narrative
3. The result is saved and cached for the rest of the day

This means the briefing always reflects the actual seed data and is visibly AI-written (not a bullet list template). During the demo, the first Dashboard load may take 2-3 seconds longer while the LLM generates — this is expected and can be a talking point.

Fallback: if `BRIEFING_STRATEGY=template` or LLM is unavailable, a structured markdown briefing is generated from the template strategy.

### 2.7 Task Sorting (LLM-ranked)

With `TASK_SORTER_STRATEGY=llm`:
- Every time a task is created, updated, or completed, `TaskService._resort_and_save()` sends all visible tasks to the LLM
- The LLM ranks them by importance considering title, priority, due date, source, and context — not just a numeric sort
- The result is written back as `sort_score` and the task list re-orders accordingly

During the demo: after creating a new task or completing one, the task list visibly re-sorts. This is a good moment to explain: "The AI just re-evaluated all tasks and decided this new one is more urgent than the others."

**Bug fix required:** `get_sorter()` in `service.py` currently doesn't pass `llm_gateway` when strategy is `llm`, so the LLM sorter never activates. This is fixed as part of this plan (see Section 3.5).

Fallback: if LLM is unavailable, `LLMSorter` catches the exception and falls back to `HardcodedSorter` automatically.

### 2.8 Dashboard Metrics (expected at demo start)

| Metric | Expected Value | Source |
|---|---|---|
| Active projects | 2 | Projects with status=active (Metro, Office) |
| Overdue tasks | 2 | due_date < today and not completed |
| Pending tasks | 7 | Visible open tasks (excludes scheduled_at future task) |
| Files processed today | 3 | Documents with status=completed |
| Unread emails | 1 | Emails with processed=false |

These numbers will grow during the demo as documents are uploaded and emails arrive — which makes the dashboard feel alive.

---

## 3. Implementation

### 3.1 New file: `backend/seed_showcase.py`

Single script that:

1. Connects to database
2. Deletes all tasks, documents, emails, briefings, project_members, projects (preserves users, roles, permissions, system tables)
3. Inserts: 3 projects, 10 tasks, 3 documents, 2 emails, 1 briefing
4. Prints summary

Usage:

```bash
cd backend
python seed_showcase.py
```

Always does a clean reset + insert. Safe to re-run before every demo session.

### 3.2 Prepare demo files (manual, before demo day)

| File | Purpose | Content requirements |
|---|---|---|
| A PDF or DOCX for live upload | Demonstrate file → task extraction pipeline | Must contain 2-3 clear action items with deadlines in the text |
| A test email (send to IMAP mailbox) | Demonstrate email → task extraction pipeline | Body with action items + optional attachment |

### 3.3 Environment configuration for live demo

Ensure these are set in `.env`:

```
# --- LLM-powered features (all require at least one active LLM config in Settings) ---

# Task sorting: "llm" = AI ranks tasks by importance; "hardcoded" = numeric sort
TASK_SORTER_STRATEGY=llm

# Briefing generation: "llm" = AI narrative; "template" = structured bullet list
BRIEFING_STRATEGY=llm

# Email intelligence — set to "llm" to use LLM extraction (not regex fallback)
EMAIL_TASK_STRATEGY=llm
EMAIL_PROJECT_SUGGESTION=llm
TASK_PROJECT_ASSOCIATION=llm

# --- IMAP (required only if demoing email pipeline) ---
IMAP_HOST=...
IMAP_USER=...
IMAP_PASSWORD=...
```

### 3.4 No schema, migration, or frontend changes required

All data uses existing columns (including the new `scheduled_at`). The frontend already renders everything correctly.

### 3.5 Bug fix: LLM task sorter never activates

`TaskService._resort_and_save()` calls `get_sorter(settings.TASK_SORTER_STRATEGY)` but never passes `llm_gateway`. The `get_sorter()` function requires both `strategy="llm"` AND a `llm_gateway` instance to return the LLM sorter — without it, it silently falls back to hardcoded.

Fix: when `TASK_SORTER_STRATEGY == "llm"`, instantiate `LLMGateway(db)` and pass it to `get_sorter()`. This is a one-line change in `backend/modules/tasks/service.py`.

---

## 4. Demo Flow

### Phase 1: Static walkthrough (pre-seeded data)

1. **Login** as `pm@example.com / pm123456`
2. **Dashboard** — point out the 5 metrics; the daily briefing loads for the first time and is generated by the LLM in real-time (takes 2-3s, visibly AI-written narrative — not a bullet list); switch EN ↔ FR
3. **Tasks** — show sorted list (AI-ranked, not just numeric), demonstrate filters (project / source / priority), point out 2 overdue tasks
4. **Create a task manually** — fill in the form, use the "Show after" (scheduled_at) field; after submit, the task list visibly re-sorts as the AI re-evaluates all priorities
5. **Projects** — show the 3 projects, note the different statuses (active vs paused)

### Phase 2: Live AI pipeline (real-time, audience watches)

6. **Upload a document** — upload the prepared PDF/DOCX on the Upload page
   - Switch to Tasks → new tasks appear (extracted by LLM from the document, `source=document`)
   - A WebSocket notification suggests which project the document belongs to
   - Say: "The AI read the document, identified action items, and suggested the matching project — no manual work"

7. **Email arrives** — if IMAP is configured, the email you sent earlier gets picked up by Celery
   - Switch to Tasks → new tasks appear (`source=email`)
   - Dashboard metrics update (unread emails count changes)
   - Say: "The system polls the mailbox, extracts action items from emails, and even processes attachments through the same document pipeline"

### Phase 3: Advanced features

8. **Tools → Risk Analysis** — run on Metro Line 6 (has documents with context)
   - While it runs, navigate away to prove it persists (if riskStore fix is implemented)
   - Show the generated risk report with risk matrix, inconsistencies, mitigations

9. **Settings** — show LLM configuration (swap models), email bot settings

### Talking Points

- "Tasks come from three sources: manual entry, document uploads, and emails — all unified in one view"
- "The daily briefing is AI-generated in real-time as a natural-language narrative, not a template — and it's bilingual"
- "Task priority isn't just a number — every time something changes, the AI re-evaluates and re-ranks all tasks by actual importance"
- "Tasks can be scheduled to appear at a future date — the go-live checklist surfaces automatically 30 days before cutover"
- "When you upload a document, the AI extracts tasks and suggests which project it belongs to"
- "Emails are polled automatically — attachments go through the document pipeline, action items become tasks"
- "Risk analysis runs asynchronously in the background"

---

## 5. Pre-Demo Checklist

### Infrastructure
- [ ] PostgreSQL and Redis containers running
- [ ] `alembic upgrade head` (ensure all migrations applied)
- [ ] `python seed_showcase.py` (fresh data)

### Services
- [ ] Backend running: `uvicorn main:app --reload`
- [ ] Celery worker running: `celery -A tasks worker --loglevel=info --pool=solo`
- [ ] Frontend running: `npm run dev`

### Verification
- [ ] Login works at `pm@example.com / pm123456`
- [ ] Dashboard shows expected metrics (2 active projects, 2 overdue, 7 pending, 3 files, 1 unread)
- [ ] Briefing content matches current date
- [ ] Tasks page shows 7 open tasks (not 8 — the scheduled one is hidden)

### Demo materials
- [ ] Prepare one PDF/DOCX file with clear action items for live upload
- [ ] If demoing email pipeline: send test email to IMAP mailbox 5 min before demo starts
- [ ] At least one LLM config active in Settings (required for task extraction + risk analysis)
- [ ] `.env` has `EMAIL_TASK_STRATEGY=llm`, `EMAIL_PROJECT_SUGGESTION=llm`
