"""
Lag 1 — deterministisk prediksjon (null LLM-kostnad, null DB-kall).

Tre signaler i prioritert rekkefølge:

1. Fraksjonsinformasjon fra innstillingens XML (<ForslagFraMindretall> + <KomTilrading>):
   Eksplisitt navngitt i tilrådingsfraksjonen → FOR (sannsynlighet_for = _FRAKSJON_KONFIDENS, høy konfidens).
   Ikke i tilrådingen men har mindretallsforslag → MOT (sannsynlighet_for = 1 - _FRAKSJON_KONFIDENS, høy konfidens).
   Ikke i noen av dem, men tilrådingsinfo finnes → ukjent (lav konfidens, videre til lag 2).
   Ingen tilrådingsinfo (f.eks. "samlet komité") → FOR (fallback, uavhengig av mindretallsforslag).
   NB: mindretallsforslag og tilrådingen er separate voteringer. Et parti kan stemme FOR
   tilrådingen OG FOR egne tilleggsforslag — disse er ikke gjensidig utelukkende.

2. Forslagsstiller-regel (fra baseline beregning 0):
   Representantforslag fra opposisjonspartier → regjeringen FOR (baseline: 99.6% FOR).
   Representantforslag fra regjeringsparti → regjeringen MOT (baseline: ~0% FOR).

3. Tilrådingsregel (fra baseline beregning 2):
   Regjeringspartier i mindretallsregjering → lav sannsynlighet_for på omstridte tilrådinger.
   Fallback med middels konfidens; bruker empiriske rater fra DB (tilraading_for_rate).

Stemme-semantikk (viktig):
  sannsynlighet_for = P(partiet stemmer FOR tilrådingen).
  Lav verdi (≈0.10) betyr partiet forventes å stemme MOT tilrådingen —
  dvs. FOR det alternative forslaget / egne mindretallsforslag.
"""
from __future__ import annotations

from datetime import date

import structlog

from app.config import regjering_partier_for_dato
from app.models.dokument import DokumentStruktur, Forslagspunkt
from app.models.prediksjon import (
    Konfidens,
    PartiPrediksjon,
    PrimærSignal,
    SamletUtfall,
    VoteringPrediksjon,
    VoteringType,
)
from app.models.sak import Sak
from app.utils.partier import KJERNE_PARTIER, normaliser_partiliste

log = structlog.get_logger()

# Signal 1 konfidens — beregning 3 (beregn_fraksjon_konsistens.py, 30 saker 2023–2025):
# Målt konsistensrate 34.0% (n=250). Mindretall=41.1%, flertall=27.0%.
# Lavt tall skyldes primært minoritetsregjerings-effekt: flertallspartier stemmer
# hyppig MOT tilrådingen fordi tilrådingen er opposisjonens versjon.
# 0.80 er konservativt gulv (ikke fra råtall); re-evaluer med majoritetsregjerings-data.
_FRAKSJON_KONFIDENS = 0.80  # Empirisk gulv: beregning 3, 34.0% målt (2023-2025)

# Baseline-tall fra beregning 0 (voteringsdata 2021-2025):
# Regjeringspartier på representantforslag fra utelukkende opposisjonspartier:
# FOR-rate = 99.6% → regjeringen støtter tilrådingen nesten alltid.
_OPP_FORSLAG_FOR_RATE = 0.996

# Baseline beregning 2 (tilrådingsvoteringer, omstridte, _total):
# Brukes når DB-oppslag ikke gir sak-spesifikke rater.
_FALLBACK_TILRAADING_FOR_RATE: dict[str, float] = {
    "A": 0.100,   # 10.0%, n=797
    "Sp": 0.070,  # 7.0%, n=497
}


def lag1_prediker(
    dok: DokumentStruktur,
    sak: Sak,
    alle_partier: list[str] | None = None,
    dato: date | None = None,
    tilraading_for_rate: dict[str, float] | None = None,
) -> dict[str, PartiPrediksjon]:
    """
    Kjører lag 1 og returnerer PartiPrediksjon per parti.

    Parametere:
        dok: Ferdig parsert DokumentStruktur (fra saksanalyse-pipelinen steg 3).
        sak: Saksmetadata fra Stortingets API.
        alle_partier: Liste med partikoder å gi indikasjoner for. Standard: KJERNE_PARTIER.
        dato: Dato for å bestemme regjeringssammensetning. Standard: i dag.
        tilraading_for_rate: FOR-rate per parti på tilrådingsvoteringer (fra DB/parti_moenster).
                             Brukes i signal 3. Faller tilbake til _FALLBACK_TILRAADING_FOR_RATE.
    """
    partier = alle_partier if alle_partier is not None else KJERNE_PARTIER
    dato_bruk = dato or date.today()
    rp = regjering_partier_for_dato(dato_bruk)
    rater = tilraading_for_rate or {}

    # ── Signal 1: Fraksjonsinformasjon fra XML ────────────────────────────────
    if dok.mindretallsforslag:
        log.debug("lag1_signal1", sak_id=sak.id, n_forslag=len(dok.mindretallsforslag))
        return _signal1_fraksjon(dok, sak.id, partier, rp)

    # ── Signal 2: Forslagsstiller-regel ──────────────────────────────────────
    if sak.er_representantforslag and sak.sak_opphav:
        forslagsstillere = frozenset(
            p.parti.id
            for p in sak.sak_opphav.forslagstiller_liste
            if p.parti and p.parti.id
        )
        if forslagsstillere:
            log.debug("lag1_signal2", sak_id=sak.id, forslagsstillere=list(forslagsstillere))
            s2 = _signal2_repr_forslag(sak.id, forslagsstillere, partier, dato_bruk, rp)
            if s2:
                return s2
            # {} → Dok8 fra regjeringsparti, fall through to signal 3

    # ── Signal 3: Tilrådingsregel (fallback) ─────────────────────────────────
    log.debug("lag1_signal3_fallback", sak_id=sak.id)
    return _signal3_tilraading(sak.id, partier, rp, rater)


# ── Interne implementasjoner ──────────────────────────────────────────────────


def _signal1_fraksjon(
    dok: DokumentStruktur,
    sak_id: int,
    alle_partier: list[str],
    rp: set[str],
) -> dict[str, PartiPrediksjon]:
    """
    Fire-veis klassifisering fra XML-fraksjonsinformasjon for tilrådingen:

    1. Navngitt i tilraading_partier → FOR tilrådingen (høy konfidens).
    2. Ingen tilrådingsinfo (f.eks. samlet komité) → FOR tilrådingen (fallback, høy konfidens).
       NB: mindretallsforslag betyr IKKE at partiet er mot tilrådingen — de er separate voteringer.
    3. Tilrådingsinfo finnes og partiet har mindretallsforslag men er ikke i tilrådingen → MOT (høy konfidens).
    4. Tilrådingsinfo finnes, partiet er verken i tilrådingen eller mindretallsforslag → ukjent, lav konfidens.
    """
    partier_mot: set[str] = set()
    for fp in dok.mindretallsforslag:
        if fp.fra and fp.fra.partier:
            for kode in normaliser_partiliste(fp.fra.partier):
                partier_mot.add(kode)

    tilraading: set[str] = set(dok.tilraading_partier)
    har_tilraadingsinfo = bool(tilraading)

    resultat: dict[str, PartiPrediksjon] = {}
    for parti in alle_partier:
        er_i_tilraading = parti in tilraading
        er_i_mindretall = parti in partier_mot
        naiv_for = parti in rp

        if er_i_tilraading:
            # Eksplisitt navngitt i tilrådingsfraksjonen — FOR høy konfidens.
            # Inkluderer partier med tilleggsforslag (SV/Sp-type) — tilrådingen har prioritet.
            sannsynlighet = _FRAKSJON_KONFIDENS
            konfidens = Konfidens.hoy
            begrunnelse = (
                f"{parti} er eksplisitt navngitt som tilrådingsfraternitet i komiteinnstillingen "
                f"— forventes å stemme FOR tilrådingen "
                f"(sannsynlighet_for={sannsynlighet:.0%}; signal 1 fraksjonsinformasjon fra XML)."
            )
        elif not har_tilraadingsinfo:
            # Ingen tilrådingsinfo (samlet komité, eldre dokumenter).
            # Mindretallsforslag betyr ikke MOT tilrådingen — de er separate voteringer.
            sannsynlighet = _FRAKSJON_KONFIDENS
            konfidens = Konfidens.hoy
            begrunnelse = (
                f"{parti} er del av komitéflertallet og forventes å støtte tilrådingen "
                f"(sannsynlighet_for={sannsynlighet:.0%}; signal 1 fraksjonsinformasjon fra XML, "
                f"ingen eksplisitt tilrådingsfraternitet oppgitt i dette dokumentet)."
            )
        elif er_i_mindretall:
            # Tilrådingsinfo finnes, partiet har mindretallsforslag og er IKKE i tilrådingen → MOT
            sannsynlighet = 1.0 - _FRAKSJON_KONFIDENS
            konfidens = Konfidens.hoy
            begrunnelse = (
                f"{parti} fremmet mindretallsforslag i komiteen og er ikke del av "
                f"tilrådingsfraksjonen — forventes å stemme MOT tilrådingen i plenum "
                f"(sannsynlighet_for={sannsynlighet:.0%}; signal 1 fraksjonsinformasjon fra XML)."
            )
        else:
            # Tilrådingsinfo finnes men partiet er ikke navngitt i noen → ukjent posisjon
            sannsynlighet = 0.40
            konfidens = Konfidens.lav
            begrunnelse = (
                f"{parti} er verken navngitt i tilrådingsfraksjonen eller i mindretallsforslag "
                f"— posisjon ukjent fra XML (sannsynlighet_for={sannsynlighet:.0%}; "
                f"lav konfidens, videresendes til lag 2)."
            )

        avvik = (sannsynlighet < 0.5) != (not naiv_for)

        resultat[parti] = PartiPrediksjon(
            parti=parti,
            sannsynlighet_for=sannsynlighet,
            konfidens=konfidens,
            primaersignal=PrimærSignal.fraksjon_xml,
            begrunnelse=begrunnelse,
            avvik_fra_baseline=avvik,
        )

    return resultat


def _signal2_repr_forslag(
    sak_id: int,
    forslagsstillere: frozenset[str],
    alle_partier: list[str],
    dato: date,
    rp: set[str],
) -> dict[str, PartiPrediksjon]:
    """
    Forslagsstiller-regel for representantforslag.

    Alle forslagsstillere er opposisjonspartier:
      - Regjeringspartier: FOR tilrådingen (baseline 99.6%)
      - Forslagsstillerne: MOT tilrådingen (de støtter egne forslag ≈ 99.6%)
      - Andre opposisjonspartier: USIKKERT → lav konfidens

    Minst ett forslagsstiller er regjeringsparti:
      - Sjeldent tilfelle, signal 2 returnerer None → faller tilbake til signal 3.
    """
    er_alle_opp = all(p not in rp for p in forslagsstillere)
    er_noen_rp = any(p in rp for p in forslagsstillere)

    if er_noen_rp:
        # Dok8 fra regjeringsparti: sjeldent og komplekst — la signal 3 håndtere det
        return {}

    if not er_alle_opp:
        return {}

    # Representantforslag fra utelukkende opposisjonspartier
    forslagsstillere_str = ", ".join(sorted(forslagsstillere))
    resultat: dict[str, PartiPrediksjon] = {}

    for parti in alle_partier:
        er_rp = parti in rp
        er_forslagsstiller = parti in forslagsstillere

        if er_rp:
            sannsynlighet = _OPP_FORSLAG_FOR_RATE
            konfidens = Konfidens.hoy
            begrunnelse = (
                f"{parti} er regjeringsparti på representantforslag fra {forslagsstillere_str} "
                f"— stemmer FOR tilrådingen (baseline: {_OPP_FORSLAG_FOR_RATE:.1%} FOR, "
                f"beregning 0, n=3573)."
            )
            avvik = False  # Konsistent med naiv baseline

        elif er_forslagsstiller:
            sannsynlighet = 1.0 - _OPP_FORSLAG_FOR_RATE
            konfidens = Konfidens.hoy
            begrunnelse = (
                f"{parti} fremmet representantforslaget — stemmer MOT tilrådingen "
                f"(sannsynlighet_for={1.0 - _OPP_FORSLAG_FOR_RATE:.1%}, beregning 0, n=3573)."
            )
            avvik = False  # Konsistent med naiv baseline

        else:
            # Andre opposisjonspartier: noen ganger støtter de opposisjonsforslag, men ikke alltid
            sannsynlighet = 0.5
            konfidens = Konfidens.lav
            begrunnelse = (
                f"{parti} er opposisjonsparti men ikke forslagsstiller — uklar retning. "
                f"Historisk mønstermatching (lag 2) anbefales."
            )
            avvik = False

        resultat[parti] = PartiPrediksjon(
            parti=parti,
            sannsynlighet_for=sannsynlighet,
            konfidens=konfidens,
            primaersignal=PrimærSignal.regjeringsposisjon,
            begrunnelse=begrunnelse,
            avvik_fra_baseline=avvik,
        )

    return resultat


def _signal3_tilraading(
    sak_id: int,
    alle_partier: list[str],
    rp: set[str],
    tilraading_for_rate: dict[str, float],
) -> dict[str, PartiPrediksjon]:
    """
    Fallback: tilrådingsregel for mindretallsregjering.

    Regjeringspartier stemmer mot omstridte tilrådinger i ~90% av tilfellene
    (A: 10% FOR, Sp: 7% FOR — beregning 2). Middels konfidens.
    Ikke-regjeringspartier: lav konfidens, ingen pålitelig regel.
    """
    resultat: dict[str, PartiPrediksjon] = {}

    for parti in alle_partier:
        if parti in rp:
            rate = tilraading_for_rate.get(
                parti,
                _FALLBACK_TILRAADING_FOR_RATE.get(parti, 0.10),
            )
            begrunnelse = (
                f"{parti} er regjeringsparti i mindretallsregjering — stemmer mot omstridte "
                f"tilrådinger i ~{(1 - rate):.0%} av tilfellene "
                f"(sannsynlighet_for={rate:.0%}, baseline beregning 2). "
                f"Middels konfidens: varierer med sakstype."
            )
            konfidens = Konfidens.middels
        else:
            rate = 0.5
            begrunnelse = (
                f"Ingen strukturell informasjon om {parti}s posisjon — "
                f"anbefaler historisk mønstermatching (lag 2)."
            )
            konfidens = Konfidens.lav

        resultat[parti] = PartiPrediksjon(
            parti=parti,
            sannsynlighet_for=rate,
            konfidens=konfidens,
            primaersignal=PrimærSignal.regjeringsposisjon,
            begrunnelse=begrunnelse,
            avvik_fra_baseline=False,
        )

    return resultat


# ── Hjelpefunksjoner brukt av pipeline ───────────────────────────────────────


def klassifiser_sakskategori(
    prediksjoner: dict[str, PartiPrediksjon],
    rp: set[str],
    lav_predikabilitet_saksfelter: set[str],
    saksfelt: list[str],
) -> str:
    """
    Sakskategori basert på konfidensfordeling i lag 1-resultat.

    - rutine: alle prediksjoner har høy konfidens
    - personvotering: saksfelt med dokumentert lav predikabilitet (beregning 6)
    - koalisjonssak: regjeringspartier har lav konfidens, eller lav generell konfidens
    - balansesak: blandet konfidens innad i en blokk
    """
    alle_konfidenser = {p.konfidens for p in prediksjoner.values()}
    if alle_konfidenser == {Konfidens.hoy}:
        return "rutine"

    # Saksfelt med lav predikabilitet → balansesak (beregning 6)
    if lav_predikabilitet_saksfelter and any(sf in lav_predikabilitet_saksfelter for sf in saksfelt):
        return "balansesak"

    # Regjeringspartier med lav konfidens → koalisjonssak
    rp_konfidenser = {prediksjoner[p].konfidens for p in prediksjoner if p in rp}
    if Konfidens.lav in rp_konfidenser:
        return "koalisjonssak"

    return "koalisjonssak"


def beregn_samlet_utfall(
    prediksjoner: dict[str, PartiPrediksjon],
) -> tuple[str, Konfidens]:
    """
    Estimerer om tilrådingen sannsynligvis vil bifales.

    Enkel heuristikk basert på antall partier med sannsynlighet_for > 0.5.
    En mandatvektet versjon implementeres i en fremtidig fase.

    Returnerer (samlet_utfall, samlet_konfidens).
    """
    if not prediksjoner:
        return "usikkert", Konfidens.lav

    n_for = sum(1 for p in prediksjoner.values() if p.sannsynlighet_for > 0.5)
    n_mot = len(prediksjoner) - n_for
    margin = abs(n_for - n_mot)

    if n_for > n_mot and margin >= 2:
        utfall = "sannsynlig_bifalt"
    elif n_mot > n_for and margin >= 2:
        utfall = "sannsynlig_forkastet"
    else:
        utfall = "usikkert"

    alle_k = [p.konfidens for p in prediksjoner.values()]
    if all(k == Konfidens.hoy for k in alle_k):
        samlet_k = Konfidens.hoy
    elif any(k == Konfidens.hoy for k in alle_k):
        samlet_k = Konfidens.middels
    else:
        samlet_k = Konfidens.lav

    return utfall, samlet_k


def lag1_mindretallsforslag_prediksjoner(
    dok: DokumentStruktur,
    alle_partier: list[str],
) -> list[VoteringPrediksjon]:
    """
    Bygger VoteringPrediksjon for hvert unikt sett av forslagsstillere i mindretallsforslag.

    Partier bak forslaget → FOR (høy konfidens).
    Øvrige partier → MOT (middels konfidens).
    Forslag med identiske forslagsstillere grupperes; tittel angir forslagsnumre og partier.
    """
    # Group by frozenset of proposing party codes, preserving insertion order
    groups: dict[frozenset, list[Forslagspunkt]] = {}
    group_order: list[frozenset] = []

    for fp in dok.mindretallsforslag:
        if fp.fra is None:
            continue
        koder: frozenset[str] = frozenset(normaliser_partiliste(fp.fra.partier))
        if not koder:
            continue
        if koder not in groups:
            groups[koder] = []
            group_order.append(koder)
        groups[koder].append(fp)

    resultat: list[VoteringPrediksjon] = []

    for koder_sett in group_order:
        for_partier = koder_sett
        forslag_liste = groups[koder_sett]

        nrs = [fp.nr for fp in forslag_liste]
        nr_tekst = f"Forslag {nrs[0]}" if len(nrs) == 1 else f"Forslag {nrs[0]}–{nrs[-1]}"

        # Sort party codes in hemicycle order for readable title
        parti_rekke = [p for p in KJERNE_PARTIER if p in for_partier]
        tittel = f"{nr_tekst} ({', '.join(parti_rekke)})"

        pred_dict: dict[str, PartiPrediksjon] = {}
        for parti in alle_partier:
            if parti in for_partier:
                sannsynlighet = _FRAKSJON_KONFIDENS
                konfidens = Konfidens.hoy
                begrunnelse = (
                    f"{parti} er blant forslagsstillerne til {nr_tekst} — "
                    f"forventes å stemme FOR (sannsynlighet_for={sannsynlighet:.0%})."
                )
            else:
                sannsynlighet = 0.15
                konfidens = Konfidens.lav
                begrunnelse = (
                    f"{parti} er ikke forslagsstiller til {nr_tekst} — lav base-rate for støtte til "
                    f"mindretallsforslag (sannsynlighet_for=15%; videresendes til lag 2)."
                )
            pred_dict[parti] = PartiPrediksjon(
                parti=parti,
                sannsynlighet_for=sannsynlighet,
                konfidens=konfidens,
                primaersignal=PrimærSignal.fraksjon_xml,
                begrunnelse=begrunnelse,
                avvik_fra_baseline=False,
            )

        utfall_str, _ = beregn_samlet_utfall(pred_dict)
        forslagstekst = "\n\n".join(fp.tekst.strip() for fp in forslag_liste)

        resultat.append(VoteringPrediksjon(
            votering_type=VoteringType.mindretallsforslag,
            tittel=tittel,
            forslagstekst=forslagstekst,
            forslagsstillere=parti_rekke,
            prediksjoner=list(pred_dict.values()),
            samlet_utfall=SamletUtfall(utfall_str),
        ))

    return resultat
