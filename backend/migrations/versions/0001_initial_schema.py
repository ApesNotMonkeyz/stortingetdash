"""Initial schema: saksanalyser, voteringer, voteringsresultat_parti,
parti_moenster, fraksjon_plenum_konsistens, parti_korrelasjon, saksprediksjoner

Revision ID: 0001
Revises:
Create Date: 2026-04-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saksanalyser",
        sa.Column("sak_id", sa.Integer(), primary_key=True),
        sa.Column("pub_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("analyse_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "opprettet",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("utloper", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_saksanalyser_utloper", "saksanalyser", ["utloper"])

    op.create_table(
        "voteringer",
        sa.Column("votering_id", sa.Text(), primary_key=True),
        sa.Column("sak_id", sa.Integer(), nullable=False),
        sa.Column("sesjon", sa.Text(), nullable=False),
        sa.Column("dato", sa.Date(), nullable=False),
        sa.Column("tema", sa.Text(), nullable=True),
        sa.Column("saksfelt", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("dokumentgruppe", sa.Text(), nullable=True),
        sa.Column("vedtatt", sa.Boolean(), nullable=True),
        sa.Column(
            "hentet_tidspunkt",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_voteringer_sak_id", "voteringer", ["sak_id"])
    op.create_index("ix_voteringer_sesjon", "voteringer", ["sesjon"])
    op.create_index("ix_voteringer_dato", "voteringer", ["dato"])
    # GIN-indeks for array-søk på saksfelt
    op.create_index(
        "ix_voteringer_saksfelt_gin",
        "voteringer",
        ["saksfelt"],
        postgresql_using="gin",
    )

    op.create_table(
        "voteringsresultat_parti",
        sa.Column(
            "votering_id",
            sa.Text(),
            sa.ForeignKey("voteringer.votering_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("parti", sa.Text(), primary_key=True),
        sa.Column("for_stemmer", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mot_stemmer", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fravarende", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "parti_moenster",
        sa.Column("parti", sa.Text(), primary_key=True),
        sa.Column("saksfelt", sa.Text(), primary_key=True),
        sa.Column("dokumentgruppe", sa.Text(), primary_key=True),
        sa.Column("antall_voteringer", sa.Integer(), nullable=False),
        sa.Column("andel_for", sa.Float(), nullable=False),
        sa.Column("andel_mot", sa.Float(), nullable=False),
        sa.Column(
            "sist_oppdatert",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "fraksjon_plenum_konsistens",
        sa.Column("parti", sa.Text(), primary_key=True),
        sa.Column("saksfelt", sa.Text(), primary_key=True),
        sa.Column("antall_saker_med_fraksjoninfo", sa.Integer(), nullable=False),
        sa.Column("antall_konsistente", sa.Integer(), nullable=False),
        sa.Column("andel_konsistent", sa.Float(), nullable=False),
        sa.Column(
            "sist_oppdatert",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "parti_korrelasjon",
        sa.Column("parti_a", sa.Text(), primary_key=True),
        sa.Column("parti_b", sa.Text(), primary_key=True),
        sa.Column("saksfelt", sa.Text(), primary_key=True),
        sa.Column("andel_lik_stemme", sa.Float(), nullable=False),
        sa.Column("antall_voteringer", sa.Integer(), nullable=False),
        sa.Column(
            "sist_oppdatert",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "saksprediksjoner",
        sa.Column("sak_id", sa.Integer(), primary_key=True),
        sa.Column("prediksjoner_json", postgresql.JSONB(), nullable=False),
        sa.Column("signalkilder", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("prompt_versjon", sa.Text(), nullable=True),
        sa.Column(
            "opprettet",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("utloper", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_saksprediksjoner_utloper", "saksprediksjoner", ["utloper"])


def downgrade() -> None:
    op.drop_table("saksprediksjoner")
    op.drop_table("parti_korrelasjon")
    op.drop_table("fraksjon_plenum_konsistens")
    op.drop_table("parti_moenster")
    op.drop_table("voteringsresultat_parti")
    op.drop_table("voteringer")
    op.drop_table("saksanalyser")
