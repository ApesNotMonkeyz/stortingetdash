"""
Cache for saksanalyser — dual-backend.

Når DATABASE_URL ikke er konfigurert (f.eks. i tester), brukes en in-memory dict
identisk med den som lå i pipeline.py. Når DATABASE_URL er satt, skrives og leses
fra saksanalyser-tabellen i PostgreSQL.

cache_tøm() tømmer alltid dict-cachen og brukes primært i tester.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog

from app.db.session import get_session_factory
from app.models.analyse import Saksanalyse

log = structlog.get_logger()

_TTL_SEKUNDER = 86_400

# In-memory fallback — aktiv når DATABASE_URL ikke er satt
_dict: dict[int, tuple[Saksanalyse, float | None]] = {}


async def cache_hent(sak_id: int) -> Saksanalyse | None:
    factory = get_session_factory()
    if factory is None:
        return _dict_hent(sak_id)
    return await _db_hent(sak_id, factory)


async def cache_sett(sak_id: int, analyse: Saksanalyse, *, permanent: bool) -> None:
    factory = get_session_factory()
    if factory is None:
        _dict_sett(sak_id, analyse, permanent=permanent)
    else:
        await _db_sett(sak_id, analyse, permanent=permanent, factory=factory)


def cache_tøm() -> None:
    """Tøm in-memory cache. Primært for tester."""
    _dict.clear()


# ── Dict-backend ──────────────────────────────────────────────────────────────

def _dict_hent(sak_id: int) -> Saksanalyse | None:
    entry = _dict.get(sak_id)
    if entry is None:
        return None
    analyse, utloper = entry
    if utloper is not None and time.monotonic() > utloper:
        del _dict[sak_id]
        log.info("cache_utlopt", sak_id=sak_id, backend="dict")
        return None
    return analyse


def _dict_sett(sak_id: int, analyse: Saksanalyse, *, permanent: bool) -> None:
    utloper = None if permanent else time.monotonic() + _TTL_SEKUNDER
    _dict[sak_id] = (analyse, utloper)
    log.info("cache_lagret", sak_id=sak_id, permanent=permanent, backend="dict")


# ── DB-backend ────────────────────────────────────────────────────────────────

async def _db_hent(sak_id: int, factory) -> Saksanalyse | None:  # type: ignore[type-arg]
    from app.db.models import DbSaksanalyse
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    async with factory() as session:
        row: DbSaksanalyse | None = await session.get(DbSaksanalyse, sak_id)
        if row is None:
            return None
        row_utloper = row.utloper.replace(tzinfo=None) if row.utloper and row.utloper.tzinfo else row.utloper
        if row_utloper is not None and row_utloper < now:
            await session.delete(row)
            await session.commit()
            log.info("cache_utlopt", sak_id=sak_id, backend="db")
            return None
        return Saksanalyse.model_validate(row.analyse_json)


async def _db_sett(sak_id: int, analyse: Saksanalyse, *, permanent: bool, factory) -> None:  # type: ignore[type-arg]
    from sqlalchemy.dialects.postgresql import insert

    from app.db.models import DbSaksanalyse

    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    utloper = None if permanent else datetime.fromtimestamp(
        time.time() + _TTL_SEKUNDER, tz=timezone.utc
    ).replace(tzinfo=None)
    stmt = (
        insert(DbSaksanalyse)
        .values(
            sak_id=sak_id,
            pub_id=analyse.pub_id,
            analyse_json=analyse.model_dump(mode="json"),
            opprettet=now,
            utloper=utloper,
        )
        .on_conflict_do_update(
            index_elements=["sak_id"],
            set_={
                "pub_id": analyse.pub_id,
                "analyse_json": analyse.model_dump(mode="json"),
                "utloper": utloper,
            },
        )
    )
    async with factory() as session:
        await session.execute(stmt)
        await session.commit()
    log.info("cache_lagret", sak_id=sak_id, permanent=permanent, backend="db")
