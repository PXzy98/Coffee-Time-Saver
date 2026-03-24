"""Unit tests for JWT and password utilities — no database required."""
import uuid
import pytest
from core.auth.jwt import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from core.auth.password import hash_password, verify_password


# ── Password ──────────────────────────────────────────────────────────────────

def test_hash_and_verify():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)


def test_wrong_password_fails():
    hashed = hash_password("mysecret")
    assert not verify_password("wrong", hashed)


def test_hashes_are_unique():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt includes salt


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_access_token_round_trip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, ["admin"])
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert "admin" in payload["roles"]


def test_refresh_token_round_trip():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)


def test_wrong_token_type_rejected():
    user_id = uuid.uuid4()
    access = create_access_token(user_id, [])
    # decode_refresh_token should reject an access token
    assert decode_refresh_token(access) is None


def test_invalid_token_returns_none():
    assert decode_access_token("not.a.token") is None


def test_tampered_token_returns_none():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, [])
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None
