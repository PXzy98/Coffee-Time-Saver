"""
Plan B — Upload test documents via the real HTTP pipeline.

Each file goes through the full stack:
  POST /api/files/upload → Celery worker → parse → chunk → embed
  → extract_tasks → suggest_project (WebSocket)

Requirements:
  - uvicorn must be running  (uvicorn main:app --reload)
  - celery worker must be running  (celery -A tasks worker --loglevel=info)
  - PostgreSQL + Redis containers must be up

Usage:
    python upload_test_docs.py                        # upload all files, poll until done
    python upload_test_docs.py --no-poll              # upload and exit (don't wait)
    python upload_test_docs.py --base-url http://localhost:8000
    python upload_test_docs.py --email pm@example.com --password pm123456
"""

import argparse
import asyncio
import pathlib
import sys

TEST_DATA_DIR = pathlib.Path(__file__).parent.parent / "test_data" / "autogenerate"

# Files to upload and optional project name hint (used only for display; the
# project suggestion feature is expected to match automatically).
FILES = [
    "kickoff_meeting_metro_line6.txt",
    "erp_upgrade_action_items.txt",
    "office_relocation_vendor_proposal.md",
    "erp_data_migration_checklist.md",
    "infrastructure_security_assessment.md",
    "general_reference_glossary.txt",
]


async def run(base_url: str, email: str, password: str, poll: bool) -> None:
    try:
        import httpx
    except ImportError:
        print("[error] httpx not installed — run: pip install httpx")
        sys.exit(1)

    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        # 1. Login
        print(f"[auth] logging in as {email} ...")
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        if resp.status_code != 200:
            print(f"[error] login failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[auth] ok")

        # 2. Upload each file
        doc_ids: list[tuple[str, str]] = []   # (filename, document_id)
        for filename in FILES:
            filepath = TEST_DATA_DIR / filename
            if not filepath.exists():
                print(f"[skip] {filename} — not found")
                continue

            mime = {
                ".txt":  "text/plain",
                ".md":   "text/markdown",
                ".pdf":  "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }.get(filepath.suffix.lower(), "text/plain")

            with filepath.open("rb") as fh:
                resp = client.post(
                    "/api/files/upload",
                    headers=headers,
                    files={"file": (filename, fh, mime)},
                    data={"doc_type": "general"},
                )

            if resp.status_code not in (200, 201):
                print(f"[error] upload failed for {filename}: {resp.status_code} {resp.text}")
                continue

            doc_id = resp.json().get("document_id", "?")
            doc_ids.append((filename, doc_id))
            print(f"[upload] {filename}  →  document_id={doc_id}")

        if not poll or not doc_ids:
            print(f"\n[done] {len(doc_ids)} file(s) uploaded. Celery will process them in background.")
            return

        # 3. Poll for completion
        print(f"\n[poll] waiting for Celery pipeline to complete ...")
        import time
        pending = dict(doc_ids)
        max_wait = 300   # 5 minutes
        start = time.time()

        while pending and (time.time() - start) < max_wait:
            await asyncio.sleep(5)
            for filename, doc_id in list(pending.items()):
                resp = client.get(f"/api/files/{doc_id}/status", headers=headers)
                if resp.status_code != 200:
                    continue
                status = resp.json().get("status", "unknown")
                if status in ("completed", "failed"):
                    icon = "[ok]" if status == "completed" else "[fail]"
                    print(f"  {icon} {filename}  ({status})")
                    del pending[filename]

        if pending:
            print(f"[timeout] still pending after {max_wait}s: {list(pending.keys())}")
        else:
            print(f"\n[done] all files processed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload test documents via HTTP pipeline (Plan B)")
    parser.add_argument("--base-url",  default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--email",     default="pm@example.com")
    parser.add_argument("--password",  default="pm123456")
    parser.add_argument("--no-poll",   action="store_true", help="Don't wait for Celery processing")
    args = parser.parse_args()

    asyncio.run(run(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        poll=not args.no_poll,
    ))
