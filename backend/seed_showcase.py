"""
Showcase seed script — wipes ALL project data and inserts clean demo data.

Usage:
    cd backend
    python seed_showcase.py

What it does:
    1. Deletes ALL tasks, documents (+ chunks), emails, briefings,
       project_members, and projects.
    2. Inserts 3 projects, 10 tasks, 3 document stubs, 2 emails.
    3. Does NOT pre-seed a briefing — the LLM generates it live on
       the first Dashboard load (more impressive for the demo).

What it preserves:
    Users, roles, permissions, llm_configs, tool_modules, audit_logs.

Safe to re-run before every demo session.
"""
import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, text
from sqlalchemy import select

sys.path.insert(0, ".")

from core.database import AsyncSessionLocal
from core.models import (
    User, Project, ProjectMember, Task, DailyBriefing,
    Document, DocumentChunk, Email,
)

TODAY = date.today()


# ---------------------------------------------------------------------------
# 1. Full wipe (preserves users / roles / permissions / llm_configs)
# ---------------------------------------------------------------------------

async def wipe_all(db) -> None:
    print("  Wiping tasks, documents, emails, briefings, projects...")

    # Delete in dependency order (children before parents)
    await db.execute(text("DELETE FROM email_attachments"))
    await db.execute(delete(Task))
    await db.execute(delete(DocumentChunk))
    await db.execute(delete(Document))
    await db.execute(delete(Email))
    await db.execute(delete(DailyBriefing))
    await db.execute(delete(ProjectMember))
    await db.execute(delete(Project))

    await db.commit()
    print("  Wipe complete.")


# ---------------------------------------------------------------------------
# 2. Projects
# ---------------------------------------------------------------------------

async def seed_projects(db, admin: User, pm: User) -> tuple:
    projects_data = [
        {
            "name": "Metro Line 6 Extension",
            "description": (
                "Infrastructure expansion project covering 12 km of new underground track "
                "through the city centre. Phase 1 scope includes 4 new stations and "
                "ventilation systems. Budget: $2.4B CAD."
            ),
            "status": "active",
            "owner_id": admin.id,
            "is_shared": True,
            "metadata_": {"budget_cad": 2_400_000_000, "phase": 1, "region": "downtown"},
        },
        {
            "name": "Office Relocation Q3",
            "description": (
                "Consolidation of three downtown offices into a single hub at "
                "1200 McGill College. Target move date: September 15."
            ),
            "status": "active",
            "owner_id": pm.id,
            "is_shared": False,
            "metadata_": {"move_date": "2026-09-15", "headcount": 340},
        },
        {
            "name": "ERP System Upgrade",
            "description": (
                "Migration from legacy SAP ECC 6.0 to SAP S/4HANA. Includes data "
                "migration, user training, and parallel run period. Currently paused "
                "pending license resolution."
            ),
            "status": "paused",
            "owner_id": admin.id,
            "is_shared": True,
            "metadata_": {"vendor": "SAP", "go_live": "2027-01-01"},
        },
    ]

    created = []
    for data in projects_data:
        project = Project(id=uuid.uuid4(), **data)
        db.add(project)
        await db.flush()

        # PM is member on all shared projects and projects they own
        if data["is_shared"] or data["owner_id"] == pm.id:
            db.add(ProjectMember(project_id=project.id, user_id=pm.id, role="member"))

        # Admin is viewer on PM-owned projects
        if data["owner_id"] == pm.id:
            db.add(ProjectMember(project_id=project.id, user_id=admin.id, role="viewer"))

        await db.flush()
        created.append(project)
        print(f"  [ok] Project: {data['name']}")

    await db.commit()
    return tuple(created)


# ---------------------------------------------------------------------------
# 3. Tasks
# ---------------------------------------------------------------------------

async def seed_tasks(db, metro: Project, office: Project, erp: Project, pm: User) -> None:
    tasks_data = [
        # ── Metro Line 6 Extension ──────────────────────────────────────
        {
            "title": "Approve revised ventilation specs (ECO-2241)",
            "description": (
                "Engineering change order ECO-2241 pending sign-off. Fire safety "
                "consultant has reviewed. Increase in fan capacity required to meet "
                "updated NFPA 502 standards."
            ),
            "priority": 75,
            "due_date": TODAY + timedelta(days=1),
            "source": "meeting",
            "project_id": metro.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Send weekly progress report to city liaison",
            "description": (
                "Standard Monday report covering progress, risks, and upcoming "
                "milestones. The steering committee meets this afternoon."
            ),
            "priority": 50,
            "due_date": TODAY - timedelta(days=1),   # overdue
            "source": "manual",
            "project_id": metro.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Confirm concrete pour schedule with contractor",
            "description": (
                "Tunnelling crew on standby — needed date confirmation before "
                "crew mobilisation. Confirmed."
            ),
            "priority": 95,
            "due_date": TODAY,
            "source": "email",
            "project_id": metro.id,
            "is_completed": True,
            "scheduled_at": None,
        },
        # ── Office Relocation Q3 ────────────────────────────────────────
        {
            "title": "Finalize floor plan with interior design team",
            "description": (
                "Open-plan layout for floors 8–11. IT cabling requirements to be "
                "incorporated. Decision needed on server room placement on floor 10."
            ),
            "priority": 70,
            "due_date": TODAY + timedelta(days=2),
            "source": "meeting",
            "project_id": office.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Collect quotes from three moving companies",
            "description": (
                "Must include insurance coverage for server room equipment. "
                "Preferred vendors: Allied, AMJ Campbell, Hercules."
            ),
            "priority": 55,
            "due_date": TODAY + timedelta(days=5),
            "source": "manual",
            "project_id": office.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Notify all staff of move timeline",
            "description": "Draft HR communication approved and distributed to all 340 staff.",
            "priority": 40,
            "due_date": TODAY + timedelta(days=7),
            "source": "manual",
            "project_id": office.id,
            "is_completed": True,
            "scheduled_at": None,
        },
        # ── ERP System Upgrade ──────────────────────────────────────────
        {
            "title": "Follow up with SAP on delayed license renewal",
            "description": (
                "License expired — sandbox environment suspended. Renewal invoice "
                "received but payment approval pending from finance."
            ),
            "priority": 85,
            "due_date": TODAY - timedelta(days=2),   # overdue
            "source": "email",
            "project_id": erp.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Reschedule data migration dry-run",
            "description": (
                "Originally set for March 28 — postponed pending license resolution. "
                "New target date to be confirmed with SI partner."
            ),
            "priority": 65,
            "due_date": TODAY + timedelta(days=10),
            "source": "manual",
            "project_id": erp.id,
            "is_completed": False,
            "scheduled_at": None,
        },
        # ── Personal (no project) ───────────────────────────────────────
        {
            "title": "Prepare Q2 PM team capacity plan",
            "description": "Present at the next steering committee. Include contractor renewals and vacation coverage.",
            "priority": 72,
            "due_date": TODAY + timedelta(days=9),
            "source": "manual",
            "project_id": None,
            "is_completed": False,
            "scheduled_at": None,
        },
        {
            "title": "Prepare go-live checklist for ERP cutover",
            "description": (
                "Comprehensive go-live checklist covering data migration sign-off, "
                "user acceptance testing, hypercare plan, and rollback procedure."
            ),
            "priority": 85,
            "due_date": TODAY + timedelta(days=45),
            "source": "manual",
            "project_id": None,
            "is_completed": False,
            "scheduled_at": TODAY + timedelta(days=30),  # hidden until then
        },
    ]

    for data in tasks_data:
        completed_at = datetime.now(timezone.utc) if data["is_completed"] else None
        task = Task(
            id=uuid.uuid4(),
            user_id=pm.id,
            completed_at=completed_at,
            sort_score=float(data["priority"]),
            **{k: v for k, v in data.items()},
        )
        db.add(task)
        flag = " [overdue]" if data.get("due_date") and data["due_date"] < TODAY and not data["is_completed"] else ""
        flag += " [completed]" if data["is_completed"] else ""
        flag += " [hidden until +30d]" if data.get("scheduled_at") else ""
        print(f"  [ok] Task: {data['title'][:55]}{flag}")

    await db.commit()


# ---------------------------------------------------------------------------
# 4. Document stubs (pre-processed — no file on disk)
# ---------------------------------------------------------------------------

async def seed_documents(db, metro: Project, office: Project, erp: Project, pm: User) -> None:
    docs_data = [
        # ── Metro Line 6 Extension (3 docs) ────────────────────────────
        {
            "filename": "geotechnical_survey_station3.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 4_821_504,
            "status": "completed",
            "doc_type": "report",
            "project_id": metro.id,
            "full_text": (
                "Geotechnical Survey Report — Station 3 North Portal. "
                "Executive Summary: Subsurface investigation identified soft clay deposits "
                "at depths 8-14m. Recommend pile foundation with 600mm diameter cast-in-place "
                "concrete piles to bearing stratum at 18m depth. Groundwater table observed "
                "at 6.2m below grade. Dewatering plan required during excavation phase. "
                "Risk: potential settlement of adjacent building foundations if dewatering "
                "not managed carefully. Monitoring wells to be installed at 10m intervals. "
                "Construction timeline assumes no dewatering complications. Total piling "
                "works estimated at 8 weeks. Contractor mobilisation planned for April 2026."
            ),
        },
        {
            "filename": "ventilation_ECO2241_rev3.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size_bytes": 892_928,
            "status": "completed",
            "doc_type": "specification",
            "project_id": metro.id,
            "full_text": (
                "Engineering Change Order ECO-2241 Rev 3 — Tunnel Ventilation System. "
                "Change scope: Increase emergency ventilation capacity from 60 m3/s to "
                "80 m3/s per section to meet updated NFPA 502 requirements. Fan units "
                "upgraded from Type AV-4 to AV-6. Budget impact: +$1.2M CAD. "
                "Schedule impact: +2 weeks. Approval required from project director "
                "and city fire safety coordinator before procurement can proceed. "
                "Lead time for AV-6 units: 14 weeks. NOTE: The original project schedule "
                "baseline does not account for this 2-week extension. The updated "
                "completion date for Station 3 ventilation is now June 30, 2026, not "
                "June 14 as stated in the master project schedule document."
            ),
        },
        {
            "filename": "metro_phase1_project_schedule_v2.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1_245_184,
            "status": "completed",
            "doc_type": "report",
            "project_id": metro.id,
            "full_text": (
                "Metro Line 6 Extension — Phase 1 Master Project Schedule v2. "
                "Approved baseline: January 15, 2026. Project Director: City Infrastructure Office. "
                "Key milestones: Tunnelling works complete — May 30, 2026. "
                "Station 3 structural works complete — June 14, 2026. "
                "Station 3 ventilation and MEP complete — June 14, 2026. "
                "Systems integration testing — July 1 to August 15, 2026. "
                "Trial operations — September 1 to October 15, 2026. "
                "Revenue service launch — November 1, 2026. "
                "Budget status: Phase 1 approved at $2.4B CAD. Current forecast within approved "
                "envelope pending ECO-2241 impact assessment. Contractor mobilisation on schedule. "
                "Critical path: tunnelling completion drives all downstream station fit-out milestones."
            ),
        },
        # ── Office Relocation Q3 (3 docs) ───────────────────────────────
        {
            "filename": "office_floorplan_v4.xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "file_size_bytes": 215_040,
            "status": "completed",
            "doc_type": "general",
            "project_id": office.id,
            "full_text": (
                "Floor Plan Space Allocation v4 — 1200 McGill College. "
                "Floor 8: 120 workstations (open plan), 4 meeting rooms, 1 focus room. "
                "Floor 9: Executive suite, boardroom (20 seats), HR department, reception. "
                "Floor 10: IT infrastructure, server room (tier-2), NOC, helpdesk. "
                "Floor 11: Cafeteria (180 seats), training centre, wellness room. "
                "Total capacity: 340 staff. Move date: September 15, 2026. "
                "IT sign-off required on server room spec by June 30. "
                "Note: Floor 10 server room is designed for 12 racks at standard density. "
                "Current inventory at existing offices totals 18 racks. Consolidation "
                "plan required before move date."
            ),
        },
        {
            "filename": "relocation_it_requirements.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size_bytes": 348_160,
            "status": "completed",
            "doc_type": "specification",
            "project_id": office.id,
            "full_text": (
                "IT Infrastructure Requirements — Office Relocation Q3. "
                "Prepared by: IT Infrastructure Lead. Date: February 20, 2026. "
                "Network: 10Gbps backbone between floors, 1Gbps to desktop, WiFi 6 coverage "
                "across all floors. Cabling to be completed 4 weeks before move date. "
                "Server room: Minimum 20 rack units required to accommodate current inventory "
                "plus 30% growth headroom. Power: 2N redundant UPS with 30-minute runtime. "
                "Cooling: Precision air conditioning unit, N+1 redundancy. "
                "Move sequence: IT systems must be migrated floor by floor over 3 weekends "
                "to avoid business disruption. All systems must be validated before staff arrive. "
                "Critical dependency: Network cabling sign-off by August 15 to allow "
                "system migration to begin August 22."
            ),
        },
        {
            "filename": "relocation_steering_committee_brief_march.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 512_000,
            "status": "completed",
            "doc_type": "report",
            "project_id": office.id,
            "full_text": (
                "Office Relocation Q3 — Steering Committee Brief. March 2026. "
                "Project status: On track. Move date confirmed September 15, 2026. "
                "Budget: $3.2M approved. Current forecast $3.1M. "
                "Open issues: (1) Server room capacity — floor plan v4 allocates 12 racks; "
                "IT requirements document specifies 20 racks minimum. Gap not yet resolved. "
                "Decision required from CIO before construction drawings are finalized. "
                "(2) Moving company selection in progress — quotes received from Allied and "
                "AMJ Campbell. Hercules quote outstanding. Award target: April 30. "
                "(3) Staff communications plan approved and distributed. 340 staff notified. "
                "Next steering committee: April 15, 2026. "
                "Decision required: Server room rack capacity — approve floor plan revision "
                "or reduce IT inventory before move."
            ),
        },
        # ── ERP System Upgrade (3 docs) ────────────────────────────────
        {
            "filename": "erp_migration_plan_v1.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2_097_152,
            "status": "completed",
            "doc_type": "report",
            "project_id": erp.id,
            "full_text": (
                "SAP S/4HANA Migration Plan v1 — ERP System Upgrade. "
                "Prepared by: SI Partner (Accenture). Approved: December 10, 2025. "
                "Scope: Migration from SAP ECC 6.0 to SAP S/4HANA Cloud, Private Edition. "
                "Data migration approach: Full historical data migration (7 years). "
                "Parallel run period: 8 weeks. Go-live target: January 1, 2027. "
                "Key phases: (1) System landscape design — Jan to Feb 2026. "
                "(2) Data migration preparation — Mar to Jun 2026. "
                "(3) Development and configuration — Apr to Sep 2026. "
                "(4) User acceptance testing — Oct to Nov 2026. "
                "(5) Cutover and go-live — December 2026. "
                "License assumption: Active SAP ECC development license maintained throughout "
                "migration period. License renewal due March 15, 2026 — finance to process. "
                "Risk: License lapse will suspend sandbox and development environments, "
                "blocking phases 2 and 3."
            ),
        },
        {
            "filename": "erp_project_charter_v2.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size_bytes": 718_848,
            "status": "completed",
            "doc_type": "specification",
            "project_id": erp.id,
            "full_text": (
                "ERP System Upgrade — Project Charter v2. "
                "Project Sponsor: CFO. Project Manager: PM Account. "
                "Approved budget: $4.8M CAD over 24 months. "
                "Objectives: Replace legacy SAP ECC 6.0 with S/4HANA to support "
                "real-time financial reporting, streamline procure-to-pay, and retire "
                "three legacy integration middleware components. "
                "Key constraints: No disruption to fiscal year-end processing (March 31 annually). "
                "All cutover activities must occur outside Q4 (Oct-Dec). "
                "Go-live window: January 2027 only. "
                "Current status: Project paused as of March 20, 2026 pending SAP license "
                "renewal resolution. Development environment suspended. SI partner on "
                "standby — daily cost of delay: approximately $4,200 in standby fees. "
                "Escalation: CFO office notified March 22. Finance processing renewal invoice."
            ),
        },
        {
            "filename": "erp_user_training_plan.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size_bytes": 425_984,
            "status": "completed",
            "doc_type": "general",
            "project_id": erp.id,
            "full_text": (
                "ERP System Upgrade — User Training and Change Management Plan. "
                "Prepared by: Change Management Lead. Date: January 30, 2026. "
                "Training scope: 520 users across Finance, Procurement, HR, and Operations. "
                "Approach: Role-based training modules delivered via classroom and e-learning. "
                "Training schedule: September to November 2026 (10 weeks before go-live). "
                "Train-the-trainer program: 25 super-users identified and trained by August 2026. "
                "Change readiness assessment: Planned for Q2 2026. "
                "Note: Training timeline assumes go-live January 1, 2027 as per project charter. "
                "If go-live is delayed beyond January 2027, training schedule must be revised. "
                "Current risk: Project pause due to license issue may compress training window "
                "if development phase slips. Minimum training window required: 8 weeks. "
                "If development completes after October 15, go-live must move to April 2027."
            ),
        },
    ]

    for data in docs_data:
        doc = Document(id=uuid.uuid4(), uploaded_by=pm.id, **data)
        db.add(doc)
        print(f"  [ok] Document: {data['filename']}")

    await db.commit()


# ---------------------------------------------------------------------------
# 5. Emails
# ---------------------------------------------------------------------------

async def seed_emails(db, metro: Project, erp: Project) -> None:
    now = datetime.now(timezone.utc)

    emails_data = [
        {
            "message_id": "<showcase-001@mail.example.com>",
            "subject": "RE: Concrete pour schedule — urgent confirmation needed",
            "from_address": "j.tremblay@tunnelcorp.ca",
            "to_addresses": ["pm@example.com"],
            "cc_addresses": [],
            "body_text": (
                "Hi,\n\nWe need your go-ahead by 3pm today to mobilise the crew for "
                "Saturday. If we don't get confirmation the slot goes to another client.\n\n"
                "Please advise ASAP.\n\nJean Tremblay\nSite Superintendent, TunnelCorp"
            ),
            "received_at": now - timedelta(hours=3),
            "processed": True,
            "project_id": metro.id,
        },
        {
            "message_id": "<showcase-002@mail.example.com>",
            "subject": "SAP license renewal — action required",
            "from_address": "licensing@sap.com",
            "to_addresses": ["pm@example.com", "it@example.com"],
            "cc_addresses": [],
            "body_text": (
                "Dear Customer,\n\nYour SAP ECC development license (Contract 4500123) "
                "expired on March 15, 2026. The sandbox environment has been suspended. "
                "To restore access please process the renewal invoice attached.\n\n"
                "SAP License Management"
            ),
            "received_at": now - timedelta(days=10),
            "processed": False,
            "project_id": erp.id,
        },
    ]

    for data in emails_data:
        email = Email(id=uuid.uuid4(), **data)
        db.add(email)
        print(f"  [ok] Email: {data['subject'][:60]}")

    await db.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    async with AsyncSessionLocal() as db:
        print("\n=== Coffee Time Saver — Showcase Seed ===\n")

        # Verify users exist
        r = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = r.scalar_one_or_none()
        r = await db.execute(select(User).where(User.email == "pm@example.com"))
        pm = r.scalar_one_or_none()

        if not admin or not pm:
            print("ERROR: Users not found. Run first:")
            print("  python seed.py --demo")
            return

        print("[0/5] Wiping existing data...")
        await wipe_all(db)

        print("\n[1/5] Projects...")
        metro, office, erp = await seed_projects(db, admin, pm)

        print("\n[2/5] Tasks...")
        await seed_tasks(db, metro, office, erp, pm)

        print("\n[3/5] Documents (stubs)...")
        await seed_documents(db, metro, office, erp, pm)

        print("\n[4/5] Emails...")
        await seed_emails(db, metro, erp)

        print("\n[5/5] Briefing — skipped (LLM generates live on first Dashboard load)")

        print("""
Done! Summary:
  Projects : 3  (Metro Line 6 Extension, Office Relocation Q3, ERP System Upgrade)
  Tasks    : 10 (7 visible open, 2 completed, 1 hidden until +30d)
  Documents: 9  stubs (3 per project, completed, with full_text for risk analysis)
  Emails   : 2  (1 processed, 1 unread)
  Briefing : will be LLM-generated on first Dashboard load

Login: pm@example.com / pm123456
""")


if __name__ == "__main__":
    asyncio.run(main())
