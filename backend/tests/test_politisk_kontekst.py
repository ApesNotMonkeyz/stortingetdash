"""
Integrasjonstester for steg 6: politisk kontekst.

Kjøres med: pytest tests/test_politisk_kontekst.py -v -m integration
Hoppes over i CI med: pytest -m "not integration"
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.models.analyse import KoblingType, PolitiskKontekst, Sikkerhetsnivaa
from app.models.dokument import Forslagspunkt
from app.services.claude import ClaudeClient
from app.services.xml_parser import parse_dokument
from app.steps.politisk_kontekst import analyser_politisk_kontekst

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "spike"

_GYLDIGE_SIKKERHET = {n.value for n in Sikkerhetsnivaa}
_GYLDIGE_KOBLING = {k.value for k in KoblingType}


# ── Fixtures (session-scoped → ett API-kall per fixture) ──────────────────────


@pytest.fixture(scope="session")
def claude() -> ClaudeClient:
    return ClaudeClient(get_settings())


@pytest.fixture(scope="session")
async def kontekst_innstilling(claude: ClaudeClient) -> PolitiskKontekst:
    xml = (FIXTURES / "ny_innstilling_inns-202425-176s.xml").read_bytes()
    dok = parse_dokument(xml, pub_id="inns-202425-176s")
    return await analyser_politisk_kontekst(dok, dok.mindretallsforslag, claude)


@pytest.fixture(scope="session")
async def kontekst_dok8(claude: ClaudeClient) -> PolitiskKontekst:
    xml = (FIXTURES / "ny_dok8_dok8-202324-173s.xml").read_bytes()
    dok = parse_dokument(xml, pub_id="dok8-202324-173s")
    vedtakspunkt = (
        [Forslagspunkt(nr="1", tekst=dok.vedtakstekst)]
        if dok.vedtakstekst
        else []
    )
    return await analyser_politisk_kontekst(dok, vedtakspunkt, claude)


# ── Ny innstilling ────────────────────────────────────────────────────────────


class TestPolitiskKontekstNyInnstilling:
    def test_returnerer_politisk_kontekst(self, kontekst_innstilling: PolitiskKontekst) -> None:
        assert isinstance(kontekst_innstilling, PolitiskKontekst)

    def test_har_minst_en_dimensjon(self, kontekst_innstilling: PolitiskKontekst) -> None:
        assert len(kontekst_innstilling.politiske_dimensjoner) >= 1

    def test_dimensjoner_har_akse(self, kontekst_innstilling: PolitiskKontekst) -> None:
        for d in kontekst_innstilling.politiske_dimensjoner:
            assert d.akse and len(d.akse) > 2

    def test_dimensjoner_har_plassering(self, kontekst_innstilling: PolitiskKontekst) -> None:
        for d in kontekst_innstilling.politiske_dimensjoner:
            assert d.plassering and len(d.plassering) > 2

    def test_dimensjoner_sikkerhet_er_gyldig(self, kontekst_innstilling: PolitiskKontekst) -> None:
        for d in kontekst_innstilling.politiske_dimensjoner:
            assert d.sikkerhet.value in _GYLDIGE_SIKKERHET

    def test_dimensjoner_har_begrunnelse(self, kontekst_innstilling: PolitiskKontekst) -> None:
        for d in kontekst_innstilling.politiske_dimensjoner:
            assert d.begrunnelse and len(d.begrunnelse) > 10

    def test_kobling_er_satt(self, kontekst_innstilling: PolitiskKontekst) -> None:
        assert kontekst_innstilling.kobling_eksisterende_politikk is not None

    def test_kobling_type_er_gyldig(self, kontekst_innstilling: PolitiskKontekst) -> None:
        kobling = kontekst_innstilling.kobling_eksisterende_politikk
        assert kobling is not None
        assert kobling.type.value in _GYLDIGE_KOBLING

    def test_kobling_sikkerhet_er_gyldig(self, kontekst_innstilling: PolitiskKontekst) -> None:
        kobling = kontekst_innstilling.kobling_eksisterende_politikk
        assert kobling is not None
        assert kobling.sikkerhet.value in _GYLDIGE_SIKKERHET

    def test_kobling_har_begrunnelse(self, kontekst_innstilling: PolitiskKontekst) -> None:
        kobling = kontekst_innstilling.kobling_eksisterende_politikk
        assert kobling is not None
        assert kobling.begrunnelse and len(kobling.begrunnelse) > 10


# ── Ny Dok 8 ─────────────────────────────────────────────────────────────────


class TestPolitiskKontekstNyDok8:
    def test_returnerer_politisk_kontekst(self, kontekst_dok8: PolitiskKontekst) -> None:
        assert isinstance(kontekst_dok8, PolitiskKontekst)

    def test_har_minst_en_dimensjon(self, kontekst_dok8: PolitiskKontekst) -> None:
        assert len(kontekst_dok8.politiske_dimensjoner) >= 1

    def test_alle_sikkerhetsnivaaer_gyldige(self, kontekst_dok8: PolitiskKontekst) -> None:
        for d in kontekst_dok8.politiske_dimensjoner:
            assert d.sikkerhet.value in _GYLDIGE_SIKKERHET

    def test_kobling_type_er_gyldig(self, kontekst_dok8: PolitiskKontekst) -> None:
        kobling = kontekst_dok8.kobling_eksisterende_politikk
        if kobling is not None:
            assert kobling.type.value in _GYLDIGE_KOBLING
