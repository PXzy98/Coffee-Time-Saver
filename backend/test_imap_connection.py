"""Quick script to test IMAP connection to Hotmail/Outlook."""
import imaplib
import sys
sys.path.insert(0, ".")

from config import settings

print(f"Host:  {settings.IMAP_HOST}")
print(f"Port:  {settings.IMAP_PORT}")
print(f"User:  {settings.IMAP_USER}")
print(f"Auth:  {settings.IMAP_AUTH_METHOD}")
print()

try:
    print("Connecting...")
    conn = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
    print("Connected. Logging in...")
    conn.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
    print("Login OK!")

    conn.select("INBOX")
    _, msg_ids = conn.search(None, "ALL")
    total = len(msg_ids[0].split()) if msg_ids[0] else 0

    _, unseen_ids = conn.search(None, "UNSEEN")
    unseen = len(unseen_ids[0].split()) if unseen_ids[0] else 0

    print(f"\nINBOX: {total} total, {unseen} unseen")

    conn.close()
    conn.logout()
    print("\nConnection test PASSED")
except Exception as e:
    print(f"\nFAILED: {e}")
