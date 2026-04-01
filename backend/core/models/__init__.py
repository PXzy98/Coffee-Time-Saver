import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, BigInteger, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, func, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from core.database import Base


# ---------------------------------------------------------------------------
# Auth & Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_lang: Mapped[str] = mapped_column(String(2), default="en")
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="uploader")
    briefings: Mapped[list["DailyBriefing"]] = relationship("DailyBriefing", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role")
    role_permissions: Mapped[list["RolePermission"]] = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), primary_key=True)

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id"), primary_key=True)

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(20), default="manual")
    sort_score: Mapped[Optional[float]] = mapped_column(Float)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="tasks")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")


# ---------------------------------------------------------------------------
# Documents & Ingestion
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    source: Mapped[str] = mapped_column(String(20), default="upload")
    doc_type: Mapped[str] = mapped_column(String(20), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Pre-computed document-level summary (populated at ingestion time)
    doc_summary: Mapped[Optional[str]] = mapped_column(Text)
    doc_summary_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    doc_summary_model: Mapped[Optional[str]] = mapped_column(String(100))
    doc_summary_hash: Mapped[Optional[str]] = mapped_column(String(64))

    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_lang: Mapped[Optional[str]] = mapped_column(String(2))
    structured_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Pre-computed chunk-level summary (populated at ingestion time)
    summary_text: Mapped[Optional[str]] = mapped_column(Text)
    summary_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    summary_model: Mapped[Optional[str]] = mapped_column(String(100))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


# ---------------------------------------------------------------------------
# Daily Briefings
# ---------------------------------------------------------------------------

class DailyBriefing(Base):
    __tablename__ = "daily_briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    content_en: Mapped[Optional[str]] = mapped_column(Text)
    content_fr: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="briefings")


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------

class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[Optional[str]] = mapped_column(String(500), unique=True)
    from_address: Mapped[Optional[str]] = mapped_column(String(255))
    to_addresses: Mapped[Optional[list]] = mapped_column(ARRAY(Text))
    cc_addresses: Mapped[Optional[list]] = mapped_column(ARRAY(Text))
    subject: Mapped[Optional[str]] = mapped_column(String(1000))
    body_text: Mapped[Optional[str]] = mapped_column(Text)
    body_html: Mapped[Optional[str]] = mapped_column(Text)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attachments: Mapped[list["EmailAttachment"]] = relationship("EmailAttachment", back_populates="email", cascade="all, delete-orphan")


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"))
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    email: Mapped["Email"] = relationship("Email", back_populates="attachments")


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# LLM Config
# ---------------------------------------------------------------------------

class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    api_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[Optional[str]] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Tool Modules
# ---------------------------------------------------------------------------

class ToolModule(Base):
    __tablename__ = "tool_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_fr: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    api_endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
