from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DbSaksanalyse(Base):
    __tablename__ = "saksanalyser"

    sak_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pub_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    analyse_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    opprettet: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    utloper: Mapped[datetime | None] = mapped_column(nullable=True)


class DbVotering(Base):
    __tablename__ = "voteringer"

    votering_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sak_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sesjon: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    dato: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    tema: Mapped[str | None] = mapped_column(Text, nullable=True)
    saksfelt: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    dokumentgruppe: Mapped[str | None] = mapped_column(Text, nullable=True)
    vedtatt: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    alternativ_votering_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    votering_resultat_type: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hentet_tidspunkt: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class DbVoteringsresultatParti(Base):
    __tablename__ = "voteringsresultat_parti"

    votering_id: Mapped[str] = mapped_column(
        Text, ForeignKey("voteringer.votering_id", ondelete="CASCADE"), primary_key=True
    )
    parti: Mapped[str] = mapped_column(Text, primary_key=True)
    for_stemmer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mot_stemmer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fravarende: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DbPartiMoenster(Base):
    __tablename__ = "parti_moenster"

    parti: Mapped[str] = mapped_column(Text, primary_key=True)
    saksfelt: Mapped[str] = mapped_column(Text, primary_key=True)
    dokumentgruppe: Mapped[str] = mapped_column(Text, primary_key=True)
    antall_voteringer: Mapped[int] = mapped_column(Integer, nullable=False)
    andel_for: Mapped[float] = mapped_column(Float, nullable=False)
    andel_mot: Mapped[float] = mapped_column(Float, nullable=False)
    sist_oppdatert: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class DbFraksjonPlenumKonsistens(Base):
    __tablename__ = "fraksjon_plenum_konsistens"

    parti: Mapped[str] = mapped_column(Text, primary_key=True)
    saksfelt: Mapped[str] = mapped_column(Text, primary_key=True)
    antall_saker_med_fraksjoninfo: Mapped[int] = mapped_column(Integer, nullable=False)
    antall_konsistente: Mapped[int] = mapped_column(Integer, nullable=False)
    andel_konsistent: Mapped[float] = mapped_column(Float, nullable=False)
    sist_oppdatert: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class DbPartiKorrelasjon(Base):
    __tablename__ = "parti_korrelasjon"

    parti_a: Mapped[str] = mapped_column(Text, primary_key=True)
    parti_b: Mapped[str] = mapped_column(Text, primary_key=True)
    saksfelt: Mapped[str] = mapped_column(Text, primary_key=True)
    andel_lik_stemme: Mapped[float] = mapped_column(Float, nullable=False)
    antall_voteringer: Mapped[int] = mapped_column(Integer, nullable=False)
    sist_oppdatert: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class DbSaksprediksjon(Base):
    __tablename__ = "saksprediksjoner"

    sak_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediksjoner_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signalkilder: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    prompt_versjon: Mapped[str | None] = mapped_column(Text, nullable=True)
    opprettet: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    utloper: Mapped[datetime | None] = mapped_column(nullable=True)


class DbStortingetCache(Base):
    __tablename__ = "stortinget_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    data_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    opprettet: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    utloper: Mapped[datetime | None] = mapped_column(nullable=True)
