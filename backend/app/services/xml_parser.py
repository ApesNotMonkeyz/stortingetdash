from __future__ import annotations

import re
import structlog
from lxml import etree

from app.exceptions import AnalyseFeilet
from app.models.dokument import DokType, DokumentStruktur, Forslagspunkt, Fraksjon, Seksjon
from app.utils.partier import normaliser_partiliste

log = structlog.get_logger()


def parse_dokument(xml_bytes: bytes, pub_id: str = "") -> DokumentStruktur:
    """
    Parser XML-bytes til DokumentStruktur.

    Støttede dokumenttyper (bestemt av rotelementnavn):
      <Innstilling> + <ForslagFraMindretall>  → ny_innstilling  (innstillinger.dtd 2016+)
      <Innstilling> uten <ForslagFraMindretall> → ny_dok8       (innstillinger.dtd 2016+)
      <innstilling>                             → gammel_innstilling (innst_xml.dtd)
      <dok8>                                    → AnalyseFeilet (ikke støttet)
    """
    # Normaliser U+00A0 (non-breaking space, UTF-8: 0xC2 0xA0) til vanlig mellomrom
    # tidlig i pipelinen slik at tekstfeltene i output er rene.
    xml_bytes = xml_bytes.replace(b"\xc2\xa0", b" ")

    try:
        tree = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise AnalyseFeilet(f"XML-parsing feiler for {pub_id!r}: {exc}") from exc

    root_tag: str = tree.tag
    log.debug("xml_parser_rotelement", pub_id=pub_id, root_tag=root_tag)

    if root_tag == "Innstilling":
        if tree.xpath("//ForslagFraMindretall"):
            return _parse_ny_innstilling(tree, pub_id)
        return _parse_ny_dok8(tree, pub_id)

    if root_tag == "innstilling":
        return _parse_gammel_innstilling(tree, pub_id)

    if root_tag == "dok8":
        raise AnalyseFeilet(
            "Analyse ikke støttet for denne dokumenttypen: <dok8> (gammel Dok 8-DTD). "
            "Hent innstillingen (publikasjon type 6) i stedet, "
            "eller vent til saken er komitébehandlet."
        )

    raise AnalyseFeilet(
        f"Ukjent XML-rootelement: {root_tag!r} for publikasjon {pub_id!r}"
    )


# ── Hjelpefunksjoner ──────────────────────────────────────────────────────────


def _tekst(el: etree._Element | None) -> str:
    """All tekst fra element og etterkommere, stripet. U+00A0 allerede normalisert."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _finn(parent: etree._Element | None, tag: str) -> str | None:
    """Henter tekstinnhold fra første child med gitt tag; None hvis mangler."""
    if parent is None:
        return None
    el = parent.find(tag)
    return _tekst(el) or None


_WS = re.compile(r"\s+")


def _split_partier(fra_raa: str) -> list[str]:
    """
    Splitter komma-/og-separert navnestreng til liste.
    Normaliserer whitespace (inkl. newlines) før splitting.
    Håndterer 'Høyre, FrP' og 'Ap, SV og Sp' og 'X,\\nY og Z'.
    """
    t = _WS.sub(" ", fra_raa).strip()
    partier: list[str] = []
    for del_ in t.split(","):
        del_ = del_.strip()
        if " og " in del_:
            partier.extend(p.strip() for p in del_.split(" og ") if p.strip())
        elif del_:
            partier.append(del_)
    return partier


def _parse_fraksjon_tittel(tittel: str) -> list[str]:
    """
    Ekstraherer partinavn fra <Fraksjon><Tittel>-tekst.
    'Forslag fra Sosialistisk Venstreparti, Senterpartiet og Rødt:' → ['Sosialistisk Venstreparti', ...]
    """
    t = _WS.sub(" ", tittel).strip()
    if t.lower().startswith("forslag fra "):
        t = t[len("forslag fra "):]
    return _split_partier(t.rstrip(":"))


def _parse_tilraading_fra_tekst(tekst: str) -> list[str]:
    """
    Ekstraherer tilrådingspartier fra KomTilrading/A-tekst.
    'Komiteens tilråding fremmes av ... fra Arbeiderpartiet, SV og Sp.' → ['Arbeiderpartiet', 'SV', 'Sp']
    Returnerer [] hvis mønsteret ikke gjenkjennes.
    """
    t = _WS.sub(" ", tekst).strip()
    idx = t.lower().rfind(" fra ")
    if idx == -1:
        return []
    rest = t[idx + 5:].rstrip(".").strip()
    return _split_partier(rest)


def _les_fraksjon(el: etree._Element, attr: str) -> Fraksjon:
    """
    Lager Fraksjon fra et <Fraksjon>/<fraksjon>-element.
    Prioritet: @Fra/@fra-attributt (eldre DTD) → <Tittel>-tekst (ny DTD).
    """
    fra_raa = el.get(attr, "")
    if fra_raa:
        return Fraksjon(partier_raa=fra_raa, partier=_split_partier(fra_raa))
    tittel_el = el.find("Tittel")
    if tittel_el is None:
        tittel_el = el.find("tittel")
    tittel_tekst = _tekst(tittel_el) if tittel_el is not None else ""
    return Fraksjon(partier_raa=tittel_tekst, partier=_parse_fraksjon_tittel(tittel_tekst))


def _seksjoner_ny(tree: etree._Element) -> list[Seksjon]:
    """Seksjoner fra ny DTD: //Hovedseksjon/Kapittel."""
    seksjoner = []
    for kap in tree.xpath("//Hovedseksjon/Kapittel"):
        tittel = _tekst(kap.find("Tittel"))
        tekst = _tekst(kap)
        seksjoner.append(Seksjon(tittel=tittel, tekst=tekst))
    return seksjoner


def _seksjoner_gammel(tree: etree._Element) -> list[Seksjon]:
    """Seksjoner fra gammel DTD: //til/kapittel."""
    seksjoner = []
    for kap in tree.xpath("//til/kapittel"):
        tittel = _tekst(kap.find("tit"))
        tekst = _tekst(kap)
        seksjoner.append(Seksjon(tittel=tittel, tekst=tekst))
    return seksjoner


def _vedtakstekst_ny(tree: etree._Element) -> str | None:
    """Vedtakstekst fra ny DTD: VedtakS eller VedtakL i KomTilrading."""
    for xpath in (
        "//KomTilrading/ForslagTilVedtak/VedtakS",
        "//KomTilrading/ForslagTilVedtak/VedtakL",
    ):
        hits: list[etree._Element] = tree.xpath(xpath)
        if hits:
            return _tekst(hits[0]) or None
    return None


# ── Parsere ───────────────────────────────────────────────────────────────────


def _parse_ny_innstilling(tree: etree._Element, pub_id: str) -> DokumentStruktur:
    """Ny DTD innstilling (2016+): <Innstilling> med <ForslagFraMindretall>."""
    start = tree.find("Startseksjon")

    tittel = _finn(start, "Ingress") or _finn(start, "Doktit")
    sesjon = _finn(start, "Aar")
    kildedok = _finn(start, "Kildedok")

    mindretallsforslag: list[Forslagspunkt] = []
    for fraksjon_el in tree.xpath("//ForslagFraMindretall/Fraksjon"):
        fraksjon = _les_fraksjon(fraksjon_el, "Fra")
        for forslag_el in fraksjon_el.xpath("Forslag"):
            nr_raa = _finn(forslag_el, "Tittel") or forslag_el.get("Nr", "?")
            # Forslagsnummer: hent tall fra "Forslag 1" eller bruk Nr-attributt
            nr_m = re.search(r"\d+", nr_raa)
            nr = nr_m.group() if nr_m else nr_raa
            tekst = _tekst(forslag_el)
            mindretallsforslag.append(Forslagspunkt(nr=nr, fra=fraksjon, tekst=tekst))

    # Tilrådingspartier fra KomTilrading/A-introduksjonstekst
    tilraading_partier: list[str] = []
    kom_a_hits: list[etree._Element] = tree.xpath("//KomTilrading/A")
    if kom_a_hits:
        intro = _tekst(kom_a_hits[0])
        raw = _parse_tilraading_fra_tekst(intro)
        tilraading_partier = normaliser_partiliste(raw)
        if tilraading_partier:
            log.debug("xml_tilraading_partier", pub_id=pub_id, partier=tilraading_partier)

    vedlegg_tekst: str | None = None
    for vedlegg_el in tree.xpath("//Vedlegg"):
        v = _tekst(vedlegg_el)
        if v and "kun i PDF" not in v:
            vedlegg_tekst = v
        break

    return DokumentStruktur(
        dok_type="ny_innstilling",
        pub_id=pub_id,
        tittel=tittel,
        sesjon=sesjon,
        kildedok=kildedok,
        seksjoner=_seksjoner_ny(tree),
        mindretallsforslag=mindretallsforslag,
        tilraading_partier=tilraading_partier,
        vedtakstekst=_vedtakstekst_ny(tree),
        vedlegg_tekst=vedlegg_tekst,
    )


def _parse_ny_dok8(tree: etree._Element, pub_id: str) -> DokumentStruktur:
    """Ny DTD Dok 8 (2016+): <Innstilling> uten <ForslagFraMindretall>."""
    start = tree.find("Startseksjon")

    tittel = _finn(start, "Ingress") or _finn(start, "Doktit")
    sesjon = _finn(start, "Aar")
    kildedok = _finn(start, "Kildedok")

    return DokumentStruktur(
        dok_type="ny_dok8",
        pub_id=pub_id,
        tittel=tittel,
        sesjon=sesjon,
        kildedok=kildedok,
        seksjoner=_seksjoner_ny(tree),
        mindretallsforslag=[],
        vedtakstekst=_vedtakstekst_ny(tree),
        vedlegg_tekst=None,
    )


def _parse_gammel_innstilling(tree: etree._Element, pub_id: str) -> DokumentStruktur:
    """Gammel DTD innstilling (pre-2016): <innstilling> med <forslagfram>."""
    front = tree.find("front")
    titgrp = front.find("titgrp") if front is not None else None

    tittel = _finn(titgrp, "tit")
    sesjon = _finn(titgrp, "aar")
    kildedok = _finn(titgrp, "kildedok")

    mindretallsforslag: list[Forslagspunkt] = []
    for fraksjon_el in tree.xpath("//forslagfram/fraksjon"):
        fraksjon = _les_fraksjon(fraksjon_el, "fra")
        for forsl_el in fraksjon_el.xpath("forsl"):
            nr = forsl_el.get("nr", "?")
            tekst = _tekst(forsl_el)
            mindretallsforslag.append(Forslagspunkt(nr=nr, fra=fraksjon, tekst=tekst))

    vedtakstekst: str | None = None
    hits: list[etree._Element] = tree.xpath(
        "//komtilr/forslag-til-vedtak/vedtak/vedtakstekst"
    )
    if hits:
        vedtakstekst = _tekst(hits[0]) or None

    # Gammel DTD: <vedlegg> inneholder faktisk tekstinnhold (ikke bare PDF-peker).
    vedlegg_tekst: str | None = None
    vedlegg_els: list[etree._Element] = tree.xpath("//vedlegg")
    if vedlegg_els:
        vedlegg_tekst = _tekst(vedlegg_els[0]) or None

    return DokumentStruktur(
        dok_type="gammel_innstilling",
        pub_id=pub_id,
        tittel=tittel,
        sesjon=sesjon,
        kildedok=kildedok,
        seksjoner=_seksjoner_gammel(tree),
        mindretallsforslag=mindretallsforslag,
        vedtakstekst=vedtakstekst,
        vedlegg_tekst=vedlegg_tekst,
    )
