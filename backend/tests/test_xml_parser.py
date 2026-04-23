"""
Parser-tester mot de fire XML-filene i tests/fixtures/spike/.

Krever ingen nettverkstilgang — filene ble lagret lokalt under spike-sesjonen.
Kjøres med: pytest tests/test_xml_parser.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import AnalyseFeilet
from app.models.dokument import DokumentStruktur
from app.services.xml_parser import parse_dokument

FIXTURES = Path(__file__).parent / "fixtures" / "spike"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def ny_innstilling() -> DokumentStruktur:
    xml = (FIXTURES / "ny_innstilling_inns-202425-176s.xml").read_bytes()
    return parse_dokument(xml, pub_id="inns-202425-176s")


@pytest.fixture(scope="module")
def ny_dok8() -> DokumentStruktur:
    xml = (FIXTURES / "ny_dok8_dok8-202324-173s.xml").read_bytes()
    return parse_dokument(xml, pub_id="dok8-202324-173s")


@pytest.fixture(scope="module")
def gammel_innstilling() -> DokumentStruktur:
    xml = (FIXTURES / "gammel_innstilling_inns-201011-109.xml").read_bytes()
    return parse_dokument(xml, pub_id="inns-201011-109")


# ── Ny innstilling (inns-202425-176s) ─────────────────────────────────────────


class TestNyInnstilling:
    def test_dok_type(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.dok_type == "ny_innstilling"

    def test_pub_id_bevart(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.pub_id == "inns-202425-176s"

    def test_tittel_inneholder_produktivitet(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.tittel is not None
        assert "produktivitetskommisjon" in ny_innstilling.tittel.lower()

    def test_sesjon(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.sesjon is not None
        assert "2024" in ny_innstilling.sesjon

    def test_kildedok_peker_til_dok8(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.kildedok is not None
        assert "173" in ny_innstilling.kildedok

    def test_minst_to_seksjoner(self, ny_innstilling: DokumentStruktur) -> None:
        assert len(ny_innstilling.seksjoner) >= 2

    def test_seksjon_bakgrunn_finnes(self, ny_innstilling: DokumentStruktur) -> None:
        titler = [s.tittel for s in ny_innstilling.seksjoner]
        assert any("Bakgrunn" in t for t in titler)

    def test_seksjon_merknader_finnes(self, ny_innstilling: DokumentStruktur) -> None:
        titler = [s.tittel for s in ny_innstilling.seksjoner]
        assert any("merknader" in t.lower() for t in titler)

    def test_ett_mindretallsforslag(self, ny_innstilling: DokumentStruktur) -> None:
        assert len(ny_innstilling.mindretallsforslag) == 1

    def test_fraksjon_inneholder_hoyre(self, ny_innstilling: DokumentStruktur) -> None:
        forslag = ny_innstilling.mindretallsforslag[0]
        assert forslag.fra is not None
        assert "Høyre" in forslag.fra.partier_raa

    def test_fraksjon_inneholder_frp(self, ny_innstilling: DokumentStruktur) -> None:
        forslag = ny_innstilling.mindretallsforslag[0]
        assert forslag.fra is not None
        assert "Fremskrittspartiet" in forslag.fra.partier_raa

    def test_fraksjon_partier_er_splittet(self, ny_innstilling: DokumentStruktur) -> None:
        forslag = ny_innstilling.mindretallsforslag[0]
        assert forslag.fra is not None
        # "Høyre, Fremskrittspartiet, Venstre, Kristelig Folkeparti" → 4 partier
        assert len(forslag.fra.partier) == 4

    def test_forslagsnummer(self, ny_innstilling: DokumentStruktur) -> None:
        assert ny_innstilling.mindretallsforslag[0].nr == "1"

    def test_forslagstekst_inneholder_produktivitet(self, ny_innstilling: DokumentStruktur) -> None:
        tekst = ny_innstilling.mindretallsforslag[0].tekst
        assert "produktivitetskommisjon" in tekst.lower()

    def test_vedtakstekst_vedtas_ikke(self, ny_innstilling: DokumentStruktur) -> None:
        # Flertallet forkastet forslaget
        assert ny_innstilling.vedtakstekst is not None
        assert "vedtas ikke" in ny_innstilling.vedtakstekst.lower()

    def test_vedlegg_er_pdf_peker_returnerer_none(self, ny_innstilling: DokumentStruktur) -> None:
        # Ny DTD: <Vedlegg> sier "finnes kun i PDF" → vedlegg_tekst skal være None
        assert ny_innstilling.vedlegg_tekst is None

    def test_ingen_nbsp_i_seksjoner(self, ny_innstilling: DokumentStruktur) -> None:
        for s in ny_innstilling.seksjoner:
            assert "\u00a0" not in s.tekst, f"U+00A0 funnet i seksjon {s.tittel!r}"


# ── Ny Dok 8 (dok8-202324-173s) ───────────────────────────────────────────────


class TestNyDok8:
    def test_dok_type(self, ny_dok8: DokumentStruktur) -> None:
        assert ny_dok8.dok_type == "ny_dok8"

    def test_tittel_inneholder_produktivitet(self, ny_dok8: DokumentStruktur) -> None:
        assert ny_dok8.tittel is not None
        assert "produktivitetskommisjon" in ny_dok8.tittel.lower()

    def test_sesjon(self, ny_dok8: DokumentStruktur) -> None:
        assert ny_dok8.sesjon is not None
        assert "2023" in ny_dok8.sesjon

    def test_ingen_mindretallsforslag(self, ny_dok8: DokumentStruktur) -> None:
        # Original Dok 8 er ikke komitébehandlet — ingen mindretallsforslag
        assert ny_dok8.mindretallsforslag == []

    def test_vedtakstekst_er_selve_forslaget(self, ny_dok8: DokumentStruktur) -> None:
        # I Dok 8 er vedtaksteksten (ForslagTilVedtak/VedtakS) selve forslagspunktet
        assert ny_dok8.vedtakstekst is not None
        assert "produktivitetskommisjon" in ny_dok8.vedtakstekst.lower()

    def test_minst_en_seksjon(self, ny_dok8: DokumentStruktur) -> None:
        assert len(ny_dok8.seksjoner) >= 1

    def test_seksjon_bakgrunn_finnes(self, ny_dok8: DokumentStruktur) -> None:
        assert any("Bakgrunn" in s.tittel for s in ny_dok8.seksjoner)

    def test_ingen_vedlegg(self, ny_dok8: DokumentStruktur) -> None:
        assert ny_dok8.vedlegg_tekst is None

    def test_ingen_nbsp_i_seksjoner(self, ny_dok8: DokumentStruktur) -> None:
        for s in ny_dok8.seksjoner:
            assert "\u00a0" not in s.tekst


# ── Gammel innstilling (inns-201011-109) ──────────────────────────────────────


class TestGammelInnstilling:
    def test_dok_type(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.dok_type == "gammel_innstilling"

    def test_tittel_inneholder_transportetat(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.tittel is not None
        assert "transportetat" in gammel_innstilling.tittel.lower()

    def test_sesjon(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.sesjon is not None
        assert "2010" in gammel_innstilling.sesjon

    def test_kildedok(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.kildedok is not None
        assert "175" in gammel_innstilling.kildedok

    def test_minst_to_seksjoner(self, gammel_innstilling: DokumentStruktur) -> None:
        assert len(gammel_innstilling.seksjoner) >= 2

    def test_ett_mindretallsforslag(self, gammel_innstilling: DokumentStruktur) -> None:
        assert len(gammel_innstilling.mindretallsforslag) == 1

    def test_fraksjon_ap_sv_sp(self, gammel_innstilling: DokumentStruktur) -> None:
        forslag = gammel_innstilling.mindretallsforslag[0]
        assert forslag.fra is not None
        fra = forslag.fra.partier_raa
        assert "Arbeiderpartiet" in fra
        assert "Senterpartiet" in fra

    def test_fraksjon_tre_partier(self, gammel_innstilling: DokumentStruktur) -> None:
        forslag = gammel_innstilling.mindretallsforslag[0]
        assert forslag.fra is not None
        # "Arbeiderpartiet, Sosialistisk Venstreparti og Senterpartiet" → 3 partier
        assert len(forslag.fra.partier) == 3

    def test_forslagstekst_vedlegges_protokollen(self, gammel_innstilling: DokumentStruktur) -> None:
        tekst = gammel_innstilling.mindretallsforslag[0].tekst
        assert "vedlegges protokollen" in tekst.lower()

    def test_vedtakstekst_transportetat(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.vedtakstekst is not None
        assert "transportetat" in gammel_innstilling.vedtakstekst.lower()

    def test_vedlegg_har_innhold(self, gammel_innstilling: DokumentStruktur) -> None:
        # Gammel DTD: <vedlegg> inneholder faktisk tekst (brev fra departement)
        assert gammel_innstilling.vedlegg_tekst is not None
        assert len(gammel_innstilling.vedlegg_tekst) > 200

    def test_vedlegg_inneholder_samferdsel(self, gammel_innstilling: DokumentStruktur) -> None:
        assert gammel_innstilling.vedlegg_tekst is not None
        assert "Samferdselsdepartementet" in gammel_innstilling.vedlegg_tekst

    def test_ingen_nbsp_i_seksjoner(self, gammel_innstilling: DokumentStruktur) -> None:
        for s in gammel_innstilling.seksjoner:
            assert "\u00a0" not in s.tekst, f"U+00A0 funnet i seksjon {s.tittel!r}"

    def test_ingen_nbsp_i_vedlegg(self, gammel_innstilling: DokumentStruktur) -> None:
        if gammel_innstilling.vedlegg_tekst:
            assert "\u00a0" not in gammel_innstilling.vedlegg_tekst


# ── Gammel Dok 8 (dok8-200910-175) ────────────────────────────────────────────


class TestGammelDok8:
    def test_reiser_analysefeilet(self) -> None:
        xml = (FIXTURES / "gammel_dok8_dok8-200910-175.xml").read_bytes()
        with pytest.raises(AnalyseFeilet, match="ikke støttet"):
            parse_dokument(xml, pub_id="dok8-200910-175")

    def test_feilmelding_nevner_dok8(self) -> None:
        xml = (FIXTURES / "gammel_dok8_dok8-200910-175.xml").read_bytes()
        with pytest.raises(AnalyseFeilet, match="<dok8>"):
            parse_dokument(xml, pub_id="dok8-200910-175")
