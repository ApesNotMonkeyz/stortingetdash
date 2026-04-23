"""
Prompt for lag 3 — LLM-assistert sannsynlighetsindikasjon.

Versjonskonstant PREDIKSJON_V1 brukes som cache-nokkel: endre ved prompt-oppdatering.
"""
from __future__ import annotations

from app.models.analyse import Saksanalyse
from app.models.prediksjon import PartiPrediksjon

PREDIKSJON_V1 = "PREDIKSJON_V1"

SYSTEM = """\
<rolle>
Du vurderer sannsynligheten for at norske politiske partier stemmer for komiteens tilrading \
i stortingsvoteringer, basert pa historiske voteringsdata og saksinnhold.

sannsynlighet_for = P(partiet stemmer FOR tilradingen) [0.0-1.0].
Lav verdi (naer 0) betyr partiet forventes a stemme MOT tilradingen.

Du fa r lag 1-2-resultater som kontekst og skal kun vurdere partier med lav konfidens.
Begrunnelsen MA referere til konkrete baseline-tall (sak-ID-er, FOR-rater, n-verdier) \
fra dataene du mottar. Generelle utsagn om partienes ideologi er ikke tilstrekkelig.
</rolle>
"""


_EKSEMPLER = """\
<eksempler>

<eksempel id="1">
<kontekst>
Sak 87341 (proposisjon): Prop. 45 L om endring i arbeidsmiljoeloven.
Sakskategori: koalisjonssak. Regjeringspartier: A.
Lag 1: A=0.10 (middels), alle opp-partier=0.50 (lav) [signal 3 fallback].
Historiske monstre pa saksfelt ["arbeidsliv"]:
  SV: andel_for=0.89, n=156
  R:  andel_for=0.83, n=94
  MDG: andel_for=0.76, n=41
Korrelasjon (SV, R) = 0.94 | (SV, MDG) = 0.88
Partier som trenger vurdering: [SV, R, MDG]
</kontekst>
<output>
SV:  sannsynlighet_for=0.88, konfidens=hoy,
     begrunnelse="SV har historisk FOR-rate pa 89 % pa arbeidsmiljo-saker (n=156, parti_moenster).
     Forslaget styrker arbeidstakernes rettigheter, noe SV konsekvent har stottet."
R:   sannsynlighet_for=0.83, konfidens=middels,
     begrunnelse="R har FOR-rate 83 % pa arbeidsliv (n=94). Hoy stemmekorrelasjon med SV (94 %).
     Middels konfidens fordi n er lavere enn for SV."
MDG: sannsynlighet_for=0.76, konfidens=middels,
     begrunnelse="MDG har FOR-rate 76 % pa arbeidsliv (n=41). Proxy via SV (korrelasjon 88 %).
     Middels konfidens pga lavere n."
</output>
</eksempel>

<eksempel id="2">
<kontekst>
Sak 91204 (representantforslag): Dok 8 om redusert formuesskatt.
Sakskategori: koalisjonssak. Regjeringspartier: A, Sp.
Lag 1: A=0.10 (middels), Sp=0.07 (middels), alle opp=0.50 (lav) [signal 3].
Historiske monstre pa saksfelt ["skatt", "naringsliv"]:
  H:   andel_for=0.31, n=214  (H er opprinnelig for skattekutt men representantforslaget
                                er fra H selv — her er H forslagsstiller)
  FrP: andel_for=0.28, n=187
  KrF: andel_for=0.61, n=89
  V:   andel_for=0.55, n=67
Korrelasjon (H, FrP) = 0.91 | (KrF, V) = 0.79
Partier som trenger vurdering: [H, FrP, KrF, V]
Merk: H er forslagsstiller (lag 1 burde ha fanget dette — men gitt at lag 1 ga lav konfidens,
behandles H her som usikker).
</kontekst>
<output>
H:   sannsynlighet_for=0.08, konfidens=middels,
     begrunnelse="H er forslagsstiller pa dette representantforslaget. Historisk FOR-rate for H pa
     skattesaker er 31 % (n=214) — men det er tilradingsvoteringer generelt. Nar H er forslagsstiller
     pa et kutt-forslag og innstillingen inneholder en mildere versjon, er H typisk MOT tilradingen.
     Middels konfidens (ikke hoy) fordi tilrading-semantikk pa representantforslag er kompleks."
FrP: sannsynlighet_for=0.12, konfidens=middels,
     begrunnelse="FrP har FOR-rate 28 % pa naringsliv/skatt (n=187). Hoy korrelasjon med H (91 %).
     Siden H forventes MOT, er FrP sannsynligvis ogsa MOT tilradingen."
KrF: sannsynlighet_for=0.61, konfidens=lav,
     begrunnelse="KrF har FOR-rate 61 % pa skatt/naringsliv (n=89), klart over 50 %. Lav korrelasjon
     med H/FrP pa denne sakstypen. Lav konfidens fordi KrFs posisjon varierer med saksdetaljer."
V:   sannsynlighet_for=0.55, konfidens=lav,
     begrunnelse="V har FOR-rate 55 % pa naringsliv (n=67). Hoy korrelasjon med KrF (79 %). Usikker
     retning; lav konfidens."
</output>
</eksempel>

</eksempler>
"""


def brukermelding(
    sak_id: int,
    analyse: Saksanalyse,
    partier_trenger_vurdering: list[str],
    rp: set[str],
    sakskategori: str,
    endelig_lag12: dict[str, PartiPrediksjon],
    moenster: dict[str, dict[str, tuple[float, int]]],
    korrelasjoner: dict[tuple[str, str], float],
    saksfelt: list[str],
) -> str:
    saksinfo = _format_saksinfo(sak_id, analyse, rp, sakskategori, saksfelt)
    historikk = _format_historikk(moenster, partier_trenger_vurdering, saksfelt)
    korr_tekst = _format_korrelasjoner(korrelasjoner, partier_trenger_vurdering)
    lag12_tekst = _format_lag12(endelig_lag12, partier_trenger_vurdering)
    trenger_str = ", ".join(partier_trenger_vurdering)

    return f"""\
{_EKSEMPLER}

<oppgave>
Gi sannsynlighetsindikasjon for partiene som mangler tilstrekkelig konfidens etter lag 1-2 (listet nedenfor).
Baser deg pa historiske data og saksinnhold — ikke pa generell partiideologi.
Begrunnelsen MA referere til konkrete tall (FOR-rater, n-verdier, korrelasjonsverdier, sak-ID-er).
</oppgave>

{saksinfo}

{historikk}

{korr_tekst}

{lag12_tekst}

<partier_som_trenger_vurdering>
{trenger_str}
</partier_som_trenger_vurdering>
"""


def _format_saksinfo(
    sak_id: int,
    analyse: Saksanalyse,
    rp: set[str],
    sakskategori: str,
    saksfelt: list[str],
) -> str:
    rp_str = ", ".join(sorted(rp)) if rp else "(ingen registrert)"
    sf_str = ", ".join(saksfelt) if saksfelt else "(ukjent)"

    innhold = ""
    if analyse.innholdsanalyse:
        inn = analyse.innholdsanalyse
        innhold = (
            f"Problemforstaelse: {inn.problemforstaelse}\n"
            f"Losningsforslag: {inn.losningsforslag}\n"
            f"Argumentasjonslinjer: {'; '.join(inn.argumentasjonslinjer[:4])}"
        )
    else:
        innhold = f"Tittel: {analyse.tittel or '(ukjent)'}"

    kontekst = ""
    if analyse.politisk_kontekst and analyse.politisk_kontekst.politiske_dimensjoner:
        dim = analyse.politisk_kontekst.politiske_dimensjoner[0]
        kontekst = f"Politisk akse: {dim.akse} — {dim.plassering} (sikkerhet: {dim.sikkerhet.value})"

    forslag_tekst = ""
    if analyse.forslag:
        forslag_tekst = "Forslagspunkter:\n" + "\n".join(
            f"  {p.nr}. {p.tekst[:200]}" for p in analyse.forslag[:5]
        )

    return f"""\
<saksinfo>
Sak-ID: {sak_id}  |  Sesjon: {analyse.sesjon or 'ukjent'}
Sakskategori: {sakskategori}
Regjeringspartier: {rp_str}
Saksfelt: {sf_str}

{innhold}

{kontekst}

{forslag_tekst}
</saksinfo>"""


def _format_historikk(
    moenster: dict[str, dict[str, tuple[float, int]]],
    partier: list[str],
    saksfelt: list[str],
) -> str:
    if not moenster:
        return "<historikk>\n(Ingen historiske monstre tilgjengelig for disse saksfelene)\n</historikk>"

    linjer = [
        f"Historiske FOR-rater fra parti_moenster (saksfelt: {', '.join(saksfelt) or 'alle'}):"
    ]
    for parti in partier:
        parti_data = moenster.get(parti)
        if not parti_data:
            linjer.append(f"  {parti}: ingen data (n < 5)")
            continue
        total_vektet = sum(andel * n for andel, n in parti_data.values())
        total_n = sum(n for _, n in parti_data.values())
        snitt = total_vektet / total_n if total_n > 0 else 0.0
        detaljer = ", ".join(
            f"{sf}={andel:.0%}(n={n})"
            for sf, (andel, n) in sorted(parti_data.items(), key=lambda x: -x[1][1])[:3]
        )
        linjer.append(f"  {parti}: vektet FOR-rate {snitt:.0%} (totalt n={total_n}) [{detaljer}]")

    return f"<historikk>\n" + "\n".join(linjer) + "\n</historikk>"


def _format_korrelasjoner(
    korrelasjoner: dict[tuple[str, str], float],
    partier: list[str],
) -> str:
    if not korrelasjoner:
        return "<korrelasjoner>\n(Ingen korrelasjonsdata tilgjengelig)\n</korrelasjoner>"

    sett = set(partier)
    linjer = ["Stemmekorrelasjon mellom relevante partier (_total, kun par >= 60%):"]
    sett_par: set[frozenset] = set()
    for (pa, pb), korr in sorted(korrelasjoner.items(), key=lambda x: -x[1]):
        par = frozenset([pa, pb])
        if par in sett_par:
            continue
        if (pa in sett or pb in sett) and korr >= 0.60:
            linjer.append(f"  {pa} <-> {pb}: {korr:.0%}")
            sett_par.add(par)

    if len(linjer) == 1:
        return "<korrelasjoner>\n(Ingen sterke korrelasjoner funnet for disse partiene)\n</korrelasjoner>"
    return "<korrelasjoner>\n" + "\n".join(linjer) + "\n</korrelasjoner>"


def _format_lag12(
    endelig_lag12: dict[str, PartiPrediksjon],
    partier_trenger: list[str],
) -> str:
    trenger_sett = set(partier_trenger)
    linjer_avklart = []
    linjer_usikre = []

    for parti, pred in sorted(endelig_lag12.items()):
        linje = (
            f"  {parti}: sannsynlighet_for={pred.sannsynlighet_for:.0%}, "
            f"konfidens={pred.konfidens.value}, signal={pred.primaersignal.value}"
        )
        if parti in trenger_sett:
            linjer_usikre.append(linje + "  <-- trenger lag 3")
        else:
            linjer_avklart.append(linje)

    tekst = "<lag1_2_prediksjoner>\n"
    if linjer_avklart:
        tekst += "Avklarte partier (for referanse):\n" + "\n".join(linjer_avklart) + "\n"
    if linjer_usikre:
        tekst += "\nPartier med lav konfidens (disse skal vurderes):\n" + "\n".join(linjer_usikre) + "\n"
    tekst += "</lag1_2_prediksjoner>"
    return tekst


# ── Mindretallsforslag lag 3 ──────────────────────────────────────────────────

SYSTEM_MINDRETALL = """\
<rolle>
Du vurderer sannsynligheten for at norske politiske partier stemmer FOR et konkret mindretallsforslag \
i stortingsvoteringer, basert pa historiske voteringsdata, stemmekorrelasjon og forslagstekst.

sannsynlighet_for = P(partiet stemmer FOR dette mindretallsforslaget) [0.0-1.0].
Lav verdi (naer 0) betyr partiet stemmer MOT forslaget.

Viktig: mindretallsforslag er typisk mer ambisiose enn det komiteen flertallet ville vedta.
Base-raten for at et parti utenfor forslagsstillerne stotter et slikt forslag er lav (rundt 0.10–0.20),
med mindre det er sterk politisk alignement eller konkrete historiske presedenser.
Ikke infla prosentene — en estimert for-rate pa 0.25 er realistisk for et naert alliert parti.

Du far lag 1-2-resultater og korrelasjonsdata som kontekst. Vurder kun partier med lav konfidens.
Begrunnelsen MA referere til konkrete tall (korrelasjoner, n-verdier) fra de vedlagte dataene.
Generelle utsagn om partienes ideologi er ikke tilstrekkelig.
</rolle>
"""


def brukermelding_mindretallsforslag(
    sak_id: int,
    analyse: Saksanalyse,
    forslag_tittel: str,
    forslagstekst: str,
    forslagsstillere: list[str],
    partier_trenger_vurdering: list[str],
    rp: set[str],
    saksfelt: list[str],
    endelig_lag12: dict[str, PartiPrediksjon],
    korrelasjoner: dict[tuple[str, str], float],
) -> str:
    rp_str = ", ".join(sorted(rp)) if rp else "(ingen registrert)"
    sf_str = ", ".join(saksfelt) if saksfelt else "(ukjent)"
    fs_str = ", ".join(forslagsstillere)
    trenger_str = ", ".join(partier_trenger_vurdering)

    forslagstekst_trimmed = forslagstekst[:1200] + ("…" if len(forslagstekst) > 1200 else "")

    tittel_sak = analyse.tittel or "(ukjent)"

    korr_tekst = _format_korrelasjoner_mindretall(korrelasjoner, partier_trenger_vurdering, forslagsstillere)
    lag12_tekst = _format_lag12(endelig_lag12, partier_trenger_vurdering)

    return f"""\
<oppgave>
Gi sannsynlighetsindikasjon for partiene som mangler tilstrekkelig konfidens etter lag 1-2
for a stemme FOR mindretallsforslaget beskrevet nedenfor.
Baser deg pa historiske korrelasjoner og forslagsteksten.
Begrunnelsen MA referere til konkrete tall fra de vedlagte dataene.
</oppgave>

<saksinfo>
Sak-ID: {sak_id}  |  Sakstittel: {tittel_sak}
Regjeringspartier: {rp_str}  |  Saksfelt: {sf_str}
</saksinfo>

<mindretallsforslag>
Tittel: {forslag_tittel}
Forslagsstillere: {fs_str}
Tekst:
{forslagstekst_trimmed}
</mindretallsforslag>

{korr_tekst}

{lag12_tekst}

<partier_som_trenger_vurdering>
{trenger_str}
</partier_som_trenger_vurdering>
"""


def _format_korrelasjoner_mindretall(
    korrelasjoner: dict[tuple[str, str], float],
    non_proposers: list[str],
    forslagsstillere: list[str],
) -> str:
    """Formater korrelasjoner mellom ikke-forslagsstillere og forslagsstillerne."""
    if not korrelasjoner:
        return "<korrelasjoner>\n(Ingen korrelasjonsdata tilgjengelig)\n</korrelasjoner>"

    linjer = [f"Stemmekorrelasjon mellom ikke-forslagsstillere og forslagsstillerne ({', '.join(sorted(forslagsstillere))}):"]

    vist: set[str] = set()
    for np in non_proposers:
        korr_for_np: list[str] = []
        for fs in sorted(forslagsstillere):
            k = korrelasjoner.get((np, fs)) or korrelasjoner.get((fs, np))
            if k is not None:
                korr_for_np.append(f"{fs}: {k:.0%}")
        if korr_for_np:
            linjer.append(f"  {np}: {' | '.join(korr_for_np)}")
            vist.add(np)

    if len(linjer) == 1:
        return "<korrelasjoner>\n(Ingen korrelasjonsdata funnet mellom disse partiene)\n</korrelasjoner>"
    return "<korrelasjoner>\n" + "\n".join(linjer) + "\n</korrelasjoner>"
