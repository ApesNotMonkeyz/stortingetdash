"""
Tester for CachedStortingetClient.

Bruker AsyncMock for å isolere fra DB og Stortinget API.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.sak import Sak
from app.services.stortinget_cache import CachedStortingetClient, _SAK_TTL_S


# ── Hjelpere ──────────────────────────────────────────────────────────────────


def _minimal_sak(*, id: int = 200066, ferdigbehandlet: bool = True) -> Sak:
    return Sak.model_validate(
        {
            "id": id,
            "tittel": "Test sak",
            "dokumentgruppe": 4,
            "type": 1,
            "status": 1,
            "ferdigbehandlet": ferdigbehandlet,
        }
    )


def _sak_med_publikasjon(*, ferdigbehandlet: bool = True) -> Sak:
    return Sak.model_validate(
        {
            "id": 200066,
            "tittel": "Test sak",
            "dokumentgruppe": 4,
            "type": 1,
            "status": 1,
            "ferdigbehandlet": ferdigbehandlet,
            "publikasjon_referanse_liste": [
                {
                    "eksport_id": "inns-test-123",
                    "lenke_tekst": "Innst. 1 S (2024-2025)",
                    "lenke_url": "//stortinget.no/test",
                    "type": 6,
                }
            ],
        }
    )


def _lag_klient() -> CachedStortingetClient:
    settings = MagicMock()
    return CachedStortingetClient(settings, factory=None)


# ── hent_sak: cache-treff ─────────────────────────────────────────────────────


class TestHentSakCacheTreff:
    @pytest.mark.asyncio
    async def test_ingen_api_kall_ved_treff(self):
        """Cache-treff skal returnere Sak uten å kalle StortingetClient."""
        sak = _minimal_sak()
        client = _lag_klient()
        client._hent = AsyncMock(return_value=sak.model_dump(mode="json"))
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock()

        result = await client.hent_sak(200066)

        assert result.id == 200066
        client._client.hent_sak.assert_not_called()
        client._sett.assert_not_called()

    @pytest.mark.asyncio
    async def test_riktig_cache_nokkel(self):
        """_hent kalles med cache-nøkkel 'sak:{sak_id}'."""
        sak = _minimal_sak(id=200040)
        client = _lag_klient()
        client._hent = AsyncMock(return_value=sak.model_dump(mode="json"))
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock()

        await client.hent_sak(200040)

        client._hent.assert_called_once_with("sak:200040")


# ── hent_sak: cache-miss ──────────────────────────────────────────────────────


class TestHentSakCacheMiss:
    @pytest.mark.asyncio
    async def test_api_kalles_og_resultat_lagres(self):
        """Cache-miss: API kalles og resultatet skrives til cache."""
        sak = _minimal_sak()
        client = _lag_klient()
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock(return_value=sak)

        result = await client.hent_sak(200066)

        assert result.id == 200066
        client._client.hent_sak.assert_called_once()
        client._sett.assert_called_once()

    @pytest.mark.asyncio
    async def test_ferdigbehandlet_lagres_permanent(self):
        """Ferdigbehandlede saker skal caches permanent (ttl_seconds=None)."""
        sak = _minimal_sak(ferdigbehandlet=True)
        client = _lag_klient()
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock(return_value=sak)

        await client.hent_sak(200066)

        _, kwargs = client._sett.call_args
        assert kwargs["ttl_seconds"] is None

    @pytest.mark.asyncio
    async def test_paagarende_sak_lagres_med_ttl(self):
        """Saker under behandling caches med 24 timers TTL."""
        sak = _minimal_sak(ferdigbehandlet=False)
        client = _lag_klient()
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock(return_value=sak)

        await client.hent_sak(200066)

        _, kwargs = client._sett.call_args
        assert kwargs["ttl_seconds"] == _SAK_TTL_S


# ── hent_sak: utløpt cache ────────────────────────────────────────────────────


class TestHentSakTtlUtlopt:
    @pytest.mark.asyncio
    async def test_utlopt_entry_gir_nytt_api_kall(self):
        """
        Simulerer en utløpt cache ved at _hent returnerer None (DB-laget filtrerer
        allerede bort utløpte entries med WHERE utloper > now()).
        Verifiserer at API kalles og nytt resultat lagres.
        """
        sak = _minimal_sak(ferdigbehandlet=False)
        client = _lag_klient()
        # _hent returnerer None — som om entry var utløpt og silt bort av DB
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_sak = AsyncMock(return_value=sak)

        result = await client.hent_sak(200066)

        assert result.id == 200066
        client._client.hent_sak.assert_called_once()
        client._sett.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_memory_ttl_semantikk(self):
        """
        Etterligner TTL-logikken i minnet: cache returnerer None for utløpt entry,
        noe som trigger nytt API-kall på andre kjøring.
        """
        sak = _minimal_sak(ferdigbehandlet=False)
        store: dict[str, dict] = {}

        async def hent(key: str) -> dict | None:
            row = store.get(key)
            if row is None:
                return None
            utloper = row.get("utloper")
            if utloper is not None and utloper < datetime.utcnow():
                return None
            return row["data"]

        async def sett(key: str, data: dict, *, ttl_seconds: int | None) -> None:
            utloper = None
            if ttl_seconds is not None:
                utloper = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            store[key] = {"data": data, "utloper": utloper}

        # Lagre allerede-utløpt entry
        store["sak:200066"] = {
            "data": sak.model_dump(mode="json"),
            "utloper": datetime.utcnow() - timedelta(seconds=1),
        }

        client = _lag_klient()
        client._hent = hent  # type: ignore[assignment]
        client._sett = sett  # type: ignore[assignment]
        client._client.hent_sak = AsyncMock(return_value=sak)

        result = await client.hent_sak(200066)

        assert result.id == 200066
        client._client.hent_sak.assert_called_once()


# ── hent_publikasjon ──────────────────────────────────────────────────────────


class TestHentPublikasjon:
    @pytest.mark.asyncio
    async def test_cache_treff_returnerer_bytes(self):
        """Cache-treff for publikasjon returnerer bytes uten API-kall."""
        sak = _sak_med_publikasjon()
        xml = b"<root><test/></root>"
        cached_data = {"data": base64.b64encode(xml).decode(), "fmt": "xml"}

        client = _lag_klient()
        client._hent = AsyncMock(return_value=cached_data)
        client._sett = AsyncMock()
        client._client.hent_publikasjon = AsyncMock()

        content, fmt = await client.hent_publikasjon(sak)

        assert content == xml
        assert fmt == "xml"
        client._client.hent_publikasjon.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_lagres_permanent(self):
        """Publikasjoner lagres alltid permanent (endrer seg ikke etter publisering)."""
        sak = _sak_med_publikasjon()
        xml = b"<root/>"

        client = _lag_klient()
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_publikasjon = AsyncMock(return_value=(xml, "xml"))

        await client.hent_publikasjon(sak)

        _, kwargs = client._sett.call_args
        assert kwargs["ttl_seconds"] is None

    @pytest.mark.asyncio
    async def test_riktig_cache_nokkel_for_publikasjon(self):
        """Cache-nøkkel for publikasjon er 'publikasjon:{eksport_id}'."""
        sak = _sak_med_publikasjon()
        client = _lag_klient()
        client._hent = AsyncMock(return_value=None)
        client._sett = AsyncMock()
        client._client.hent_publikasjon = AsyncMock(return_value=(b"<r/>", "xml"))

        await client.hent_publikasjon(sak)

        client._hent.assert_called_once_with("publikasjon:inns-test-123")


# ── Voteringsdata ikke i stortinget_cache ─────────────────────────────────────


class TestVoteringsdataIkkeDuplisert:
    def test_klienten_har_ingen_voteringsmetoder(self):
        """
        CachedStortingetClient skal ikke ha metoder for voteringsdata.
        Voteringer lagres i dedikerte tabeller (voteringer, voteringsresultat_parti).
        """
        public_methods = {
            m for m in dir(CachedStortingetClient) if not m.startswith("_")
        }
        assert "hent_voteringer" not in public_methods
        assert "hent_voteringsresultat" not in public_methods
        assert "lagre_votering" not in public_methods

    def test_offentlig_grensesnitt_matcher_stortinget_client(self):
        """CachedStortingetClient eksponerer samme metoder som StortingetClient."""
        from app.services.stortinget import StortingetClient

        cached_public = {m for m in dir(CachedStortingetClient) if not m.startswith("_")}
        original_public = {m for m in dir(StortingetClient) if not m.startswith("_")}
        # Alle StortingetClient-metoder finnes i den cachende versjonen
        assert original_public.issubset(cached_public)


# ── Ingen DB: klienten virker uten factory ────────────────────────────────────


class TestIngenFactory:
    @pytest.mark.asyncio
    async def test_factory_none_kaller_api_direkte(self):
        """Uten factory (factory=None) fungerer klienten som ikke-cachende StortingetClient."""
        sak = _minimal_sak()
        client = CachedStortingetClient(MagicMock(), factory=None)
        client._client.hent_sak = AsyncMock(return_value=sak)

        result = await client.hent_sak(200066)

        assert result.id == 200066
        client._client.hent_sak.assert_called_once()
