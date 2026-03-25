from typing import Optional
from pydantic import BaseModel
import uuid


class LLMConfigOut(BaseModel):
    id: int
    name: str
    provider: str
    api_url: str
    model: str
    is_active: bool

    model_config = {"from_attributes": True}


class LLMConfigCreate(BaseModel):
    name: str
    provider: str
    api_url: str
    api_key: Optional[str] = None
    model: str
    is_active: bool = False


class LLMConfigUpdate(BaseModel):
    provider: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None


class EmailBotConfigOut(BaseModel):
    imap_host: str
    imap_port: int
    imap_user: str
    imap_folder: str
    poll_interval_seconds: int


class EmailBotConfigUpdate(BaseModel):
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_folder: Optional[str] = None
    poll_interval_seconds: Optional[int] = None


class UserAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}


class UserRoleUpdate(BaseModel):
    roles: list[str]
