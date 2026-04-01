"""
Demo seed script — injects realistic test data for UI development and manual testing.

Usage:
    python seed_demo.py           # insert demo data (skips if already exists)
    python seed_demo.py --reset   # wipe demo data first, then re-insert

Requires:
    - alembic upgrade head (tables must exist)
    - python seed.py --demo (users must exist)
"""
import argparse
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from core.database import AsyncSessionLocal
from core.models import (
    User, Project, ProjectMember, Task, DailyBriefing, Document, Email
)

# Tag used to identify demo-inserted rows so --reset can clean them up
DEMO_TAG = "[DEMO]"

TODAY = date.today()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag(name: str) -> str:
    return f"{DEMO_TAG} {name}"


async def _get_user(db, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

async def reset_demo_data(db) -> None:
    print("  Resetting demo data...")

    # Tasks tagged with DEMO_TAG
    await db.execute(delete(Task).where(Task.title.like(f"{DEMO_TAG}%")))

    # Briefings for demo users on any date (safe — only demo PMs use this script)
    pm = await _get_user(db, "pm@example.com")
    if pm:
        await db.execute(delete(DailyBriefing).where(DailyBriefing.user_id == pm.id))

    # Documents tagged with DEMO_TAG
    await db.execute(delete(Document).where(Document.filename.like(f"{DEMO_TAG}%")))

    # Emails tagged with DEMO_TAG
    await db.execute(delete(Email).where(Email.subject.like(f"{DEMO_TAG}%")))

    # Projects tagged with DEMO_TAG (cascade deletes members)
    await db.execute(delete(Project).where(Project.name.like(f"{DEMO_TAG}%")))

    await db.commit()
    print("  Reset complete.")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def seed_projects(db, admin: User, pm: User) -> list[Project]:
    projects_data = [
        {
            "name": _tag("Metro Line 6 Extension"),
            "description": "Infrastructure expansion project covering 12 km of new underground track through the city centre. Phase 1 scope includes 4 new stations and ventilation systems.",
            "status": "active",
            "owner_id": admin.id,
            "is_shared": True,
            "metadata_": {"budget_cad": 2_400_000_000, "phase": 1, "region": "downtown"},
        },
        {
            "name": _tag("Office Relocation Q3"),
            "description": "Consolidation of three downtown offices into a single hub at 1200 McGill College. Target move date: September 15.",
            "status": "active",
            "owner_id": pm.id,
            "is_shared": False,
            "metadata_": {"move_date": "2026-09-15", "headcount": 340},
        },
        {
            "name": _tag("ERP System Upgrade"),
            "description": "Migration from legacy SAP ECC 6.0 to SAP S/4HANA. Includes data migration, user training, and parallel run period.",
            "status": "paused",
            "owner_id": admin.id,
            "is_shared": True,
            "metadata_": {"vendor": "SAP", "go_live": "2027-01-01"},
        },
    ]

    created = []
    for data in projects_data:
        # Skip if already exists
        result = await db.execute(select(Project).where(Project.name == data["name"]))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  [skip] Project already exists: {data['name']}")
            created.append(existing)
            continue

        project = Project(id=uuid.uuid4(), **data)
        db.add(project)
        await db.flush()

        # Add pm as member on shared projects
        if data["is_shared"] or data["owner_id"] == pm.id:
            db.add(ProjectMember(project_id=project.id, user_id=pm.id, role="member"))

        # Add admin as member on pm-owned project
        if data["owner_id"] == pm.id:
            db.add(ProjectMember(project_id=project.id, user_id=admin.id, role="viewer"))

        await db.flush()
        created.append(project)
        print(f"  [ok] Project: {data['name']}")

    await db.commit()
    return created


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

async def seed_tasks(db, projects: list[Project], pm: User) -> None:
    metro, office, erp = projects[0], projects[1], projects[2]

    tasks_data = [
        # Metro project tasks
        {
            "title": _tag("Review geotechnical survey report for Station 3"),
            "description": "Survey delivered by Stantec on March 20. Need to flag any foundation risks before contractor mobilisation.",
            "priority": 90,
            "due_date": TODAY,
            "source": "email",
            "project_id": metro.id,
            "is_completed": False,
        },
        {
            "title": _tag("Approve revised ventilation specs"),
            "description": "Engineering change order ECO-2241 pending sign-off. Fire safety consultant has reviewed.",
            "priority": 75,
            "due_date": TODAY + timedelta(days=1),
            "source": "meeting",
            "project_id": metro.id,
            "is_completed": False,
        },
        {
            "title": _tag("Update project schedule in Primavera"),
            "description": "Baseline shift of 3 weeks due to permitting delay on Station 1 excavation.",
            "priority": 60,
            "due_date": TODAY + timedelta(days=3),
            "source": "manual",
            "project_id": metro.id,
            "is_completed": False,
        },
        {
            "title": _tag("Send weekly progress report to city liaison"),
            "description": "Standard Monday report covering progress, risks, and upcoming milestones.",
            "priority": 50,
            "due_date": TODAY - timedelta(days=1),  # overdue
            "source": "manual",
            "project_id": metro.id,
            "is_completed": False,
        },
        {
            "title": _tag("Confirm concrete pour schedule with contractor"),
            "description": "Tunnelling crew on standby — need date confirmation by EOD.",
            "priority": 95,
            "due_date": TODAY,
            "source": "email",
            "project_id": metro.id,
            "is_completed": True,
        },
        # Office relocation tasks
        {
            "title": _tag("Finalize floor plan with interior design team"),
            "description": "Open-plan layout for floors 8-11. IT cabling requirements to be incorporated.",
            "priority": 70,
            "due_date": TODAY + timedelta(days=2),
            "source": "meeting",
            "project_id": office.id,
            "is_completed": False,
        },
        {
            "title": _tag("Get quotes from 3 moving companies"),
            "description": "Must include insurance coverage for server room equipment.",
            "priority": 55,
            "due_date": TODAY + timedelta(days=5),
            "source": "manual",
            "project_id": office.id,
            "is_completed": False,
        },
        {
            "title": _tag("Notify all staff of move timeline"),
            "description": "Draft HR communication for distribution by April 1.",
            "priority": 40,
            "due_date": TODAY + timedelta(days=7),
            "source": "manual",
            "project_id": office.id,
            "is_completed": True,
        },
        # ERP tasks
        {
            "title": _tag("Follow up with SAP on delayed license renewal"),
            "description": "License expired March 15 — sandbox environment blocked.",
            "priority": 85,
            "due_date": TODAY - timedelta(days=2),  # overdue
            "source": "email",
            "project_id": erp.id,
            "is_completed": False,
        },
        {
            "title": _tag("Reschedule data migration dry-run"),
            "description": "Originally set for March 28 — now postponed pending license resolution.",
            "priority": 65,
            "due_date": TODAY + timedelta(days=10),
            "source": "manual",
            "project_id": erp.id,
            "is_completed": False,
        },
        # Tasks without a project (personal tasks)
        {
            "title": _tag("Prepare Q2 PM team capacity plan"),
            "description": "Present at the April 3 steering committee.",
            "priority": 72,
            "due_date": TODAY + timedelta(days=9),
            "source": "manual",
            "project_id": None,
            "is_completed": False,
        },
        {
            "title": _tag("Book hotel for PMI conference in Toronto"),
            "description": "Conference dates: May 12-14. Early bird deadline April 15.",
            "priority": 25,
            "due_date": TODAY + timedelta(days=21),
            "source": "manual",
            "project_id": None,
            "is_completed": False,
        },
    ]

    for data in tasks_data:
        result = await db.execute(select(Task).where(Task.title == data["title"], Task.user_id == pm.id))
        if result.scalar_one_or_none():
            print(f"  [skip] Task already exists: {data['title'][:50]}...")
            continue

        completed_at = datetime.now(timezone.utc) if data["is_completed"] else None
        task = Task(
            id=uuid.uuid4(),
            user_id=pm.id,
            title=data["title"],
            description=data["description"],
            priority=data["priority"],
            due_date=data["due_date"],
            source=data["source"],
            project_id=data["project_id"],
            is_completed=data["is_completed"],
            completed_at=completed_at,
            sort_score=float(data["priority"]),
        )
        db.add(task)
        print(f"  [ok] Task: {data['title'][:55]}...")

    await db.commit()


# ---------------------------------------------------------------------------
# Daily Briefing
# ---------------------------------------------------------------------------

async def seed_briefing(db, pm: User) -> None:
    result = await db.execute(
        select(DailyBriefing).where(DailyBriefing.user_id == pm.id, DailyBriefing.date == TODAY)
    )
    if result.scalar_one_or_none():
        print("  [skip] Briefing already exists for today.")
        return

    briefing = DailyBriefing(
        id=uuid.uuid4(),
        user_id=pm.id,
        date=TODAY,
        content_en=f"""**Daily Briefing — {TODAY.strftime('%A, %B %d %Y')}**

Good morning. Here is your summary for today.

**Urgent (due today or overdue)**
- Confirm concrete pour schedule with Metro Line 6 contractor — awaiting your confirmation before crew mobilises.
- Send weekly progress report to city liaison — this was due yesterday. Draft is in your email drafts folder.
- Follow up with SAP on the expired license — sandbox has been blocked for 10 days, delaying the dry-run.

**Upcoming this week**
- Approve revised ventilation specs (ECO-2241) by tomorrow.
- Finalize office floor plan with interior design team by Thursday.
- Review geotechnical survey for Metro Station 3 — flag foundation risks before contractor mobilisation.

**Completed yesterday**
- Concrete pour schedule confirmed with tunnelling crew. ✓
- HR communication drafted and approved. ✓

**Projects at a glance**
| Project | Status | Open Tasks |
|---------|--------|-----------|
| Metro Line 6 Extension | Active | 4 open, 1 overdue |
| Office Relocation Q3 | Active | 2 open |
| ERP System Upgrade | Paused | 2 open, 1 overdue |

Have a productive day.""",
        content_fr=f"""**Rapport quotidien — {TODAY.strftime('%A %d %B %Y')}**

Bonjour. Voici votre résumé pour aujourd'hui.

**Urgent (dû aujourd'hui ou en retard)**
- Confirmer le calendrier de coulage de béton avec l'entrepreneur du métro — en attente de votre confirmation avant la mobilisation de l'équipe.
- Envoyer le rapport d'avancement hebdomadaire au représentant de la ville — ce rapport était dû hier. Le brouillon est dans votre dossier.
- Relancer SAP concernant la licence expirée — l'environnement sandbox est bloqué depuis 10 jours.

**À venir cette semaine**
- Approuver les spécifications de ventilation révisées (ECO-2241) d'ici demain.
- Finaliser le plan d'étage du bureau avec l'équipe de design intérieur d'ici jeudi.
- Examiner le rapport géotechnique pour la Station 3 du métro.

**Complétés hier**
- Calendrier de coulage confirmé avec l'équipe de tunnelisation. ✓
- Communication RH rédigée et approuvée. ✓

**Aperçu des projets**
| Projet | Statut | Tâches ouvertes |
|--------|--------|----------------|
| Prolongement ligne 6 | Actif | 4 ouvertes, 1 en retard |
| Déménagement Q3 | Actif | 2 ouvertes |
| Mise à niveau ERP | En pause | 2 ouvertes, 1 en retard |

Bonne journée.""",
    )
    db.add(briefing)
    await db.commit()
    print("  [ok] Daily briefing created for today.")


# ---------------------------------------------------------------------------
# Documents (pre-processed stubs — no file on disk)
# ---------------------------------------------------------------------------

async def seed_documents(db, projects: list[Project], pm: User) -> None:
    metro, office, erp = projects[0], projects[1], projects[2]

    docs_data = [
        {
            "filename": _tag("geotechnical_survey_station3.pdf"),
            "mime_type": "application/pdf",
            "file_size_bytes": 4_821_504,
            "status": "completed",
            "doc_type": "report",
            "project_id": metro.id,
            "full_text": "Geotechnical Survey Report — Station 3 North Portal. Executive Summary: Subsurface investigation identified soft clay deposits at depths 8-14m. Recommend pile foundation with 600mm diameter cast-in-place concrete piles to bearing stratum at 18m depth. Groundwater table observed at 6.2m below grade. Dewatering plan required during excavation.",
        },
        {
            "filename": _tag("ventilation_ECO2241_rev3.docx"),
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size_bytes": 892_928,
            "status": "completed",
            "doc_type": "specification",
            "project_id": metro.id,
            "full_text": "Engineering Change Order ECO-2241 Rev 3 — Tunnel Ventilation System. Change scope: Increase emergency ventilation capacity from 60 m³/s to 80 m³/s per section to meet updated NFPA 502 requirements. Fan units upgraded from Type AV-4 to AV-6. Budget impact: +$1.2M. Schedule impact: +2 weeks.",
        },
        {
            "filename": _tag("office_floorplan_v4.xlsx"),
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "file_size_bytes": 215_040,
            "status": "completed",
            "doc_type": "general",
            "project_id": office.id,
            "full_text": "Floor Plan Space Allocation v4 — 1200 McGill College. Floor 8: 120 workstations (open plan), 4 meeting rooms. Floor 9: Executive suite, boardroom, HR. Floor 10: IT infrastructure, server room, NOC. Floor 11: Cafeteria, training centre, wellness room. Total capacity: 340 staff.",
        },
        {
            "filename": _tag("sap_migration_scope_v2.pdf"),
            "mime_type": "application/pdf",
            "file_size_bytes": 2_304_000,
            "status": "processing",
            "doc_type": "report",
            "project_id": erp.id,
            "full_text": None,  # still processing
        },
    ]

    for data in docs_data:
        result = await db.execute(select(Document).where(Document.filename == data["filename"]))
        if result.scalar_one_or_none():
            print(f"  [skip] Document already exists: {data['filename']}")
            continue

        doc = Document(id=uuid.uuid4(), uploaded_by=pm.id, **data)
        db.add(doc)
        print(f"  [ok] Document: {data['filename']}")

    await db.commit()


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------

async def seed_emails(db, projects: list[Project]) -> None:
    metro, office, erp = projects[0], projects[1], projects[2]

    now = datetime.now(timezone.utc)

    emails_data = [
        {
            "message_id": f"<demo-001@mail.example.com>",
            "subject": _tag("RE: Concrete pour schedule — urgent confirmation needed"),
            "from_address": "j.tremblay@tunnelcorp.ca",
            "to_addresses": ["pm@example.com"],
            "body_text": "Hi,\n\nWe need your go-ahead by 3pm today to mobilise the crew for Saturday. If we don't get confirmation the slot goes to another client.\n\nPlease advise ASAP.\n\nJean Tremblay\nSite Superintendent, TunnelCorp",
            "received_at": now - timedelta(hours=3),
            "processed": True,
            "project_id": metro.id,
        },
        {
            "message_id": "<demo-002@mail.example.com>",
            "subject": _tag("FW: City liaison — weekly progress report reminder"),
            "from_address": "m.chen@montreal.ca",
            "to_addresses": ["pm@example.com"],
            "body_text": "Hi,\n\nJust a reminder that the weekly status report was due by 9am Monday. Please send at your earliest convenience — the steering committee meets this afternoon.\n\nThanks,\nMai Chen\nCity Liaison Office",
            "received_at": now - timedelta(hours=6),
            "processed": False,
            "project_id": metro.id,
        },
        {
            "message_id": "<demo-003@mail.example.com>",
            "subject": _tag("SAP license renewal — action required"),
            "from_address": "licensing@sap.com",
            "to_addresses": ["pm@example.com", "it@example.com"],
            "body_text": "Dear Customer,\n\nYour SAP ECC development license (Contract 4500123) expired on March 15, 2026. The sandbox environment has been suspended. To restore access please process the renewal invoice attached.\n\nSAP License Management",
            "received_at": now - timedelta(days=10),
            "processed": False,
            "project_id": erp.id,
        },
    ]

    for data in emails_data:
        result = await db.execute(select(Email).where(Email.message_id == data["message_id"]))
        if result.scalar_one_or_none():
            print(f"  [skip] Email already exists: {data['subject'][:50]}")
            continue

        email = Email(id=uuid.uuid4(), cc_addresses=[], **data)
        db.add(email)
        print(f"  [ok] Email: {data['subject'][:55]}...")

    await db.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(reset: bool) -> None:
    async with AsyncSessionLocal() as db:
        print("\n=== Coffee Time Saver — Demo Data Seed ===\n")

        admin = await _get_user(db, "admin@example.com")
        pm = await _get_user(db, "pm@example.com")

        if not admin or not pm:
            print("ERROR: Required users not found.")
            print("  Run: python seed.py --demo")
            return

        if reset:
            await reset_demo_data(db)

        print("\n[1/5] Projects...")
        projects = await seed_projects(db, admin, pm)

        print("\n[2/5] Tasks...")
        await seed_tasks(db, projects, pm)

        print("\n[3/5] Daily briefing...")
        await seed_briefing(db, pm)

        print("\n[4/5] Documents (stubs)...")
        await seed_documents(db, projects, pm)

        print("\n[5/5] Emails...")
        await seed_emails(db, projects)

        print("\nDone! Log in as pm@example.com / pm123456 to see the demo data.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for Coffee Time Saver")
    parser.add_argument("--reset", action="store_true", help="Wipe existing demo data before inserting")
    args = parser.parse_args()
    asyncio.run(main(args.reset))
