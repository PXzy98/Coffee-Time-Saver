# Coffee Time Saver — Test Plan
**Date:** 2026-03-25
**Scope:** Phase 1 (Daily PM Assistant) + Phase 2 Risk Analyzer
**Overall completion:** ~92% of design document implemented

---

## Implementation Status Summary

| Area | Status | Notes |
|---|---|---|
| Backend core (FastAPI, auth, DB, WebSocket) | ✅ Complete | |
| All 10 backend modules + endpoints | ✅ Complete | |
| Risk Analyzer (core analysis) | ✅ Complete | |
| Frontend (all 8 pages) | ✅ Complete | |
| API client layer (frontend ↔ backend) | ✅ Complete | All endpoints matched |
| Document intelligence (task extract, project suggest) | ✅ Complete | |
| Celery file processing pipeline | ✅ Complete | Manual trigger only |
| Celery Beat schedule (email polling, briefing) | ⚠️ Scaffolded | Not wired to Beat |
| LLM Sorter (tasks) | ⚠️ Skeleton | Phase 2, not implemented |
| LLM Briefing | ❌ Not started | Phase 2 |
| Web search in risk analyzer | ❌ Not started | Phase 2 |
| Scope Drift Detector tool | ❌ Not started | Phase 2 |

---

## Prerequisites

### Minimum (backend only, no Celery)
```bash
docker run -d --name cts-db  -p 5432:5432 -e POSTGRES_DB=coffee_time_saver -e POSTGRES_USER=cts -e POSTGRES_PASSWORD=cts_password pgvector/pgvector:pg16
docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
cd backend
pip install -r requirements.txt
cp .env.example .env   # set JWT_SECRET etc.
alembic upgrade head
python seed.py --demo
python seed_demo.py
python inject_test_docs.py
uvicorn main:app --reload
```

### Full (with async file pipeline)
```bash
# same as above, then in a second terminal:
celery -A tasks worker --loglevel=info
```

### Test accounts
| Email | Password | Role |
|---|---|---|
| admin@example.com | admin123456 | admin |
| pm@example.com | pm123456 | pm |

---

## T1 — Authentication

| # | Test | Method | Expected |
|---|---|---|---|
| T1-1 | Login with valid credentials (pm user) | POST /api/auth/login | 200, access_token + refresh_token returned |
| T1-2 | Login with wrong password | POST /api/auth/login | 401 |
| T1-3 | Refresh token | POST /api/auth/refresh | 200, new access_token |
| T1-4 | Access protected endpoint without token | GET /api/tasks | 401 |
| T1-5 | Access admin endpoint as pm user | POST /api/projects | 403 |
| T1-6 | GET /api/auth/me returns current user | GET /api/auth/me | 200, user profile with roles |
| T1-7 | Frontend login page — valid login redirects to dashboard | Browser | Redirected, sidebar visible |
| T1-8 | Frontend — expired token triggers logout | Browser | Redirected to /login |

---

## T2 — Dashboard

| # | Test | Method | Expected |
|---|---|---|---|
| T2-1 | GET /api/dashboard returns metrics | GET /api/dashboard | 200, active_projects, overdue_tasks, pending_tasks, unread_emails |
| T2-2 | GET /api/briefing/today returns today's briefing | GET /api/briefing/today | 200, content_en and content_fr populated |
| T2-3 | Briefing shows correct date | GET /api/briefing/today | date field = today |
| T2-4 | Frontend dashboard renders briefing card | Browser | Briefing text visible, EN/FR toggle works |
| T2-5 | Frontend metrics grid shows non-zero counts | Browser | At least active_projects > 0 after seed_demo |
| T2-6 | Activity feed shows recent audit entries | Browser | Recent login actions visible |

---

## T3 — Tasks

| # | Test | Method | Expected |
|---|---|---|---|
| T3-1 | GET /api/tasks returns tasks list | GET /api/tasks | 200, array of TaskOut |
| T3-2 | Create task with title only | POST /api/tasks | 201, task created with UUID id |
| T3-3 | Create task with project_id | POST /api/tasks | 201, project_id set |
| T3-4 | Update task title | PATCH /api/tasks/{id} | 200, updated title |
| T3-5 | Mark task complete | PATCH /api/tasks/{id} {"is_completed": true} | 200, is_completed=true, completed_at set |
| T3-6 | Delete task | DELETE /api/tasks/{id} | 204 |
| T3-7 | Tasks sorted by sort_score | GET /api/tasks | Results ordered correctly |
| T3-8 | Filter tasks by project | GET /api/tasks?project_id=... | Only tasks for that project returned |
| T3-9 | Filter completed tasks | GET /api/tasks?completed=true | Only completed tasks |
| T3-10 | Frontend task list — create task via form | Browser | Task appears in list |
| T3-11 | Frontend — checkbox marks task complete | Browser | Task moves to completed state, strikethrough |
| T3-12 | Frontend — overdue tasks show warning color | Browser | Tasks past due_date highlighted |

---

## T4 — Projects

| # | Test | Method | Expected |
|---|---|---|---|
| T4-1 | List projects (pm user sees own + shared) | GET /api/projects | 200, array includes DEMO projects |
| T4-2 | Create project (admin) | POST /api/projects | 201, project returned with members array |
| T4-3 | Create project (pm user) | POST /api/projects | 403 |
| T4-4 | Get project detail | GET /api/projects/{id} | 200, members list populated |
| T4-5 | Update project description | PATCH /api/projects/{id} | 200, updated |
| T4-6 | Toggle is_shared | PATCH /api/projects/{id}/share | 200, is_shared toggled |
| T4-7 | Frontend project list renders | Browser | 3+ DEMO projects visible |
| T4-8 | Frontend project detail shows documents | Browser | Documents linked to project listed |

---

## T5 — File Upload & Processing

### 5a — Upload (manual trigger, no Celery required)
| # | Test | Method | Expected |
|---|---|---|---|
| T5-1 | Upload a PDF file | POST /api/files/upload | 201, document_id returned, status="pending" |
| T5-2 | Upload a DOCX file | POST /api/files/upload | 201 |
| T5-3 | Upload a TXT file | POST /api/files/upload | 201 |
| T5-4 | Upload unsupported file type | POST /api/files/upload (.exe) | 400 |
| T5-5 | List uploaded files | GET /api/files | 200, includes uploaded files |
| T5-6 | Check file status | GET /api/files/{id}/status | 200, status field |
| T5-7 | Frontend dropzone — drag and drop file | Browser | File appears in upload queue |
| T5-8 | Frontend — project selector pre-fills project_id | Browser | Dropdown lists DEMO projects |

### 5b — Pipeline (requires Celery worker)
| # | Test | Method | Expected |
|---|---|---|---|
| T5-9 | Upload PDF — Celery processes it | Upload via browser | Status changes pending→processing→completed |
| T5-10 | Completed doc has full_text set | DB query / GET /api/files | full_text not null |
| T5-11 | DocumentChunk rows created | DB | chunks with content_text, content_lang |
| T5-12 | WebSocket pushes file.status_changed event | Browser with WS connected | Status badge updates in real time |

---

## T6 — Document Intelligence (post-pipeline LLM features)

**Setup:** Run `python inject_test_docs.py` to load test documents with full_text.

| # | Test | Method | Expected |
|---|---|---|---|
| T6-1 | Task extraction on meeting notes | `python -c "... extract_tasks(...)"` | 5-10 tasks created with title, priority, due_date |
| T6-2 | Extracted tasks linked to correct project | DB check | task.project_id = document.project_id |
| T6-3 | Task source field = "document" | DB check | source="document" |
| T6-4 | Project suggestion on Metro Line doc | `suggest_project(...)` | WebSocket event pushed, match_type="existing", project="Metro Line 6" |
| T6-5 | Project suggestion on glossary (no match expected) | `suggest_project(...)` | No WebSocket event (match_type="none", confidence<0.5) |
| T6-6 | Project suggestion for new security doc | `suggest_project(...)` | match_type="new" or "none" (no matching project) |
| T6-7 | Frontend upload page shows project suggestion banner | Browser + Celery | Banner appears after file.status_changed with suggestion payload |
| T6-8 | Accept button sets project dropdown to suggested project | Browser | Dropdown updates to suggested project ID |

**Test files available in `test_data/autogenerate/`:**
- `kickoff_meeting_metro_line6.txt` → expect tasks + project suggestion: Metro Line 6
- `erp_upgrade_action_items.txt` → expect tasks + project suggestion: ERP System Upgrade
- `office_relocation_vendor_proposal.md` → expect tasks + project suggestion: Office Relocation Q3
- `erp_data_migration_checklist.md` → expect tasks (checklist items) + project suggestion: ERP System Upgrade
- `infrastructure_security_assessment.md` → expect tasks (security remediations) + no project match
- `general_reference_glossary.txt` → expect 0 tasks, no project suggestion (pure reference)

---

## T7 — LLM Gateway & Settings

| # | Test | Method | Expected |
|---|---|---|---|
| T7-1 | List LLM configs | GET /api/settings/llm | 200, configs with is_active flags |
| T7-2 | Active config is qwen3.5:9b | GET /api/settings/llm | ollama-qwen3.5-9b has is_active=true |
| T7-3 | Test LLM config (live ping) | POST /api/settings/llm/test | 200, success=true |
| T7-4 | Update LLM config | PUT /api/settings/llm/{id} | 200, updated |
| T7-5 | Create new LLM config | POST /api/settings/llm | 201, new config saved |
| T7-6 | LLM gateway routes to active provider | Any LLM-dependent endpoint | Response uses ollama-qwen3.5-9b |
| T7-7 | Frontend settings LLM tab lists configs | Browser (admin) | Table with configs + Test button |

---

## T8 — Risk Analyzer (Phase 2)

**Setup:** Use `ASM Gate 2 Review` project (project_id: `082a46f1-6e43-496b-8a7b-831e6f87c7d3`) which has 7 real PDFs.

| # | Test | Method | Expected |
|---|---|---|---|
| T8-1 | Run risk analysis via API | POST /api/tools/risk-analyzer/run | 200, report_id returned, status="running" |
| T8-2 | Poll status until completed | GET /api/tools/risk-analyzer/status/{id} | status changes running→completed (2-5 min) |
| T8-3 | Fetch completed report | GET /api/tools/risk-analyzer/report/{id} | 200, risks array non-empty, inconsistencies array non-empty |
| T8-4 | Report has risks with all required fields | JSON check | Each risk has id, title, description, probability_label, impact_label, risk_score, mitigation_strategies |
| T8-5 | Risk score is between 0.0 and 1.0 | JSON check | risk_score in [0.0, 1.0] |
| T8-6 | Report has executive summary | JSON check | executive_summary non-empty string |
| T8-7 | Report has overall_risk_level | JSON check | one of: low, medium, high, critical |
| T8-8 | Inconsistencies have type field | JSON check | type in: contradiction, drift, gap |
| T8-9 | Download PDF report | GET /api/tools/risk-analyzer/report/{id}/download?format=pdf | 200, application/pdf content-type |
| T8-10 | Download DOCX report | GET /api/tools/risk-analyzer/report/{id}/download?format=docx | 200, application/vnd.openxmlformats... |
| T8-11 | Frontend tools page shows Risk Analyzer card | Browser | Card visible in tools grid |
| T8-12 | Frontend — run analysis, see progress bar | Browser | Status polling shows "running" then "completed" |
| T8-13 | Frontend — report renders risk table | Browser | RSK-1, RSK-2... rows with probability/impact badges |
| T8-14 | Frontend — inconsistencies section populated | Browser | Inconsistency items with document names |
| T8-15 | Frontend — download PDF button works | Browser | PDF opens/downloads |
| T8-16 | Run analysis on DEMO Metro Line 6 project | POST /api/tools/risk-analyzer/run | 5+ risks found from injected test docs |

**Expected risk analysis timing:**
- risk_modelling: 3-8 min (qwen3.5:9b, 16000 tokens, thinking enabled)
- inconsistency_detection: 1-2 min per document pair
- Total for 7-doc project: ~15-25 min

---

## T9 — Email Bot

| # | Test | Method | Expected |
|---|---|---|---|
| T9-1 | GET /api/settings/email returns config | GET /api/settings/email | 200, imap settings |
| T9-2 | PUT /api/settings/email updates IMAP config | PUT /api/settings/email | 200 |
| T9-3 | Email records exist in DB | DB / dashboard metrics | unread_emails count visible in dashboard |
| T9-4 | Email linked to project | DB check | email.project_id set |

> **Note:** Full email polling requires a live IMAP server and Celery Beat schedule. Manual testing requires configuring IMAP credentials in settings.

---

## T10 — Admin Settings

| # | Test | Method | Expected |
|---|---|---|---|
| T10-1 | List users (admin only) | GET /api/settings/users | 200, user list with roles |
| T10-2 | Update user role | PATCH /api/settings/users/{id} | 200 |
| T10-3 | Access /api/settings/users as pm | GET /api/settings/users | 403 |
| T10-4 | Frontend settings — admin sees 4 tabs | Browser (admin) | Profile, LLM, Email, Users tabs visible |
| T10-5 | Frontend settings — pm sees 1 tab | Browser (pm) | Only Profile tab visible |

---

## T11 — WebSocket Real-time Events

| # | Test | Method | Expected |
|---|---|---|---|
| T11-1 | WS connects with valid JWT | ws://localhost:8000/ws?token=... | 101 Upgrade, connection open |
| T11-2 | WS rejects invalid token | ws://localhost:8000/ws?token=bad | Connection closed |
| T11-3 | file.status_changed event pushed after Celery processing | Upload file, monitor WS | Event received with document_id and status |
| T11-4 | project.suggestion event pushed after doc intelligence | Upload doc without project | Banner appears in UploadPage |
| T11-5 | task.updated event refreshes task list | Mark task complete | TasksPage list refreshes without manual reload |

---

## T12 — Bilingual Support (EN/FR)

| # | Test | Method | Expected |
|---|---|---|---|
| T12-1 | Switch language to FR | Frontend language toggle | All UI labels switch to French |
| T12-2 | Dashboard briefing in FR | Browser (FR mode) | content_fr shown instead of content_en |
| T12-3 | Dates formatted in FR locale | Browser (FR mode) | "25 mars 2026" instead of "March 25, 2026" |
| T12-4 | FR labels in task page | Browser (FR mode) | "Tâches" instead of "Tasks" |

---

## T13 — Backend Unit Tests

Run: `pytest tests/unit/ -v`

| # | Test File | What It Covers |
|---|---|---|
| U1 | `tests/unit/test_auth.py` | JWT encode/decode, password hash/verify |
| U2 | `tests/unit/test_chunker.py` | Chunker splits text correctly, respects overlap |
| U3 | `tests/unit/test_language_detect.py` | Detects EN vs FR text |
| U4 | `tests/unit/test_parsers.py` | PDF/DOCX/XLSX/TXT parsers return non-empty text |
| U5 | `tests/unit/test_sorter.py` | HardcodedSorter orders tasks by priority + due_date |
| U6 | `tests/unit/test_structurer.py` | RegexStructurer extracts dates and action items |

Run command:
```bash
cd backend
pytest tests/unit/ -v
```

---

## T14 — Data Injection Scripts

| # | Test | Command | Expected |
|---|---|---|---|
| D1 | Dry run inject | `python inject_test_docs.py --dry-run` | Prints 6 files, no DB changes |
| D2 | Inject test docs | `python inject_test_docs.py` | 6 documents inserted with full_text |
| D3 | Reset + re-inject | `python inject_test_docs.py --reset` | Previous docs deleted, 6 re-inserted |
| D4 | seed_demo.py idempotent | `python seed_demo.py` (run twice) | Second run prints [skip] for everything |
| D5 | seed_demo.py --reset | `python inject_test_docs.py --reset && python seed_demo.py --reset` | Order matters: inject reset first |

---

## Known Gaps (Not Tested — Not Implemented)

| Gap | Reason | Priority |
|---|---|---|
| Celery Beat scheduled briefings | Beat schedule not wired | Low — manual generation works |
| Celery Beat email polling | Beat schedule not wired | Medium — IMAP config exists |
| LLM-based task sorter | Phase 2 skeleton only | Low |
| LLM-generated daily briefing | Phase 2 not started | Medium |
| Web search enrichment in risk analyzer | Phase 2 not started | Low |
| Scope Drift Detector tool | Phase 2 not started | Low |
| OAuth / SSO providers | Phase 2+ not started | Low |
| PDF OCR (non-text PDFs) | Not started | Medium — scanned docs fail parsing |

---

## Test Execution Order (Recommended)

```
1. T14 (data injection) — set up test data first
2. T1  (auth)           — verify login works
3. T2  (dashboard)      — verify data visible
4. T3  (tasks)          — CRUD
5. T4  (projects)       — CRUD
6. T7  (LLM settings)   — verify Ollama reachable
7. T6  (doc intelligence) — verify LLM task extraction
8. T5a (upload)         — file upload (no Celery)
9. T12 (i18n)           — language toggle
10. T10 (admin settings)
11. T11 (WebSocket)     — real-time events
12. T5b (pipeline)      — requires Celery worker
13. T8  (risk analyzer) — long-running, run last
14. T13 (unit tests)    — run anytime
```
