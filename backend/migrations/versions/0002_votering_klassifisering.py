"""Legg til alternativ_votering_id og votering_resultat_type i voteringer-tabellen.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voteringer",
        sa.Column("alternativ_votering_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "voteringer",
        sa.Column("votering_resultat_type", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voteringer", "votering_resultat_type")
    op.drop_column("voteringer", "alternativ_votering_id")
