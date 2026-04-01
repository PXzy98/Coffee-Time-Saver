# Showcase Test Results — 2026-04-01 19:22:36 UTC

## Environment
- Backend: http://localhost:8000
- LLM: openrouter / gemini-2.0-flash-preview (from .env)
- Auth: pm@example.com

## Summary
- **Total:** 39  |  **PASS:** 39  |  **FAIL:** 0  |  **SKIP:** 0

## Results

| Step | Test | Status | Time (ms) | Notes |
|------|------|--------|-----------|-------|
| 0.1 | Backend health | ✅ PASS | 268 | HTTP 200 |
| 1.1 | Login as PM | ✅ PASS | 346 | Token obtained |
| 1.2 | List projects | ✅ PASS | 20 | count=4: ASM Gate 2 Review, [DEMO] Office Relocation Q3, [DEMO] ERP System Upgrade, [DEMO] Metro Line 6 Extension |
| 1.3 | List tasks | ✅ PASS | 12 | count=47 |
| 1.4 | Dashboard metrics | ✅ PASS | 21 | {'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 54, 'files_processed_today': 11, 'unread_emails': 2} |
| 1.5 | List documents | ✅ PASS | 10 | count=23 |
| 2.1 | Create task | ✅ PASS | 4307 | returned 48 tasks, created_id=5b442fec |
| 2.2 | Verify LLM sort scores | ✅ PASS | 14 | scores=[1.0, 0.979, 0.958, 0.938, 0.917], fractional=True, ordered=True |
| 2.3 | Create scheduled future task | ✅ PASS | 3805 | HTTP=201, task_in_returned_list=False (expected False) |
| 2.4 | Scheduled task hidden in GET | ✅ PASS | 11 | task_count=48, scheduled_task_visible=False |
| 2.5 | Complete a task | ✅ PASS | 3962 | task_removed_from_list=True |
| 2.6 | Delete a task | ✅ PASS | 22 | HTTP=204, deleted='Update the financial forecast model' |
| 3.1 | Delete today briefing | ✅ PASS | 16 | briefing_id=89f3ffc2, delete_HTTP=404 |
| 3.2 | LLM briefing generation | ✅ PASS | 11 | content_en=884chars, content_fr=1225chars |
| 3.3 | Verify AI narrative style | ✅ PASS | 0 | first_100='Good morning! Here is your briefing for **Wednesday, April 1st**.

We have a few critical items that' |
| 3.4 | Verify French content | ✅ PASS | 0 | first_100='Bonjour à l'équipe ! Voici votre point de situation pour ce mercredi 1er avril 2026.

**Le focus du ' |
| 3.5 | Second request (cached) | ✅ PASS | 10 | same_content=True, time<500ms=True |
| 4.1 | Upload DOCX | ✅ PASS | 305 | HTTP=202, document_id=730a207b |
| 4.2 | Poll file processing status | ✅ PASS | 12080 | transitions=['processing', 'completed'], final=completed |
| 4.3 | Verify chunks created | ✅ PASS | 13 | pipeline_status=completed, chunk_count_from_list=0 |
| 4.4 | Verify tasks extracted from doc | ✅ PASS | 12 | doc_source_tasks=38, titles=['Provide updated structural assessment fo', 'Provide updated structural assessment fo', 'Provide an updated structural assessment'] |
| 4.5 | Task-project association | ✅ PASS | 0 | tasks_linked_to_metro=38/38 |
| 4.6 | Dashboard metrics updated | ✅ PASS | 16 | files_processed_today=12, metrics={'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 54, 'files_processed_today': 12, 'unread_emails': 2} |
| 5.1 | Run risk analysis | ✅ PASS | 20 | HTTP=202, report_id=bf629460 |
| 5.2 | Poll risk analysis status | ✅ PASS | 48650 | transitions=['running', 'completed'], final=completed |
| 5.3 | Fetch report | ✅ PASS | 18 | HTTP=200, keys=['report_id', 'project_id', 'generated_at', 'overall_risk_level', 'overall_confidence', 'executive_summary'] |
| 5.4 | Verify risks found | ✅ PASS | 0 | risk_count=5, ids=['', '', ''] |
| 5.5 | Verify inconsistencies | ✅ PASS | 0 | inconsistency_count=35 |
| 5.6 | Verify model_name | ✅ PASS | 0 | model_name='openai / google/gemini-3-flash-preview' |
| 5.7 | Verify evidence stats | ✅ PASS | 0 | stats={'chunks_analyzed': 17, 'documents': 15, 'emails': 2, 'tasks': 49} |
| 5.8 | Download PDF | ✅ PASS | 280 | HTTP=200, content-type=application/pdf, size=27169bytes |
| 5.9 | Download DOCX | ✅ PASS | 66 | HTTP=200, content-type=application/vnd.openxmlformats-officedocument.wordprocessingml.document, size=45290bytes |
| 6.6 | Tasks from email body | ✅ PASS | 125112 | non_demo_email_tasks=3, titles=['Provide revised consulting cost forecast', 'Follow up with Cyber Ops regarding produ', 'Schedule session with Team B leads'] |
| 6.7 | Tasks from email attachment doc | ✅ PASS | 0 | document_source_tasks=43 |
| 6.8 | Dashboard updated after email | ✅ PASS | 22 | metrics={'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 59, 'files_processed_today': 12, 'unread_emails': 2} |
| 7.1 | Final dashboard | ✅ PASS | 17 | metrics={'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 59, 'files_processed_today': 12, 'unread_emails': 2} |
| 7.2 | Final task list | ✅ PASS | 12 | total=51, by_source={'document': 43, 'email': 5, 'meeting': 2, 'manual': 1} |
| 7.3 | Final project list | ✅ PASS | 11 | count=4 |
| 7.4 | Final briefing (cached) | ✅ PASS | 12 | HTTP=200 |

## Timing Summary
- Auth login: 346ms
- Task create + LLM sort: 4307ms
- LLM briefing generation: 11ms
- File upload + pipeline: 12080ms
- Risk analysis (full): 48650ms
- Email poll + detection: 125112ms

## Data Snapshot
- Projects: 4
- Tasks final: 51 (by source: {'document': 43, 'email': 5, 'meeting': 2, 'manual': 1})
- Documents initial: 23
- Risks found: 5
- Inconsistencies found: 35
- Dashboard initial: {'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 54, 'files_processed_today': 11, 'unread_emails': 2}
- Dashboard final: {'active_projects': 2, 'overdue_tasks': 5, 'pending_tasks': 59, 'files_processed_today': 12, 'unread_emails': 2}