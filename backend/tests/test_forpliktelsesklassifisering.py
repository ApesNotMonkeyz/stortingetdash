"""
Integrasjonstester for steg 4: forpliktelsesklassifisering.

Kaller Claude API — krever ANTHROPIC_API_KEY i .env.
Kjøres med: pytest tests/test_forpliktelsesklassifisering.py -v -m integration
Hoppes over i CI med: pytest -m "not integration"
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.models.dokument import Forslagspunkt, Forpliktelsesgrad
from app.services.claude import ClaudeClient
from app.services.xml_parser import parse_dokument
from app.steps.forpliktelsesklassifisering import klassifiser_forpliktelsesgrad

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "spike"

_GYLDIGE_GRADER = {g.value for g in Forpliktelsesgrad}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def claude() -> ClaudeClient:
    return ClaudeClient(get_settings())


@pytest.fixture(scope="session")
def innstilling_forslag() -> list[Forslagspunkt]:
    xml = (FIXTURES / "ny_innstilling_inns-202425-176s.xml").read_bytes()
    return parse_dokument(xml, pub_id="inns-202425-176s").mindretallsforslag


@pytest.fixture(scope="session")
def dok8_som_liste() -> list[Forslagspunkt]:
    """Dok 8 har ingen mindretallsforslag — bruker vedtaksteksten som testtilfelle."""
    xml = (FIXTURES / "ny_dok8_dok8-202324-173s.xml").read_bytes()
    dok = parse_dokument(xml, pub_id="dok8-202324-173s")
    if not dok.vedtakstekst:
        return []
    return [Forslagspunkt(nr="1", tekst=dok.vedtakstekst)]


# ── Ny innstilling (1 mindretallsforslag fra H, FrP, V, KrF) ─────────────────


class TestNyInnstillingKlassifisering:
    async def test_returnerer_riktig_antall(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        assert len(resultat) == len(innstilling_forslag)

    async def test_forpliktelsesgrad_er_satt(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        for punkt in resultat:
            assert punkt.forpliktelsesgrad is not None

    async def test_forpliktelsesgrad_er_gyldig_enum(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        for punkt in resultat:
            assert punkt.forpliktelsesgrad is not None
            assert punkt.forpliktelsesgrad.value in _GYLDIGE_GRADER

    async def test_begrunnelse_er_satt(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        for punkt in resultat:
            assert punkt.begrunnelse_klassifisering is not None
            assert len(punkt.begrunnelse_klassifisering) > 10

    async def test_begrunnelse_nevner_verb(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        kjente_verb = {
            "utrede", "vurdere", "legge frem", "komme tilbake",
            "sikre", "sørge for", "gjennomføre", "innføre",
            "opprette", "etablere", "legge", "fram", "frem",
        }
        for punkt in resultat:
            begrunnelse = (punkt.begrunnelse_klassifisering or "").lower()
            assert any(v in begrunnelse for v in kjente_verb), (
                f"Begrunnelse nevner ikke noe kjent verb: {begrunnelse!r}"
            )

    async def test_nr_bevart_i_output(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        input_nre = [p.nr for p in innstilling_forslag]
        output_nre = [p.nr for p in resultat]
        assert input_nre == output_nre

    async def test_fraksjon_bevart_i_output(
        self, innstilling_forslag: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        resultat = await klassifiser_forpliktelsesgrad(innstilling_forslag, claude)
        for inn, ut in zip(innstilling_forslag, resultat):
            assert inn.fra == ut.fra


# ── Ny Dok 8 (vedtakstekst som enkelt punkt) ─────────────────────────────────


class TestNyDok8Klassifisering:
    async def test_klassifiserer_vedtakspunkt(
        self, dok8_som_liste: list[Forslagspunkt], claude: ClaudeClient
    ) -> None:
        if not dok8_som_liste:
            pytest.skip("Ingen vedtakstekst i fixture")
        resultat = await klassifiser_forpliktelsesgrad(dok8_som_liste, claude)
        assert len(resultat) == 1
        assert resultat[0].forpliktelsesgrad is not None
        assert resultat[0].forpliktelsesgrad.value in _GYLDIGE_GRADER

    async def test_tom_liste_returneres_urort(self, claude: ClaudeClient) -> None:
        resultat = await klassifiser_forpliktelsesgrad([], claude)
        assert resultat == []
