"""Add handoff fields, app settings, and chunk embeddings.

Revision ID: 003_handoff_settings_embeddings
Revises: 002_agentic_tables
Create Date: 2026-10-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_handoff_settings_embeddings"
down_revision: Union[str, Sequence[str], None] = "002_agentic_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("assigned_agent_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "ai_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        "ix_conversations_assigned_agent_id",
        "conversations",
        ["assigned_agent_id"],
    )

    op.add_column(
        "knowledge_chunks",
        sa.Column("embedding_json", sa.Text(), nullable=True),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_column("knowledge_chunks", "embedding_json")
    op.drop_index("ix_conversations_assigned_agent_id", table_name="conversations")
    op.drop_column("conversations", "ai_enabled")
    op.drop_column("conversations", "assigned_agent_id")
