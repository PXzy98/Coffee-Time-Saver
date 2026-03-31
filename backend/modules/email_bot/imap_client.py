import base64
import imaplib
import email as email_lib
import logging
from email.header import decode_header
from typing import Optional

import httpx

logger = logging.getLogger("coffee_time_saver")


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


def _build_xoauth2_string(user: str, access_token: str) -> str:
    """Build XOAUTH2 SASL string: user=<user>\\x01auth=Bearer <token>\\x01\\x01"""
    return f"user={user}\x01auth=Bearer {access_token}\x01\x01"


def refresh_access_token(token_url: str, client_id: str, client_secret: str,
                         refresh_token: str) -> dict:
    """Exchange refresh_token for a new access_token. Returns the token response dict."""
    resp = httpx.post(token_url, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    return resp.json()


class IMAPClient:
    def __init__(self, host: str, port: int, user: str, password: str,
                 folder: str = "INBOX", auth_method: str = "password",
                 oauth_access_token: str = "", oauth_refresh_token: str = "",
                 oauth_client_id: str = "", oauth_client_secret: str = "",
                 oauth_token_url: str = ""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.folder = folder
        self.auth_method = auth_method
        self.oauth_access_token = oauth_access_token
        self.oauth_refresh_token = oauth_refresh_token
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_token_url = oauth_token_url

    def _authenticate(self, conn: imaplib.IMAP4_SSL) -> None:
        """Login via password or XOAUTH2 depending on auth_method."""
        if self.auth_method == "oauth2":
            # Try current access token first
            xoauth2_str = _build_xoauth2_string(self.user, self.oauth_access_token)
            try:
                conn.authenticate(
                    "XOAUTH2",
                    lambda _: xoauth2_str.encode(),
                )
                return
            except imaplib.IMAP4.error:
                logger.info("XOAUTH2 auth failed, attempting token refresh")

            # Refresh and retry
            if not self.oauth_refresh_token:
                raise RuntimeError("OAuth2 access token expired and no refresh token available")

            token_data = refresh_access_token(
                self.oauth_token_url, self.oauth_client_id,
                self.oauth_client_secret, self.oauth_refresh_token,
            )
            self.oauth_access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.oauth_refresh_token = token_data["refresh_token"]

            xoauth2_str = _build_xoauth2_string(self.user, self.oauth_access_token)
            conn.authenticate(
                "XOAUTH2",
                lambda _: xoauth2_str.encode(),
            )
        else:
            conn.login(self.user, self.password)

    def fetch_unseen(self) -> list[dict]:
        """Connect, fetch UNSEEN emails, mark as SEEN, return list of dicts."""
        conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._authenticate(conn)
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
