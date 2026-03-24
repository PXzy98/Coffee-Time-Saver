import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime
from typing import Optional


def decode_mime_words(s: str) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


class IMAPClient:
    def __init__(self, host: str, port: int, user: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.folder = folder

    def fetch_unseen(self) -> list[dict]:
        """Connect, fetch UNSEEN emails, mark as SEEN, return list of dicts."""
        conn = imaplib.IMAP4_SSL(self.host, self.port)
        conn.login(self.user, self.password)
        conn.select(self.folder)

        _, msg_ids = conn.search(None, "UNSEEN")
        messages = []
        for msg_id in msg_ids[0].split():
            _, msg_data = conn.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            body_text = ""
            body_html = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    disposition = part.get("Content-Disposition", "")
                    if "attachment" in disposition:
                        fname = part.get_filename()
                        if fname:
                            attachments.append({
                                "filename": decode_mime_words(fname),
                                "mime_type": content_type,
                                "data": part.get_payload(decode=True),
                            })
                    elif content_type == "text/plain":
                        body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    elif content_type == "text/html":
                        body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode("utf-8", errors="replace")

            messages.append({
                "message_id": msg.get("Message-ID"),
                "from_address": decode_mime_words(msg.get("From", "")),
                "to_addresses": [decode_mime_words(a) for a in (msg.get("To", "") or "").split(",")],
                "cc_addresses": [decode_mime_words(a) for a in (msg.get("CC", "") or "").split(",") if a.strip()],
                "subject": decode_mime_words(msg.get("Subject", "")),
                "body_text": body_text,
                "body_html": body_html,
                "received_at": msg.get("Date"),
                "attachments": attachments,
            })

        conn.close()
        conn.logout()
        return messages
