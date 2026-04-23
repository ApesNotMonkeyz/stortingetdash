#!/usr/bin/env python3
"""
Henter voteringer og voteringsresultat per parti fra Stortingets API og
lagrer dem i PostgreSQL. Idempotent: upsert på votering_id/parti.

Bruk (kjøres fra backend/-mappen):
    python scripts/hent_voteringer.py
    python scripts/hent_voteringer.py --sesjoner 2023-2024
    python scripts/hent_voteringer.py --sesjoner 2023-2024 2024-2025

Avhengigheter: .env med DATABASE_URL satt.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
import structlog.stdlib
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# backend/ på sys.path slik at app.* kan importeres
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings
from app.db.models import DbVotering, DbVoteringsresultatParti

# ── Logging ───────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# ── Konstanter ────────────────────────────────────────────────────────────────

BASE_URL = "https://data.stortinget.no"
ALLE_SESJONER = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]

VOTERING_FOR = 1
VOTERING_MOT = 2
VOTERING_FRAVARENDE = 3

# ── Rate limiter ──────────────────────────────────────────────────────────────
# Stortinget tillater 100 kall/min. Vi holder oss på 88 for buffer.

_MAKS_KALL_PER_MIN = 88
_VINDU_SEK = 60.0
_kall_logg: list[float] = []


async def _vent_rate_limit() -> None:
    now = time.monotonic()
    while _kall_logg and now - _kall_logg[0] >= _VINDU_SEK:
        _kall_logg.pop(0)
    if len(_kall_logg) >= _MAKS_KALL_PER_MIN:
        pause = _VINDU_SEK - (now - _kall_logg[0]) + 0.2
        if pause > 0:
            log.info("rate_limit_pause", sekunder=round(pause, 1))
            await asyncio.sleep(pause)
    _kall_logg.append(time.monotonic())


# ── HTTP ──────────────────────────────────────────────────────────────────────


async def _get(client: httpx.AsyncClient, url: str, params: dict[str, str]) -> Any:
    """GET med exponential backoff på 429/5xx. Returnerer None ved 404."""
    await _vent_rate_limit()
    for forsok in range(3):
        try:
            r = await client.get(url, params=params)
        except httpx.TransportError:
            if forsok == 2:
                raise
            await asyncio.sleep(2**forsok)
            continue

        if r.status_code == 404:
            return None
        if r.status_code == 429:
            vent = float(r.headers.get("Retry-After", 30))
            log.warning("429_rate_limit", vent=vent)
            await asyncio.sleep(vent)
            continue
        if r.status_code >= 500:
            if forsok == 2:
                r.raise_for_status()
            await asyncio.sleep(2**forsok)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("unreachable")


# ── Datohjelper ───────────────────────────────────────────────────────────────


def _parse_dato(s: str | None) -> date | None:
    """Parser Microsoft JSON-datoformat: /Date(1744117615033+0200)/"""
    if not s:
        return None
    m = re.match(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", s)
    if not m:
        return None
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date()


# ── Aggregering ───────────────────────────────────────────────────────────────


def _aggreger_per_parti(resultater: list[dict]) -> dict[str, dict[str, int]]:
    """Summerer individuelle representantstemmer til partinivå."""
    agg: dict[str, dict[str, int]] = defaultdict(
        lambda: {"for_stemmer": 0, "mot_stemmer": 0, "fravarende": 0}
    )
    for r in resultater:
        parti = r.get("representant", {}).get("parti", {}).get("id") or "UKJENT"
        v = r.get("votering")
        if v == VOTERING_FOR:
            agg[parti]["for_stemmer"] += 1
        elif v == VOTERING_MOT:
            agg[parti]["mot_stemmer"] += 1
        elif v == VOTERING_FRAVARENDE:
            agg[parti]["fravarende"] += 1
    return agg


# ── DB-skriving ───────────────────────────────────────────────────────────────


async def _upsert_votering(
    db: AsyncSession,
    votering: dict,
    sak: dict,
    sesjon: str,
) -> None:
    dato = _parse_dato(votering.get("votering_tid"))
    saksfelt = [e["navn"] for e in sak.get("emne_liste", []) if e.get("navn")] or None

    raw_alt_id = votering.get("alternativ_votering_id", -1)
    alternativ_votering_id = None if (raw_alt_id is None or raw_alt_id == -1) else int(raw_alt_id)

    stmt = (
        pg_insert(DbVotering)
        .values(
            votering_id=str(votering["votering_id"]),
            sak_id=sak["id"],
            sesjon=sesjon,
            dato=dato or datetime.now(tz=timezone.utc).date(),
            tema=votering.get("votering_tema"),
            saksfelt=saksfelt,
            dokumentgruppe=str(sak.get("dokumentgruppe", "")),
            vedtatt=votering.get("vedtatt"),
            alternativ_votering_id=alternativ_votering_id,
            votering_resultat_type=votering.get("votering_resultat_type"),
        )
        .on_conflict_do_update(
            index_elements=["votering_id"],
            set_={
                "tema": votering.get("votering_tema"),
                "vedtatt": votering.get("vedtatt"),
                "alternativ_votering_id": alternativ_votering_id,
                "votering_resultat_type": votering.get("votering_resultat_type"),
            },
        )
    )
    await db.execute(stmt)


async def _upsert_parti_resultater(
    db: AsyncSession,
    votering_id: str,
    parti_agg: dict[str, dict[str, int]],
) -> None:
    for parti, stemmer in parti_agg.items():
        stmt = (
            pg_insert(DbVoteringsresultatParti)
            .values(
                votering_id=votering_id,
                parti=parti,
                for_stemmer=stemmer["for_stemmer"],
                mot_stemmer=stemmer["mot_stemmer"],
                fravarende=stemmer["fravarende"],
            )
            .on_conflict_do_update(
                index_elements=["votering_id", "parti"],
                set_={
                    "for_stemmer": stemmer["for_stemmer"],
                    "mot_stemmer": stemmer["mot_stemmer"],
                    "fravarende": stemmer["fravarende"],
                },
            )
        )
        await db.execute(stmt)


# ── Innhenting per sesjon ─────────────────────────────────────────────────────


async def _hent_eksisterende_ids(db: AsyncSession) -> set[str]:
    rows = await db.execute(text("SELECT votering_id FROM voteringer"))
    return {row[0] for row in rows}


async def kjor_sesjon(
    sesjon: str,
    client: httpx.AsyncClient,
    factory: async_sessionmaker,
) -> None:
    log.info("sesjon_start", sesjon=sesjon)

    # Hent saksliste
    data = await _get(client, f"{BASE_URL}/eksport/saker", {"sesjonid": sesjon, "format": "json"})
    alle_saker = (data or {}).get("saker_liste", [])
    # status=1 betyr ferdigbehandlet i liste-endepunktet
    saker = [s for s in alle_saker if s.get("status") == 1]
    log.info("saker_lastet", sesjon=sesjon, ferdigbehandlet=len(saker), totalt=len(alle_saker))

    # Les eksisterende voteringer fra DB — for å hoppe over på re-run
    async with factory() as db:
        eksisterende = await _hent_eksisterende_ids(db)
    log.info("eksisterende_i_db", antall=len(eksisterende))

    nye_voteringer = 0
    saker_med_votering = 0

    for i, sak in enumerate(saker, 1):
        sak_id = sak["id"]

        if i % 100 == 0:
            log.info(
                "fremdrift",
                sesjon=sesjon,
                sak=i,
                av=len(saker),
                nye_voteringer=nye_voteringer,
            )

        # Hent voteringer for denne saken
        v_data = await _get(
            client, f"{BASE_URL}/eksport/voteringer", {"sakid": str(sak_id), "format": "json"}
        )
        voteringer = (v_data or {}).get("sak_votering_liste", [])
        if not voteringer:
            continue

        saker_med_votering += 1

        for votering in voteringer:
            vid = str(votering["votering_id"])

            if vid in eksisterende:
                # Oppdater bare votering-metadata (nye felt) — hopp over dyrt resultat-kall
                async with factory() as db:
                    await _upsert_votering(db, votering, sak, sesjon)
                    await db.commit()
                continue

            # Hent voteringsresultat (individnivå)
            r_data = await _get(
                client,
                f"{BASE_URL}/eksport/voteringsresultat",
                {"voteringid": vid, "format": "json"},
            )
            resultater = (r_data or {}).get("voteringsresultat_liste", [])
            if not resultater:
                log.warning("tomt_voteringsresultat", votering_id=vid, sak_id=sak_id)
                continue

            parti_agg = _aggreger_per_parti(resultater)

            async with factory() as db:
                await _upsert_votering(db, votering, sak, sesjon)
                await _upsert_parti_resultater(db, vid, parti_agg)
                await db.commit()

            eksisterende.add(vid)
            nye_voteringer += 1

    log.info(
        "sesjon_ferdig",
        sesjon=sesjon,
        saker_behandlet=len(saker),
        saker_med_votering=saker_med_votering,
        nye_voteringer=nye_voteringer,
    )


# ── Main ──────────────────────────────────────────────────────────────────────


async def main(sesjoner: list[str]) -> None:
    settings = Settings()
    if not settings.database_url:
        log.error("DATABASE_URL_mangler", tips="Sett DATABASE_URL i .env")
        sys.exit(1)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            for sesjon in sesjoner:
                await kjor_sesjon(sesjon, client, factory)
    finally:
        await engine.dispose()

    log.info("alt_ferdig", sesjoner=sesjoner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hent voteringer fra Stortingets API og lagre i PostgreSQL"
    )
    parser.add_argument(
        "--sesjoner",
        nargs="+",
        default=ALLE_SESJONER,
        metavar="SESJON",
        help=f"Sesjoner å hente (default: alle). Eksempel: 2023-2024",
    )
    args = parser.parse_args()
    asyncio.run(main(args.sesjoner))
