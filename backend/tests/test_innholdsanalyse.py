"""
Integrasjonstester for steg 5: innholdsanalyse.

Kjøres med: pytest tests/test_innholdsanalyse.py -v -m integration
Hoppes over i CI med: pytest -m "not integration"
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.models.analyse import Innholdsanalyse
from app.services.claude import ClaudeClient
from app.services.xml_parser import parse_dokument
from app.steps.innholdsanalyse import analyser_innhold

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "spike"


# ── Fixtures (session-scoped → ett API-kall per fixture) ──────────────────────


@pytest.fixture(scope="session")
def claude() -> ClaudeClient:
    return ClaudeClient(get_settings())


@pytest.fixture(scope="session")
async def innholdsanalyse_innstilling(claude: ClaudeClient) -> Innholdsanalyse:
    xml = (FIXTURES / "ny_innstilling_inns-202425-176s.xml").read_bytes()
    dok = parse_dokument(xml, pub_id="inns-202425-176s")
    return await analyser_innhold(dok, claude)


@pytest.fixture(scope="session")
async def innholdsanalyse_dok8(claude: ClaudeClient) -> Innholdsanalyse:
    xml = (FIXTURES / "ny_dok8_dok8-202324-173s.xml").read_bytes()
    dok = parse_dokument(xml, pub_id="dok8-202324-173s")
    return await analyser_innhold(dok, claude)


# ── Ny innstilling ────────────────────────────────────────────────────────────


class TestInnholdsanalyseNyInnstilling:
    def test_problemforstaelse_er_satt(self, innholdsanalyse_innstilling: Innholdsanalyse) -> None:
        assert innholdsanalyse_innstilling.problemforstaelse
        assert len(innholdsanalyse_innstilling.problemforstaelse) > 20

    def test_losningsforslag_er_satt(self, innholdsanalyse_innstilling: Innholdsanalyse) -> None:
        assert innholdsanalyse_innstilling.losningsforslag
        assert len(innholdsanalyse_innstilling.losningsforslag) > 20

    def test_argumentasjonslinjer_er_liste(self, innholdsanalyse_innstilling: Innholdsanalyse) -> None:
        assert isinstance(innholdsanalyse_innstilling.argumentasjonslinjer, list)
        assert len(innholdsanalyse_innstilling.argumentasjonslinjer) >= 1

    def test_argumentasjonslinjer_er_ikke_tomme(self, innholdsanalyse_innstilling: Innholdsanalyse) -> None:
        for linje in innholdsanalyse_innstilling.argumentasjonslinjer:
            assert isinstance(linje, str)
            assert len(linje) > 10

    def test_produktivitet_nevnes(self, innholdsanalyse_innstilling: Innholdsanalyse) -> None:
        all_tekst = " ".join([
            innholdsanalyse_innstilling.problemforstaelse,
            innholdsanalyse_innstilling.losningsforslag,
            *innholdsanalyse_innstilling.argumentasjonslinjer,
        ]).lower()
        assert "produktivitet" in all_tekst or "kommisjon" in all_tekst


# ── Ny Dok 8 ─────────────────────────────────────────────────────────────────


class TestInnholdsanalyseNyDok8:
    def test_problemforstaelse_er_satt(self, innholdsanalyse_dok8: Innholdsanalyse) -> None:
        assert innholdsanalyse_dok8.problemforstaelse
        assert len(innholdsanalyse_dok8.problemforstaelse) > 20

    def test_losningsforslag_er_satt(self, innholdsanalyse_dok8: Innholdsanalyse) -> None:
        assert innholdsanalyse_dok8.losningsforslag
        assert len(innholdsanalyse_dok8.losningsforslag) > 20

    def test_argumentasjonslinjer_er_ikke_tom(self, innholdsanalyse_dok8: Innholdsanalyse) -> None:
        assert len(innholdsanalyse_dok8.argumentasjonslinjer) >= 1

    def test_produktivitet_nevnes(self, innholdsanalyse_dok8: Innholdsanalyse) -> None:
        all_tekst = " ".join([
            innholdsanalyse_dok8.problemforstaelse,
            innholdsanalyse_dok8.losningsforslag,
            *innholdsanalyse_dok8.argumentasjonslinjer,
        ]).lower()
        assert "produktivitet" in all_tekst or "kommisjon" in all_tekst
