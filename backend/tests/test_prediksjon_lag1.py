"""
Enhetstester for prediksjon_lag1 — ingen DB, ingen HTTP, ingen LLM.

Dekkede scenarioer:
  - Signal 1: fraksjonsinformasjon fra XML (mindretallsforslag)
  - Signal 2: forslagsstiller-regel (Dok 8 fra ren opposisjon)
  - Signal 2: Dok 8 fra regjeringsparti → fallback til signal 3
  - Signal 3: tilrådingsregel (fallback)
  - sakskategorisering (rutine / koalisjonssak)
  - beregn_samlet_utfall
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.dokument import DokumentStruktur, Forslagspunkt, Fraksjon
from app.models.prediksjon import Konfidens, PrimærSignal
from app.models.sak import Parti, Person, Fylke, Sak, SakOpphav
from app.steps.prediksjon_lag1 import (
    beregn_samlet_utfall,
    klassifiser_sakskategori,
    lag1_prediker,
)

# Testdatoer — A+Sp regjering vs bare A
DATO_STOERE1 = date(2023, 6, 1)   # A+Sp regjering
DATO_STOERE2 = date(2025, 6, 1)   # Bare A regjering

ALLE_PARTIER = ["A", "H", "Sp", "FrP", "SV", "V", "MDG", "R", "KrF"]


# ── Hjelpere for å bygge mock-objekter ───────────────────────────────────────

def _tom_dok(
    med_mindretall: bool = False,
    mindretall_fra: list[str] | None = None,
    tilraading_partier: list[str] | None = None,
) -> DokumentStruktur:
    mindretallsforslag = []
    if med_mindretall:
        partier_str = mindretall_fra or ["SV", "R", "MDG"]
        mindretallsforslag = [
            Forslagspunkt(
                nr="1",
                fra=Fraksjon(
                    partier_raa=", ".join(partier_str),
                    partier=partier_str,
                ),
                tekst="Alternativt forslag",
            )
        ]
    return DokumentStruktur(
        dok_type="ny_innstilling",
        pub_id="TEST-1",
        mindretallsforslag=mindretallsforslag,
        tilraading_partier=tilraading_partier or [],
    )


def _sak_repr_forslag(forslagsstillere: list[str]) -> Sak:
    """Bygger en Sak (dokumentgruppe=4, Dok 8) med gitte forslagsstillere."""
    personer = [
        Person(
            id=f"test_{p}",
            fornavn="Test",
            etternavn=p,
            parti=Parti(id=p, navn=p, representert_parti=True),
            fylke=Fylke(id="oslo", navn="Oslo"),
            vara_representant=False,
        )
        for p in forslagsstillere
    ]
    return Sak(
        id=99999,
        tittel="Test representantforslag",
        dokumentgruppe=4,
        type=1,
        status=0,
        ferdigbehandlet=False,
        sak_opphav=SakOpphav(forslagstiller_liste=personer),
    )


def _sak_proposisjon() -> Sak:
    return Sak(
        id=99998,
        tittel="Test proposisjon",
        dokumentgruppe=2,
        type=1,
        status=0,
        ferdigbehandlet=False,
    )


# ── Signal 1: Fraksjonsinformasjon ────────────────────────────────────────────

class TestSignal1:
    def test_mindretall_er_mot_naar_tilraadingsinfo_finnes(self):
        """Parti med mindretallsforslag er MOT tilrådingen KUN når tilrådingsfraksjonen er eksplisitt angitt."""
        dok = _tom_dok(
            med_mindretall=True,
            mindretall_fra=["SV", "R"],
            tilraading_partier=["A", "H", "Sp", "FrP", "V", "MDG", "KrF"],  # explicit minority
        )
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        assert res["SV"].sannsynlighet_for < 0.5, "SV har mindretallsforslag og er ikke i tilrådingen"
        assert res["R"].sannsynlighet_for < 0.5, "R har mindretallsforslag og er ikke i tilrådingen"
        assert res["SV"].konfidens == Konfidens.hoy
        assert res["SV"].primaersignal == PrimærSignal.fraksjon_xml

    def test_mindretall_uten_tilraadingsinfo_er_for(self):
        """Uten eksplisitt tilrådingsinfo (f.eks. samlet komité) er mindretallspartier FOR tilrådingen.
        Mindretallsforslag og tilrådingen er separate voteringer — de er ikke gjensidig utelukkende."""
        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV", "R"])  # no tilraading_partier
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        assert res["SV"].sannsynlighet_for > 0.5, "SV er FOR tilrådingen (samlet komité, ingen eksplisitt info)"
        assert res["R"].sannsynlighet_for > 0.5, "R er FOR tilrådingen (samlet komité, ingen eksplisitt info)"
        assert res["SV"].konfidens == Konfidens.hoy
        assert res["SV"].primaersignal == PrimærSignal.fraksjon_xml

    def test_partier_utenfor_mindretall_er_for(self):
        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV"])
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        for parti in ["A", "H", "Sp", "FrP", "KrF", "V"]:
            assert res[parti].sannsynlighet_for > 0.5, f"{parti} burde være FOR"
            assert res[parti].konfidens == Konfidens.hoy

    def test_alle_partier_representert(self):
        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV"])
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)
        assert set(res.keys()) == set(ALLE_PARTIER)

    def test_signal1_trumfer_signal2(self):
        """Selv for Dok 8 skal signal 1 brukes hvis mindretallsforslag finnes."""
        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV", "R"])
        sak = _sak_repr_forslag(["SV", "R"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)
        assert res["SV"].primaersignal == PrimærSignal.fraksjon_xml


# ── Signal 2: Forslagsstiller-regel ──────────────────────────────────────────

class TestSignal2:
    def test_rp_stemmer_for_opp_forslag(self):
        """Regjeringspartier stemmer FOR tilrådingen på Dok 8 fra opposisjon."""
        dok = _tom_dok()
        sak = _sak_repr_forslag(["SV", "R", "MDG"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        # A og Sp er regjering (Støre I), forvent høy FOR-rate
        assert res["A"].sannsynlighet_for > 0.95
        assert res["Sp"].sannsynlighet_for > 0.95
        assert res["A"].konfidens == Konfidens.hoy

    def test_forslagsstillere_er_mot(self):
        """Forslagsstillerne selv forventes å stemme MOT tilrådingen."""
        dok = _tom_dok()
        sak = _sak_repr_forslag(["SV", "R"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        assert res["SV"].sannsynlighet_for < 0.05
        assert res["R"].sannsynlighet_for < 0.05
        assert res["SV"].konfidens == Konfidens.hoy

    def test_andre_opp_partier_er_usikre(self):
        """Andre opposisjonspartier som ikke er forslagsstillere → lav konfidens."""
        dok = _tom_dok()
        sak = _sak_repr_forslag(["SV"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        # R, MDG, FrP, KrF, V, H er opp men ikke forslagsstillere
        for parti in ["R", "MDG", "FrP", "KrF", "V", "H"]:
            assert res[parti].konfidens == Konfidens.lav, f"{parti} burde ha lav konfidens"
            assert res[parti].sannsynlighet_for == 0.5

    def test_rp_forslag_faller_til_signal3(self):
        """Dok 8 der et regjeringsparti er forslagsstiller → bruker signal 3 (fallback)."""
        dok = _tom_dok()
        sak = _sak_repr_forslag(["A", "SV"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        # Signal 3: A er rp → middels konfidens
        assert res["A"].konfidens == Konfidens.middels
        assert res["A"].primaersignal == PrimærSignal.regjeringsposisjon

    def test_signal2_bruker_dato_for_rp(self):
        """Støre II (bare A som rp) — Sp er nå opposisjon."""
        dok = _tom_dok()
        sak = _sak_repr_forslag(["SV", "R"])
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE2)

        assert res["A"].sannsynlighet_for > 0.95      # A er fortsatt rp
        assert res["Sp"].konfidens == Konfidens.lav   # Sp er nå opposisjon → usikker


# ── Signal 3: Tilrådingsregel ─────────────────────────────────────────────────

class TestSignal3:
    def test_rp_far_middels_konfidens(self):
        dok = _tom_dok()
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        assert res["A"].konfidens == Konfidens.middels
        assert res["Sp"].konfidens == Konfidens.middels

    def test_rp_bruker_fallback_rater(self):
        """A og Sp har kjente lave FOR-rater på omstridte tilrådinger."""
        dok = _tom_dok()
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        assert res["A"].sannsynlighet_for == pytest.approx(0.10)
        assert res["Sp"].sannsynlighet_for == pytest.approx(0.07)

    def test_rp_bruker_db_rate_nar_tilgjengelig(self):
        """DB-rater overstyrer fallback."""
        dok = _tom_dok()
        sak = _sak_proposisjon()
        res = lag1_prediker(
            dok, sak,
            alle_partier=ALLE_PARTIER,
            dato=DATO_STOERE1,
            tilraading_for_rate={"A": 0.15, "Sp": 0.12},
        )
        assert res["A"].sannsynlighet_for == pytest.approx(0.15)
        assert res["Sp"].sannsynlighet_for == pytest.approx(0.12)

    def test_opp_partier_far_lav_konfidens(self):
        dok = _tom_dok()
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)

        for parti in ["H", "FrP", "SV", "V", "MDG", "R", "KrF"]:
            assert res[parti].konfidens == Konfidens.lav, f"{parti} burde ha lav konfidens"

    def test_alle_partier_returnert(self):
        dok = _tom_dok()
        sak = _sak_proposisjon()
        res = lag1_prediker(dok, sak, alle_partier=ALLE_PARTIER, dato=DATO_STOERE1)
        assert set(res.keys()) == set(ALLE_PARTIER)


# ── Sakskategorisering ────────────────────────────────────────────────────────

class TestSakskategorisering:
    def _build_prediksjoner(self, konfidenser: dict[str, Konfidens]):
        from app.models.prediksjon import PartiPrediksjon, PrimærSignal
        return {
            p: PartiPrediksjon(
                parti=p,
                sannsynlighet_for=0.9,
                konfidens=k,
                primaersignal=PrimærSignal.fraksjon_xml,
                begrunnelse="test",
            )
            for p, k in konfidenser.items()
        }

    def test_alle_hoy_er_rutine(self):
        pred = self._build_prediksjoner({p: Konfidens.hoy for p in ALLE_PARTIER})
        rp = {"A", "Sp"}
        assert klassifiser_sakskategori(pred, rp, set(), []) == "rutine"

    def test_rp_lav_er_koalisjonssak(self):
        kfig = {p: Konfidens.hoy for p in ALLE_PARTIER}
        kfig["A"] = Konfidens.lav
        pred = self._build_prediksjoner(kfig)
        rp = {"A", "Sp"}
        assert klassifiser_sakskategori(pred, rp, set(), []) == "koalisjonssak"

    def test_blandet_men_rp_hoy_er_koalisjonssak(self):
        kfig = {p: Konfidens.lav for p in ALLE_PARTIER}
        kfig["A"] = Konfidens.hoy
        kfig["Sp"] = Konfidens.hoy
        pred = self._build_prediksjoner(kfig)
        rp = {"A", "Sp"}
        # Ingen rp har lav → koalisjonssak (kun lav totalt)
        assert klassifiser_sakskategori(pred, rp, set(), []) == "koalisjonssak"


# ── Samlet utfall ─────────────────────────────────────────────────────────────

class TestSamletUtfall:
    def _pred(self, prob: float, konfidens: Konfidens = Konfidens.hoy):
        from app.models.prediksjon import PartiPrediksjon, PrimærSignal
        return PartiPrediksjon(
            parti="X",
            sannsynlighet_for=prob,
            konfidens=konfidens,
            primaersignal=PrimærSignal.fraksjon_xml,
            begrunnelse="test",
        )

    def test_flertall_for_er_bifalt(self):
        pred = {
            "A": self._pred(0.9), "H": self._pred(0.9), "Sp": self._pred(0.9),
            "FrP": self._pred(0.9), "KrF": self._pred(0.1), "SV": self._pred(0.1),
        }
        utfall, _ = beregn_samlet_utfall(pred)
        assert utfall == "sannsynlig_bifalt"

    def test_flertall_mot_er_forkastet(self):
        pred = {
            "A": self._pred(0.1), "H": self._pred(0.1), "Sp": self._pred(0.1),
            "FrP": self._pred(0.1), "KrF": self._pred(0.9),
        }
        utfall, _ = beregn_samlet_utfall(pred)
        assert utfall == "sannsynlig_forkastet"

    def test_jevnt_er_usikkert(self):
        pred = {
            "A": self._pred(0.9), "H": self._pred(0.9),
            "Sp": self._pred(0.1), "FrP": self._pred(0.1),
        }
        utfall, _ = beregn_samlet_utfall(pred)
        assert utfall == "usikkert"

    def test_alle_hoy_konfidens_gir_hoy_samlet(self):
        pred = {p: self._pred(0.9, Konfidens.hoy) for p in ALLE_PARTIER}
        _, k = beregn_samlet_utfall(pred)
        assert k == Konfidens.hoy

    def test_blandet_konfidens_gir_middels(self):
        pred = {
            "A": self._pred(0.9, Konfidens.hoy),
            "H": self._pred(0.9, Konfidens.lav),
        }
        _, k = beregn_samlet_utfall(pred)
        assert k == Konfidens.middels

    def test_tom_prediksjoner_er_usikkert_lav(self):
        utfall, k = beregn_samlet_utfall({})
        assert utfall == "usikkert"
        assert k == Konfidens.lav


# ── lag1_mindretallsforslag_prediksjoner ─────────────────────────────────────

class TestLag1Mindretallsforslag:
    def test_forslagsstillere_far_for_hoy(self):
        """Forslagsstillerne skal alltid ha høy konfidens FOR egne forslag."""
        from app.steps.prediksjon_lag1 import lag1_mindretallsforslag_prediksjoner

        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV", "R"])
        voteringer = lag1_mindretallsforslag_prediksjoner(dok, ALLE_PARTIER)

        assert len(voteringer) == 1
        vot = voteringer[0]
        sv = next(p for p in vot.prediksjoner if p.parti == "SV")
        r = next(p for p in vot.prediksjoner if p.parti == "R")
        assert sv.sannsynlighet_for > 0.5
        assert sv.konfidens == Konfidens.hoy
        assert r.sannsynlighet_for > 0.5
        assert r.konfidens == Konfidens.hoy

    def test_ikke_forslagsstillere_far_lav_konfidens(self):
        """Ikke-forslagsstillere skal ha lav konfidens (for å trigge lag 2/3)."""
        from app.steps.prediksjon_lag1 import lag1_mindretallsforslag_prediksjoner

        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV", "R"])
        voteringer = lag1_mindretallsforslag_prediksjoner(dok, ALLE_PARTIER)
        vot = voteringer[0]

        for parti in ["A", "H", "Sp", "FrP", "V", "MDG", "KrF"]:
            pred = next(p for p in vot.prediksjoner if p.parti == parti)
            assert pred.konfidens == Konfidens.lav, f"{parti} burde ha lav konfidens"
            assert pred.sannsynlighet_for < 0.5, f"{parti} burde ha lav sannsynlighet"

    def test_forslagstekst_og_forslagsstillere_inkludert(self):
        """VoteringPrediksjon skal inneholde forslagstekst og forslagsstillere."""
        from app.steps.prediksjon_lag1 import lag1_mindretallsforslag_prediksjoner

        dok = _tom_dok(med_mindretall=True, mindretall_fra=["SV", "R"])
        voteringer = lag1_mindretallsforslag_prediksjoner(dok, ALLE_PARTIER)
        vot = voteringer[0]

        assert vot.forslagstekst is not None
        assert "Alternativt forslag" in vot.forslagstekst
        assert set(vot.forslagsstillere) == {"SV", "R"}

    def test_gruppert_etter_forslagsstillere(self):
        """Forslag fra ulike partikonstellasjoner skal gi separate VoteringPrediksjon."""
        from app.steps.prediksjon_lag1 import lag1_mindretallsforslag_prediksjoner
        from app.models.dokument import DokumentStruktur, Forslagspunkt, Fraksjon

        dok = DokumentStruktur(
            dok_type="ny_innstilling",
            pub_id="TEST",
            mindretallsforslag=[
                Forslagspunkt(nr="1", fra=Fraksjon(partier_raa="SV, R", partier=["SV", "R"]), tekst="Forslag A"),
                Forslagspunkt(nr="2", fra=Fraksjon(partier_raa="KrF", partier=["KrF"]), tekst="Forslag B"),
            ],
        )
        voteringer = lag1_mindretallsforslag_prediksjoner(dok, ALLE_PARTIER)
        assert len(voteringer) == 2
