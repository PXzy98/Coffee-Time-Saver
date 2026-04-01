"""Fix llm_configs is_active default and ensure only one active config

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Change server_default from true to false
    op.alter_column(
        "llm_configs",
        "is_active",
        server_default="false",
        existing_type=sa.Boolean,
        existing_nullable=True,
    )

    # 2. Keep only the highest-id config active; deactivate all others
    op.execute("""
        UPDATE llm_configs
        SET is_active = false
        WHERE id != (
            SELECT id FROM llm_configs
            WHERE is_active = true
            ORDER BY id DESC
            LIMIT 1
        )
        AND is_active = true
    """)


def downgrade() -> None:
    op.alter_column(
        "llm_configs",
        "is_active",
        server_default="true",
        existing_type=sa.Boolean,
        existing_nullable=True,
    )
