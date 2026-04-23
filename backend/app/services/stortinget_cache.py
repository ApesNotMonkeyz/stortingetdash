"""
Cachende wrapper rundt StortingetClient.

Strategi:
  hent_sak        — sak:{sak_id}         — permanent for ferdigbehandlede, 24t ellers
  hent_publikasjon — publikasjon:{pub_id} — permanent (dokumenter endrer seg ikke)

Voteringsdata caches IKKE her — de lagres i egne dedikerte tabeller (voteringer, osv.).

Hvis factory er None (ingen DB konfigurert) oppfører klienten seg som den ukachende
StortingetClient.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import Settings
from app.db.models import DbStortingetCache
from app.models.sak import Sak
from app.services.stortinget import StortingetClient

log = structlog.get_logger()

_SAK_TTL_S = 86_400      # 24 timer — saker under behandling
_SESJON_TTL_S = 3_600    # 1 time — saksliste per sesjon (fremtidig bruk)


class CachedStortingetClient:
    """
    Eksponerer samme grensesnitt som StortingetClient, men sjekker databasen
    før hvert API-kall og lagrer resultatet for gjenbruk.

    Injiser via get_stortinget_client() i FastAPI-routes; test-kode kan bruke
    StortingetClient direkte eller sende inn factory=None for å slå av caching.
    """

    def __init__(self, settings: Settings, factory: Any) -> None:
        self._client = StortingetClient(settings)
        self._factory = factory

    async def hent_sak(self, sak_id: str | int) -> Sak:
        sak_id = int(sak_id)
        key = f"sak:{sak_id}"

        raw = await self._hent(key)
        if raw is not None:
            log.info("stortinget_cache_hit", cache_key=key, sak_id=sak_id)
            return Sak.model_validate(raw)

        log.info("stortinget_cache_miss", cache_key=key, sak_id=sak_id)
        sak = await self._client.hent_sak(sak_id)
        ttl = None if sak.ferdigbehandlet else _SAK_TTL_S
        await self._sett(key, sak.model_dump(mode="json"), ttl_seconds=ttl)
        return sak

    async def hent_publikasjon(self, sak: Sak) -> tuple[bytes, Literal["xml", "html"]]:
        from app.exceptions import DokumentUtilgjengelig
        pub = sak.analyse_publikasjon
        if pub is None:
            raise DokumentUtilgjengelig(f"Ingen publikasjoner for sak {sak.id}")

        key = f"publikasjon:{pub.eksport_id}"

        raw = await self._hent(key)
        if raw is not None:
            log.info("stortinget_cache_hit", cache_key=key, sak_id=sak.id)
            return base64.b64decode(raw["data"]), raw["fmt"]

        log.info("stortinget_cache_miss", cache_key=key, sak_id=sak.id)
        content, fmt = await self._client.hent_publikasjon(sak)
        await self._sett(
            key,
            {"data": base64.b64encode(content).decode(), "fmt": fmt},
            ttl_seconds=None,  # permanent — dokumenter endrer seg ikke etter publisering
        )
        return content, fmt

    # ── DB-operasjoner ────────────────────────────────────────────────────────

    async def _hent(self, key: str) -> dict | None:
        if self._factory is None:
            return None
        async with self._factory() as session:
            result = await session.execute(
                select(DbStortingetCache)
                .where(DbStortingetCache.cache_key == key)
                .where(
                    or_(
                        DbStortingetCache.utloper.is_(None),
                        DbStortingetCache.utloper > func.now(),
                    )
                )
            )
            row = result.scalar_one_or_none()
            return row.data_json if row is not None else None

    async def _sett(self, key: str, data: dict, *, ttl_seconds: int | None) -> None:
        if self._factory is None:
            return
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        utloper: datetime | None = None
        if ttl_seconds is not None:
            utloper = (
                datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds)
            ).replace(tzinfo=None)

        async with self._factory() as session:
            stmt = (
                pg_insert(DbStortingetCache)
                .values(cache_key=key, data_json=data, opprettet=now, utloper=utloper)
                .on_conflict_do_update(
                    index_elements=["cache_key"],
                    set_={"data_json": data, "utloper": utloper},
                )
            )
            await session.execute(stmt)
            await session.commit()


def get_stortinget_client(settings: Settings) -> CachedStortingetClient:
    """
    FastAPI-dependency — returnerer en cachende klient med aktiv DB-factory.
    Test-kode kan injisere StortingetClient(settings) direkte for å hoppe over caching.
    """
    from app.db.session import get_session_factory
    return CachedStortingetClient(settings, get_session_factory())
