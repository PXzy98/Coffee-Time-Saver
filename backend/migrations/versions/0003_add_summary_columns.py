"""Add pre-computed summary columns to documents and document_chunks

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # document_chunks — chunk-level summary
    op.add_column("document_chunks", sa.Column("summary_text", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("summary_metadata", JSONB(), nullable=True))
    op.add_column("document_chunks", sa.Column("summary_model", sa.String(100), nullable=True))
    op.add_column("document_chunks", sa.Column("content_hash", sa.String(64), nullable=True))

    # documents — document-level summary
    op.add_column("documents", sa.Column("doc_summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("doc_summary_metadata", JSONB(), nullable=True))
    op.add_column("documents", sa.Column("doc_summary_model", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("doc_summary_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "doc_summary_hash")
    op.drop_column("documents", "doc_summary_model")
    op.drop_column("documents", "doc_summary_metadata")
    op.drop_column("documents", "doc_summary")

    op.drop_column("document_chunks", "content_hash")
    op.drop_column("document_chunks", "summary_model")
    op.drop_column("document_chunks", "summary_metadata")
    op.drop_column("document_chunks", "summary_text")
