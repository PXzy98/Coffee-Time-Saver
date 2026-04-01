"""
Plan C — Direct DB injection of test documents.

Reads files from test_data/autogenerate/, inserts Document rows with
status="completed" and full_text populated. No Celery / uvicorn required.
Only needs PostgreSQL running.

Usage:
    python inject_test_docs.py              # inject all files
    python inject_test_docs.py --reset      # delete previously injected docs first
    python inject_test_docs.py --dry-run    # print what would be inserted, touch nothing
"""

import argparse
import asyncio
import pathlib
import uuid

from sqlalchemy import select, delete

# ---------------------------------------------------------------------------
# File → project name mapping.
# None means "no project" (tests the 'none' / 'new' suggestion path).
# ---------------------------------------------------------------------------
FILE_PROJECT_MAP = {
    "kickoff_meeting_metro_line6.txt":       "[DEMO] Metro Line 6 Extension",
    "erp_upgrade_action_items.txt":          "[DEMO] ERP System Upgrade",
    "office_relocation_vendor_proposal.md":  "[DEMO] Office Relocation Q3",
    "erp_data_migration_checklist.md":       "[DEMO] ERP System Upgrade",
    "infrastructure_security_assessment.md": None,   # new-project candidate
    "general_reference_glossary.txt":        None,   # should produce match_type=none
}

TEST_DATA_DIR = pathlib.Path(__file__).parent.parent / "test_data" / "autogenerate"
SOURCE_TAG = "inject_test"   # lets us identify and --reset these rows later


def _mime(filename: str) -> str:
    ext = pathlib.Path(filename).suffix.lower()
    return {
        ".txt": "text/plain",
        ".md":  "text/markdown",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "text/plain")


async def run(reset: bool, dry_run: bool) -> None:
    from core.database import AsyncSessionLocal
    from core.models import Document, Project, User

    async with AsyncSessionLocal() as db:
        # --reset: remove previously injected docs
        if reset and not dry_run:
            result = await db.execute(
                delete(Document).where(Document.source == SOURCE_TAG)
            )
            await db.commit()
            print(f"[reset] deleted {result.rowcount} previously injected document(s)")

        # Look up demo user (prefer pm@, fall back to admin@)
        user_result = await db.execute(
            select(User).where(User.email.in_(["pm@example.com", "admin@example.com"]))
        )
        users = {u.email: u for u in user_result.scalars().all()}
        uploader = users.get("pm@example.com") or users.get("admin@example.com")
        if not uploader:
            print("[error] no user found — run seed.py --demo first")
            return
        print(f"[uploader] {uploader.email} ({uploader.id})")

        # Look up all projects once
        proj_result = await db.execute(select(Project))
        projects = {p.name: p for p in proj_result.scalars().all()}

        # Iterate files
        inserted = 0
        for filename, project_name in FILE_PROJECT_MAP.items():
            filepath = TEST_DATA_DIR / filename
            if not filepath.exists():
                print(f"[skip] {filename} — file not found at {filepath}")
                continue

            full_text = filepath.read_text(encoding="utf-8")

            project = projects.get(project_name) if project_name else None
            if project_name and not project:
                print(f"[warn] project '{project_name}' not found in DB — inserting without project link")

            if dry_run:
                proj_label = project.name if project else "(no project)"
                print(f"[dry-run] {filename}  {len(full_text):,} chars  -> {proj_label}")
                continue

            doc = Document(
                id=uuid.uuid4(),
                project_id=project.id if project else None,
                uploaded_by=uploader.id,
                filename=filename,
                mime_type=_mime(filename),
                file_size_bytes=filepath.stat().st_size,
                full_text=full_text,
                status="completed",
                source=SOURCE_TAG,
                doc_type="general",
            )
            db.add(doc)
            proj_label = project.name if project else "(no project)"
            print(f"[insert] {filename}  {len(full_text):,} chars  -> {proj_label}")
            inserted += 1

        if not dry_run:
            await db.commit()
            print(f"\n[done] inserted {inserted} document(s)")
        else:
            print(f"\n[dry-run] would insert {sum(1 for f in FILE_PROJECT_MAP if (TEST_DATA_DIR / f).exists())} document(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject test documents directly into the database (Plan C)")
    parser.add_argument("--reset",   action="store_true", help="Delete previously injected docs before inserting")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without touching the DB")
    args = parser.parse_args()

    asyncio.run(run(reset=args.reset, dry_run=args.dry_run))
