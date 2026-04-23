"""
Integrasjonstest mot ekte Stortinget API.

Kjøres med: pytest tests/test_stortinget.py -v
Krever nettverkstilgang. Ingen mock — poenget er å verifisere at
klient og modell fungerer mot faktiske API-responser.
"""
from __future__ import annotations

import pytest

from app.config import Settings
from app.exceptions import SakIkkeFunnet
from app.models.sak import Sak
from app.services.stortinget import StortingetClient


@pytest.fixture
def settings() -> Settings:
    # anthropic_api_key er ikke relevant for dette steget,
    # men Settings krever feltet — gir en dummy-verdi.
    return Settings(anthropic_api_key="test-only")


@pytest.fixture
def client(settings: Settings) -> StortingetClient:
    return StortingetClient(settings)


class TestHentSak:
    """Tester mot sak 47163: Dok 8 om transportetat (KrF, 2009-2010)."""

    async def test_returnerer_sak_objekt(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert isinstance(sak, Sak)

    async def test_korrekt_id(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.id == 47163

    async def test_er_representantforslag(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.dokumentgruppe == 4
        assert sak.er_representantforslag is True

    async def test_ferdigbehandlet(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.ferdigbehandlet is True

    async def test_korrekt_sesjon(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.sak_sesjon == "2009-2010"

    async def test_tittel_inneholder_transportetat(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.korttittel is not None
        assert "transportetat" in sak.korttittel.lower()

    async def test_norske_tegn_dekodes_korrekt(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.korttittel is not None
        # Ingen U+FFFD — bekrefer at UTF-8-dekodingen gikk rett
        assert "\ufffd" not in sak.korttittel
        # chr(229) = U+00E5 = "å"
        assert chr(229) in sak.korttittel
        # chr(248) = U+00F8 = "ø" — via fornavn "Geir Jørgen"
        assert sak.sak_opphav is not None
        bekkevold = next(f for f in sak.sak_opphav.forslagstiller_liste if f.etternavn == "Bekkevold")
        assert chr(248) in bekkevold.fornavn

    async def test_komite_er_transport(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.komite is not None
        assert sak.komite.id == "TRANSKOM"
        assert "Transport" in sak.komite.navn

    async def test_fem_forslagstillere(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.sak_opphav is not None
        assert len(sak.sak_opphav.forslagstiller_liste) == 5

    async def test_forslagstillere_er_krf(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert sak.sak_opphav is not None
        parti_ider = {f.parti.id for f in sak.sak_opphav.forslagstiller_liste}
        assert parti_ider == {"KrF"}

    async def test_stikkord_inneholder_transportetat(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert "Transportetat" in sak.stikkord_liste

    async def test_publikasjoner_finnes(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert len(sak.publikasjon_referanse_liste) >= 2

    async def test_primær_publikasjon_er_dok8(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        pub = sak.primær_publikasjon
        assert pub is not None
        assert "Dokument 8" in pub.lenke_tekst
        assert pub.full_url.startswith("https://")

    async def test_har_saksordfoerer(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        assert len(sak.saksordfoerer_liste) >= 1

    async def test_emner_inneholder_samferdsel(self, client: StortingetClient) -> None:
        sak = await client.hent_sak(47163)
        emnenavn = [e.navn for e in sak.emne_liste]
        assert any("Samferdsel" in navn for navn in emnenavn)

    async def test_sak_ikke_funnet_reiser_exception(self, client: StortingetClient) -> None:
        with pytest.raises(SakIkkeFunnet):
            await client.hent_sak(999999999)
