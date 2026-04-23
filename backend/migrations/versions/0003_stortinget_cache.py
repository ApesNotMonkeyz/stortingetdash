"""Legg til stortinget_cache — generell TTL-basert cache for Stortinget API-data.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-23
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stortinget_cache",
        sa.Column("cache_key", sa.Text(), primary_key=True),
        sa.Column("data_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "opprettet",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("utloper", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_stortinget_cache_utloper", "stortinget_cache", ["utloper"])


def downgrade() -> None:
    op.drop_index("ix_stortinget_cache_utloper", table_name="stortinget_cache")
    op.drop_table("stortinget_cache")
