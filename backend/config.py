from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cts:cts_password@localhost:5432/coffee_time_saver"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # IMAP Email Bot
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_FOLDER: str = "INBOX"
    IMAP_POLL_INTERVAL_SECONDS: int = 300
    IMAP_AUTH_METHOD: Literal["password", "oauth2"] = "password"
    IMAP_OWNER_EMAIL: str = ""  # If set, emails are assigned to this user; defaults to first active user

    # OAuth2 for IMAP (Yahoo / Google / Microsoft)
    IMAP_OAUTH_CLIENT_ID: str = ""
    IMAP_OAUTH_CLIENT_SECRET: str = ""
    IMAP_OAUTH_AUTHORIZE_URL: str = ""
    IMAP_OAUTH_TOKEN_URL: str = ""
    IMAP_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/email-oauth/callback"
    IMAP_OAUTH_SCOPE: str = ""
    IMAP_OAUTH_ACCESS_TOKEN: str = ""
    IMAP_OAUTH_REFRESH_TOKEN: str = ""

    # Strategy config keys
    TASK_SORTER_STRATEGY: Literal["hardcoded", "llm"] = "hardcoded"
    PDF_PARSER_STRATEGY: Literal["pymupdf", "ocr"] = "pymupdf"
    DOCX_PARSER_STRATEGY: Literal["python-docx", "llm"] = "python-docx"
    STRUCTURER_STRATEGY: Literal["regex", "llm"] = "regex"
    BRIEFING_STRATEGY: Literal["template", "llm"] = "template"

    # Email intelligence strategies
    EMAIL_TASK_STRATEGY: Literal["regex", "llm"] = "regex"
    EMAIL_PROJECT_SUGGESTION: Literal["off", "llm"] = "off"

    # Task-to-project association (applies to both email and file extracted tasks)
    TASK_PROJECT_ASSOCIATION: Literal["manual", "llm"] = "manual"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # LLM key encryption
    ENCRYPTION_KEY: str = "change-me-32-bytes-key-for-fernet"


settings = Settings()
