"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("preferred_lang", sa.String(2), server_default="en"),
        sa.Column("auth_provider", sa.String(20), server_default="local"),
        sa.Column("external_id", sa.String(255)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id"), primary_key=True),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("is_shared", sa.Boolean, server_default="false"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "project_members",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(20), server_default="member"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("priority", sa.Integer, server_default="50"),
        sa.Column("due_date", sa.Date),
        sa.Column("is_completed", sa.Boolean, server_default="false"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("source", sa.String(20), server_default="manual"),
        sa.Column("sort_score", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("full_text", sa.Text),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("source", sa.String(20), server_default="upload"),
        sa.Column("doc_type", sa.String(20), server_default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("content_lang", sa.String(2)),
        sa.Column("structured_data", postgresql.JSONB),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add vector column separately (pgvector type cannot be expressed in plain SA Column)
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    # IVFFlat index — deferred until data exists; created here as empty-table safe
    # (pgvector ≥ 0.5 allows creating IVFFlat on empty tables)
    op.execute("CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    op.create_table(
        "daily_briefings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("content_en", sa.Text),
        sa.Column("content_fr", sa.Text),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_briefings_user_date"),
    )

    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.String(500), unique=True),
        sa.Column("from_address", sa.String(255)),
        sa.Column("to_addresses", postgresql.ARRAY(sa.Text)),
        sa.Column("cc_addresses", postgresql.ARRAY(sa.Text)),
        sa.Column("subject", sa.String(1000)),
        sa.Column("body_text", sa.Text),
        sa.Column("body_html", sa.Text),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("processed", sa.Boolean, server_default="false"),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "email_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("emails.id", ondelete="CASCADE")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.String(255)),
        sa.Column("details", postgresql.JSONB, server_default="{}"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_user", "audit_logs", ["user_id", "created_at"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action", "created_at"])

    op.create_table(
        "llm_configs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("api_url", sa.String(500), nullable=False),
        sa.Column("api_key", sa.String(500)),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tool_modules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_fr", sa.String(200), nullable=False),
        sa.Column("description_en", sa.Text),
        sa.Column("description_fr", sa.Text),
        sa.Column("icon", sa.String(50)),
        sa.Column("api_endpoint", sa.String(200), nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed default roles and permissions
    op.execute("INSERT INTO roles (name) VALUES ('admin'), ('pm')")
    op.execute("""
        INSERT INTO permissions (code) VALUES
        ('project:read:own'), ('project:read:shared'), ('project:write:own'),
        ('project:write:admin'), ('task:read:own'), ('task:write:own'),
        ('file:upload'), ('briefing:read'), ('settings:llm:write'),
        ('settings:email:write'), ('admin:user:manage'), ('tools:risk_analyzer:execute')
    """)
    # Assign all permissions to admin, basic ones to pm
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'admin'
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'pm' AND p.code IN (
            'project:read:own', 'project:read:shared', 'project:write:own',
            'task:read:own', 'task:write:own', 'file:upload',
            'briefing:read', 'tools:risk_analyzer:execute'
        )
    """)

    # Seed risk analyzer tool module
    op.execute("""
        INSERT INTO tool_modules (slug, name_en, name_fr, description_en, description_fr, icon, api_endpoint, sort_order)
        VALUES (
            'risk-analyzer',
            'Project Risk Analyzer',
            'Analyseur de risques projet',
            'Identify risks, inconsistencies, and scope drift across all project documents.',
            'Identifiez les risques, incohérences et dérives de portée dans tous les documents du projet.',
            'shield-alert',
            '/api/tools/risk-analyzer',
            1
        )
    """)


def downgrade() -> None:
    op.drop_table("tool_modules")
    op.drop_table("llm_configs")
    op.drop_index("idx_audit_logs_action")
    op.drop_index("idx_audit_logs_user")
    op.drop_table("audit_logs")
    op.drop_table("email_attachments")
    op.drop_table("emails")
    op.drop_table("daily_briefings")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("tasks")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
