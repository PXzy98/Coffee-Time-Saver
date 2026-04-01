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

async def seed_documents(db, metro: Project, office: Project, pm: User) -> None:
    docs_data = [
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
                "not managed carefully. Monitoring wells to be installed at 10m intervals."
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
                "Change scope: Increase emergency ventilation capacity from 60 m³/s to "
                "80 m³/s per section to meet updated NFPA 502 requirements. Fan units "
                "upgraded from Type AV-4 to AV-6. Budget impact: +$1.2M CAD. "
                "Schedule impact: +2 weeks. Approval required from project director "
                "and city fire safety coordinator before procurement can proceed. "
                "Lead time for AV-6 units: 14 weeks."
            ),
        },
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
                "IT sign-off required on server room spec by June 30."
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
        await seed_documents(db, metro, office, pm)

        print("\n[4/5] Emails...")
        await seed_emails(db, metro, erp)

        print("\n[5/5] Briefing — skipped (LLM generates live on first Dashboard load)")

        print("""
Done! Summary:
  Projects : 3  (Metro Line 6 Extension, Office Relocation Q3, ERP System Upgrade)
  Tasks    : 10 (7 visible open, 2 completed, 1 hidden until +30d)
  Documents: 3  stubs (completed, with full_text for risk analysis)
  Emails   : 2  (1 processed, 1 unread)
  Briefing : will be LLM-generated on first Dashboard load

Login: pm@example.com / pm123456
""")


if __name__ == "__main__":
    asyncio.run(main())
