"""OAuth2 flow for IMAP email bot — authorize + callback endpoints."""
import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from config import settings

logger = logging.getLogger("coffee_time_saver")
router = APIRouter(prefix="/api/email-oauth", tags=["email-oauth"])


@router.get("/authorize")
async def authorize():
    """Redirect admin to the OAuth2 provider's consent page."""
    if not settings.IMAP_OAUTH_CLIENT_ID or not settings.IMAP_OAUTH_AUTHORIZE_URL:
        raise HTTPException(400, "OAuth2 not configured — set IMAP_OAUTH_* in .env")

    params = {
        "client_id": settings.IMAP_OAUTH_CLIENT_ID,
        "redirect_uri": settings.IMAP_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": settings.IMAP_OAUTH_SCOPE,
    }
    url = f"{settings.IMAP_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str):
    """Exchange authorization code for access + refresh tokens."""
    if not code:
        raise HTTPException(400, "Missing authorization code")

    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.IMAP_OAUTH_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.IMAP_OAUTH_REDIRECT_URI,
            "client_id": settings.IMAP_OAUTH_CLIENT_ID,
            "client_secret": settings.IMAP_OAUTH_CLIENT_SECRET,
        })

    if resp.status_code != 200:
        logger.error("OAuth token exchange failed: %s", resp.text)
        raise HTTPException(502, f"Token exchange failed: {resp.text}")

    data = resp.json()
    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    # Persist tokens — update settings at runtime and write to .env
    settings.IMAP_OAUTH_ACCESS_TOKEN = access_token
    settings.IMAP_OAUTH_REFRESH_TOKEN = refresh_token
    _update_env_file(access_token, refresh_token)

    logger.info("OAuth2 tokens obtained and saved to .env")
    return {
        "status": "ok",
        "message": "Email OAuth2 connected successfully. Tokens saved to .env.",
    }


def _update_env_file(access_token: str, refresh_token: str) -> None:
    """Append/update OAuth tokens in .env file."""
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    token_keys = {
        "IMAP_OAUTH_ACCESS_TOKEN": access_token,
        "IMAP_OAUTH_REFRESH_TOKEN": refresh_token,
    }

    updated_keys = set()
    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in token_keys:
            new_lines.append(f"{key}={token_keys[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, val in token_keys.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)
