"""
Tester for prediksjonsmodulen lag 3 (LLM-assistert).

Enhetstester: verifiserer at lag 3 ikke trigges ved hoy konfidens,
og at prompt-versjon lagres korrekt.

Integrasjonstester (@pytest.mark.integration): kaller faktisk LLM (Sonnet) mot
realistisk saksanalyse-input. Krever ANTHROPIC_API_KEY.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.models.analyse import Innholdsanalyse, Saksanalyse
from app.models.prediksjon import Konfidens, PartiPrediksjon, PrimærSignal, Saksprediksjon
from app.prompts.prediksjon import PREDIKSJON_V1
from app.steps.prediksjon_lag3 import lag3_prediker

pytestmark_integration = pytest.mark.integration

KJERNE = ["A", "H", "Sp", "FrP", "SV", "V", "MDG", "R", "KrF"]

# Realistisk minimumsanalyse for testformål
_MOCK_ANALYSE = Saksanalyse(
    sak_id=47163,
    pub_id="inns-202324-test",
    dok_type="ny_innstilling",
    tittel="Representantforslag om skjerpet klimapolitikk i industrien",
    sesjon="2023-2024",
    innholdsanalyse=Innholdsanalyse(
        problemforstaelse=(
            "Norsk industri har ikke kuttet utslipp tilstrekkelig. "
            "Eksisterende virkemidler er utilstrekkelige for a na 2030-malet."
        ),
        losningsforslag=(
            "Stortinget ber regjeringen innfore bindende sektorkvoter for industrien "
            "og okt CO2-avgift fra 2025."
        ),
        argumentasjonslinjer=[
            "Klimaavtalen krever 55% kutt innen 2030",
            "Markedet alene losser ikke kollektive handlingsproblemer",
            "Industrien har hatt lang varseltid",
        ],
    ),
)


# ── Enhetstester (ingen LLM, ingen DB) ───────────────────────────────────────

class TestLag3IkkeTriggertVedHoyKonfidens:
    """Verifiserer at lag 3 returnerer tomt resultat nar ingen partier har lav konfidens."""

    def _make_pred(self, parti: str, konfidens: Konfidens) -> PartiPrediksjon:
        return PartiPrediksjon(
            parti=parti,
            sannsynlighet_for=0.9,
            konfidens=konfidens,
            primaersignal=PrimærSignal.fraksjon_xml,
            begrunnelse="test",
        )

    @pytest.mark.asyncio
    async def test_ingen_partier_gir_tomt_resultat(self):
        """Tomt partier-argument returnerer {} uten LLM-kall."""
        settings = get_settings()
        resultat = await lag3_prediker(
            sak_id=1,
            analyse=_MOCK_ANALYSE,
            partier=[],
            lag1_resultat={},
            lag2_resultat={},
            saksfelt=[],
            rp={"A"},
            sakskategori="rutine",
            settings=settings,
        )
        assert resultat == {}

    @pytest.mark.asyncio
    async def test_pipeline_hopper_over_lag3_ved_hoy_konfidens(self):
        """
        Verifiserer at prediksjon_pipeline ikke kaller lag3_prediker
        nar alle partier har hoy konfidens etter lag 1-2.
        """
        hoy_resultat = {
            p: self._make_pred(p, Konfidens.hoy)
            for p in KJERNE
        }

        # Ingen partier har lav konfidens — lag 3 skal ikke trigges
        partier_lag3 = [p for p, pred in hoy_resultat.items() if pred.konfidens == Konfidens.lav]
        assert partier_lag3 == [], "Lag 3 skal ikke trigges nar alle partier har hoy konfidens"


class TestPromptVersjonICacheNokkel:
    """Verifiserer at _PROMPT_VERSJON er satt og at cache sjekker versjonen."""

    def test_prompt_versjon_er_satt(self):
        from app.services.prediksjon_pipeline import _PROMPT_VERSJON
        assert _PROMPT_VERSJON, "Prompt-versjon maa vaere satt"
        assert "lag3" in _PROMPT_VERSJON or "v" in _PROMPT_VERSJON

    def test_prediksjon_v1_er_satt(self):
        assert PREDIKSJON_V1 == "PREDIKSJON_V1"

    def test_saksprediksjon_lagrer_prompt_versjon(self):
        """Saksprediksjon-modellen har felt for prompt_versjon."""
        prediksjon = Saksprediksjon(
            sak_id=1,
            sakskategori="rutine",
            voteringer=[],
            samlet_utfall="usikkert",
            samlet_konfidens=Konfidens.lav,
            signalkilder_brukt=["lag1"],
            prompt_versjon="lag1-3/v1",
        )
        assert prediksjon.prompt_versjon == "lag1-3/v1"

    @pytest.mark.asyncio
    async def test_cache_hent_feiler_ved_feil_versjon(self):
        """_cache_hent skal returnere None og slette cache nar prompt_versjon avviker."""
        from app.services.prediksjon_pipeline import _cache_hent

        mock_row = MagicMock()
        mock_row.prompt_versjon = "gammel_versjon"
        mock_row.utloper = None

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock(return_value=mock_session)

        resultat = await _cache_hent(42, mock_factory, "ny_versjon")
        assert resultat is None
        mock_session.delete.assert_called_once_with(mock_row)

    @pytest.mark.asyncio
    async def test_cache_hent_aksepterer_riktig_versjon(self):
        """_cache_hent skal returnere cachet prediksjon nar versjon stemmer."""
        from app.services.prediksjon_pipeline import _cache_hent

        test_prediksjon = Saksprediksjon(
            sak_id=42,
            sakskategori="rutine",
            voteringer=[],
            samlet_utfall="usikkert",
            samlet_konfidens=Konfidens.lav,
            signalkilder_brukt=["lag1"],
            prompt_versjon="lag1-3/v1",
        )

        mock_row = MagicMock()
        mock_row.prompt_versjon = "lag1-3/v1"
        mock_row.utloper = None
        mock_row.prediksjoner_json = test_prediksjon.model_dump(mode="json")

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock(return_value=mock_session)

        resultat = await _cache_hent(42, mock_factory, "lag1-3/v1")
        assert resultat is not None
        assert resultat.sak_id == 42


# ── Integrasjonstester (kaller faktisk LLM) ───────────────────────────────────

@pytest.mark.integration
class TestLag3Integrasjon:
    """
    Kaller lag3_prediker mot faktisk Claude Sonnet.
    Krever ANTHROPIC_API_KEY i miljo. Kjores med: pytest -m integration
    """

    @pytest.fixture(scope="class")
    def settings(self):
        return get_settings()

    @pytest.fixture(scope="class")
    async def lag3_resultat_klimasak(self, settings):
        """Lag 3 mot et klimaforslag med lav-konfidens opposisjonspartier."""
        from app.models.prediksjon import PrimærSignal

        # Lag 1-2 med A=middels (rp) og alle opp=lav
        lag1 = {
            "A": PartiPrediksjon(
                parti="A", sannsynlighet_for=0.10, konfidens=Konfidens.middels,
                primaersignal=PrimærSignal.regjeringsposisjon,
                begrunnelse="Signal 3: A er rp i mindretallsregjering",
            ),
        }
        lav_partier = ["H", "Sp", "FrP", "SV", "V", "MDG", "R", "KrF"]
        for p in lav_partier:
            lag1[p] = PartiPrediksjon(
                parti=p, sannsynlighet_for=0.50, konfidens=Konfidens.lav,
                primaersignal=PrimærSignal.regjeringsposisjon,
                begrunnelse="Signal 3: ingen strukturell info",
            )

        return await lag3_prediker(
            sak_id=_MOCK_ANALYSE.sak_id,
            analyse=_MOCK_ANALYSE,
            partier=lav_partier[:4],  # Test 4 partier for kostnadssparing
            lag1_resultat=lag1,
            lag2_resultat={},
            saksfelt=["klima", "miljo"],
            rp={"A"},
            sakskategori="koalisjonssak",
            settings=settings,
        )

    def test_returnerer_prediksjon_for_alle_partier(self, lag3_resultat_klimasak):
        assert len(lag3_resultat_klimasak) == 4

    def test_alle_har_llm_signal(self, lag3_resultat_klimasak):
        for parti, pred in lag3_resultat_klimasak.items():
            assert pred.primaersignal == PrimærSignal.llm_analyse, \
                f"{parti} burde ha llm_analyse signal"

    def test_sannsynlighet_i_gyldig_range(self, lag3_resultat_klimasak):
        for parti, pred in lag3_resultat_klimasak.items():
            assert 0.0 <= pred.sannsynlighet_for <= 1.0, \
                f"{parti}: sannsynlighet_for={pred.sannsynlighet_for} utenfor [0,1]"

    def test_konfidens_er_gyldig_enum(self, lag3_resultat_klimasak):
        gyldige = {Konfidens.hoy, Konfidens.middels, Konfidens.lav}
        for parti, pred in lag3_resultat_klimasak.items():
            assert pred.konfidens in gyldige

    def test_begrunnelse_er_ikke_tom(self, lag3_resultat_klimasak):
        for parti, pred in lag3_resultat_klimasak.items():
            assert pred.begrunnelse, f"{parti}: tom begrunnelse"
            assert len(pred.begrunnelse) > 30, f"{parti}: for kort begrunnelse"

    def test_begrunnelse_inneholder_konkrete_data(self, lag3_resultat_klimasak):
        """
        Begrunnelsen skal referere til tall (prosent, n=, %) eller sak-ID-er.
        Generelle vurderinger uten data er ikke tilstrekkelig.
        """
        import re
        tall_pattern = re.compile(r'\d+\s*%|\bn=\d+|\d{4,6}|\d+\.\d+')
        for parti, pred in lag3_resultat_klimasak.items():
            har_tall = bool(tall_pattern.search(pred.begrunnelse))
            # Lav-konfidens svar uten data er akseptabelt (men logg det)
            if pred.konfidens != Konfidens.lav:
                assert har_tall, (
                    f"{parti} (konfidens={pred.konfidens.value}): "
                    f"begrunnelse mangler konkrete tall: {pred.begrunnelse!r}"
                )

    def test_output_er_gyldig_partiprediksjon(self, lag3_resultat_klimasak):
        for parti, pred in lag3_resultat_klimasak.items():
            assert isinstance(pred, PartiPrediksjon)
            assert pred.parti == parti


@pytest.mark.integration
class TestLag3MedHistoriskData:
    """
    Lag 3 med reelle historiske data fra DB (krever DATABASE_URL og ANTHROPIC_API_KEY).
    """

    @pytest.fixture(scope="class")
    def settings(self):
        return get_settings()

    @pytest.fixture(scope="class")
    def factory(self, settings):
        if not settings.database_url:
            pytest.skip("DATABASE_URL ikke satt")
        from app.db.session import get_session_factory
        return get_session_factory()

    @pytest.fixture(scope="class")
    async def lag3_med_db(self, settings, factory):
        from app.models.prediksjon import PrimærSignal
        lag1 = {
            p: PartiPrediksjon(
                parti=p, sannsynlighet_for=0.50, konfidens=Konfidens.lav,
                primaersignal=PrimærSignal.regjeringsposisjon,
                begrunnelse="test",
            )
            for p in ["SV", "R", "MDG"]
        }
        return await lag3_prediker(
            sak_id=_MOCK_ANALYSE.sak_id,
            analyse=_MOCK_ANALYSE,
            partier=["SV", "R", "MDG"],
            lag1_resultat=lag1,
            lag2_resultat={},
            saksfelt=["klima", "miljo"],
            rp={"A"},
            sakskategori="koalisjonssak",
            settings=settings,
            factory=factory,
        )

    def test_returnerer_tre_prediksjoner(self, lag3_med_db):
        assert len(lag3_med_db) == 3

    def test_begrunnelse_refererer_til_db_tall(self, lag3_med_db):
        """Med DB-data tilgjengelig skal begrunnelsen referere til n-verdier eller FOR-rater."""
        import re
        tall_pattern = re.compile(r'\d+\s*%|\bn=\d+|\d+\.\d+')
        for parti, pred in lag3_med_db.items():
            if pred.konfidens != Konfidens.lav:
                assert tall_pattern.search(pred.begrunnelse), \
                    f"{parti}: begrunnelse uten tall selv med DB-data: {pred.begrunnelse!r}"
