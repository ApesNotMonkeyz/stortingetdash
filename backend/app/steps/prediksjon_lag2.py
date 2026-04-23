"""
Lag 2 — historisk mønstermatching (database-oppslag, null LLM-kostnad).

For partier der lag 1 ikke gir tilstrekkelig konfidens:
  1. Slå opp aggregerte mønstre (parti_moenster) for overlappende saksfelt.
  2. Beregn vektet sannsynlighet_for (vektet etter antall voteringer per saksfelt).
  3. Supplement med parti-par-korrelasjon (beregning 5) for partier med lite data.
  4. Krav: n ≥ 5 lignende saker. Ellers: lav konfidens.
"""
from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.prediksjon import Konfidens, PartiPrediksjon, PrimærSignal

log = structlog.get_logger()

_MIN_N = 5
_N_HOY = 30
_N_MIDDELS = 10


def _konfidens_fra_n(n: int) -> Konfidens:
    if n >= _N_HOY:
        return Konfidens.hoy
    if n >= _N_MIDDELS:
        return Konfidens.middels
    return Konfidens.lav


def _vektet_andel(
    moenster: dict[str, tuple[float, int]],
) -> tuple[float, int, list[str]]:
    """
    Vektet gjennomsnitt av FOR-andel på tvers av saksfelter.

    Returnerer (andel_for, total_n, saksfelter_sortert_etter_n).
    """
    total_vektet = sum(andel * n for andel, n in moenster.values())
    total_n = sum(n for _, n in moenster.values())
    saksfelter = sorted(moenster.keys(), key=lambda sf: -moenster[sf][1])
    andel = total_vektet / total_n if total_n > 0 else 0.5
    return andel, total_n, saksfelter


async def lag2_prediker(
    sak_id: int,
    saksfelt: list[str],
    partier: list[str],
    factory: async_sessionmaker,
    dato: date | None = None,
) -> dict[str, PartiPrediksjon]:
    """
    Kjører lag 2 og returnerer PartiPrediksjon for de angitte partiene.

    sak_id: Kun til logging.
    saksfelt: Saksfelter fra saken — brukes til overlapping-søk.
    partier: Partier som trenger lag 2-indikasjon.
    factory: Async DB session factory.
    dato: For evt. fremtidig dato-avhengig logikk.
    """
    if not saksfelt or not partier:
        return {}

    alle_moenster = await _hent_parti_moenster(factory, saksfelt, partier)
    korrelasjoner = await _hent_korrelasjoner(factory, partier)

    resultat: dict[str, PartiPrediksjon] = {}

    for parti in partier:
        parti_data = alle_moenster.get(parti, {})

        if parti_data:
            andel, total_n, saksfelter_brukt = _vektet_andel(parti_data)
            sf_str = ", ".join(saksfelter_brukt[:3])
            begrunnelse = (
                f"Historisk FOR-andel for {parti} over saksfelt [{sf_str}]: "
                f"{andel:.1%} (n={total_n} voteringer, beregning 1)."
            )
            korr_tekst = _korrelasjon_supplement(parti, korrelasjoner, alle_moenster)
            if korr_tekst:
                begrunnelse += " " + korr_tekst

            resultat[parti] = PartiPrediksjon(
                parti=parti,
                sannsynlighet_for=andel,
                konfidens=_konfidens_fra_n(total_n),
                primaersignal=PrimærSignal.historisk_moenster,
                begrunnelse=begrunnelse,
            )

        else:
            proxy = _finn_proxy(parti, korrelasjoner, alle_moenster)
            if proxy:
                proxy_parti, korr, proxy_andel, proxy_n = proxy
                begrunnelse = (
                    f"Ingen direkte historikk for {parti} på disse saksfelene. "
                    f"Proxy via {proxy_parti} (korrelasjon {korr:.0%}): "
                    f"FOR-andel {proxy_andel:.1%} (n={proxy_n})."
                )
                resultat[parti] = PartiPrediksjon(
                    parti=parti,
                    sannsynlighet_for=proxy_andel,
                    konfidens=Konfidens.lav,
                    primaersignal=PrimærSignal.historisk_moenster,
                    begrunnelse=begrunnelse,
                )
            else:
                resultat[parti] = PartiPrediksjon(
                    parti=parti,
                    sannsynlighet_for=0.5,
                    konfidens=Konfidens.lav,
                    primaersignal=PrimærSignal.ikke_tilgjengelig,
                    begrunnelse=(
                        f"Utilstrekkelig historisk data for {parti} på disse "
                        f"saksfelene (n < {_MIN_N}). Lag 3 anbefales."
                    ),
                )

    log.debug("lag2_ferdig", sak_id=sak_id, partier=len(resultat))
    return resultat


async def _hent_parti_moenster(
    factory: async_sessionmaker,
    saksfelt: list[str],
    partier: list[str],
) -> dict[str, dict[str, tuple[float, int]]]:
    """Henter {parti: {saksfelt: (andel_for, n)}} fra parti_moenster."""
    async with factory() as session:
        rows = await session.execute(
            text("""
                SELECT parti, saksfelt, andel_for, antall_voteringer
                FROM parti_moenster
                WHERE saksfelt = ANY(:sf)
                AND dokumentgruppe = ''
                AND antall_voteringer >= :min_n
                AND parti = ANY(:partier)
            """),
            {"sf": saksfelt, "min_n": _MIN_N, "partier": partier},
        )

    data: dict[str, dict[str, tuple[float, int]]] = {}
    for row in rows:
        data.setdefault(row.parti, {})[row.saksfelt] = (
            float(row.andel_for),
            int(row.antall_voteringer),
        )
    return data


async def _hent_korrelasjoner(
    factory: async_sessionmaker,
    partier: list[str],
) -> dict[tuple[str, str], float]:
    """Henter parti-par-korrelasjoner (_total) for de angitte partiene."""
    async with factory() as session:
        rows = await session.execute(
            text("""
                SELECT parti_a, parti_b, andel_lik_stemme
                FROM parti_korrelasjon
                WHERE saksfelt = '_total'
                AND (parti_a = ANY(:p) OR parti_b = ANY(:p))
                AND antall_voteringer >= :min_n
            """),
            {"p": partier, "min_n": _MIN_N},
        )

    korr: dict[tuple[str, str], float] = {}
    for row in rows:
        v = float(row.andel_lik_stemme)
        korr[(row.parti_a, row.parti_b)] = v
        korr[(row.parti_b, row.parti_a)] = v
    return korr


def _korrelasjon_supplement(
    parti: str,
    korrelasjoner: dict[tuple[str, str], float],
    alle_moenster: dict[str, dict[str, tuple[float, int]]],
) -> str:
    """Returnerer tekstlig supplement med sterke korrelasjonspartnere (≥70%)."""
    beste = [
        (pb if pa == parti else pa, k)
        for (pa, pb), k in korrelasjoner.items()
        if (pa == parti or pb == parti) and (pb if pa == parti else pa) in alle_moenster and k >= 0.70
    ]
    beste.sort(key=lambda x: -x[1])
    if not beste:
        return ""
    tekst = ", ".join(f"{p} ({k:.0%})" for p, k in beste[:3])
    return f"Høy stemmekorrelasjon med: {tekst}."


def _finn_proxy(
    parti: str,
    korrelasjoner: dict[tuple[str, str], float],
    alle_moenster: dict[str, dict[str, tuple[float, int]]],
) -> tuple[str, float, float, int] | None:
    """Finner beste proxy-parti med data og høy korrelasjon."""
    beste: tuple[str, float, float, int] | None = None
    beste_korr = 0.0

    for (pa, pb), korr in korrelasjoner.items():
        partner = pb if pa == parti else (pa if pb == parti else None)
        if not partner or partner not in alle_moenster or korr <= beste_korr:
            continue
        andel, total_n, _ = _vektet_andel(alle_moenster[partner])
        if total_n >= _MIN_N:
            beste_korr = korr
            beste = (partner, korr, andel, total_n)

    return beste


async def lag2_mindretallsforslag_prediker(
    sak_id: int,
    for_partier: set[str],
    non_proposers: list[str],
    saksfelt: list[str],
    factory: async_sessionmaker,
) -> dict[str, PartiPrediksjon]:
    """
    Lag 2 for mindretallsforslag: korrelasjon mellom ikke-forslagsstillere og forslagsstillerne.

    Base-rate for støtte til mindretallsforslag er lav (~0.15); høy korrelasjon løfter noe.
    Maks konfidens: middels (n >= _MIN_N * antall_forslagsstillere).
    """
    if not factory or not non_proposers or not for_partier:
        return {}

    alle_relevante = list(set(non_proposers) | for_partier)
    korr_data = await _hent_korrelasjoner_mindretall(factory, alle_relevante, saksfelt)

    resultat: dict[str, PartiPrediksjon] = {}
    for_partier_str = ", ".join(sorted(for_partier))

    for parti in non_proposers:
        korr_med_proposers: list[float] = []
        total_n = 0
        korr_detaljer: list[str] = []

        for fp in sorted(for_partier):
            entry = korr_data.get((parti, fp)) or korr_data.get((fp, parti))
            if entry:
                korr, n = entry
                korr_med_proposers.append(korr)
                total_n += n
                korr_detaljer.append(f"{fp}: {korr:.0%}(n={n})")

        if not korr_med_proposers:
            resultat[parti] = PartiPrediksjon(
                parti=parti,
                sannsynlighet_for=0.15,
                konfidens=Konfidens.lav,
                primaersignal=PrimærSignal.ikke_tilgjengelig,
                begrunnelse=(
                    f"Ingen korrelasjonsdata for {parti} mot forslagsstillerne "
                    f"({for_partier_str}) — videresendes til lag 3."
                ),
            )
            continue

        avg_korr = sum(korr_med_proposers) / len(korr_med_proposers)
        sannsynlighet = _korr_til_sannsynlighet_mindretall(avg_korr)
        n_terskel = _MIN_N * max(1, len(for_partier))
        konfidens = Konfidens.middels if total_n >= n_terskel else Konfidens.lav
        detaljer_str = " | ".join(korr_detaljer)

        begrunnelse = (
            f"Stemmekorrelasjon mellom {parti} og forslagsstillerne ({for_partier_str}): "
            f"snitt {avg_korr:.0%} [{detaljer_str}] (n_total={total_n}). "
            f"Estimert FOR-sannsynlighet: {sannsynlighet:.0%} "
            f"({'middels' if konfidens == Konfidens.middels else 'lav'} konfidens)."
        )

        resultat[parti] = PartiPrediksjon(
            parti=parti,
            sannsynlighet_for=sannsynlighet,
            konfidens=konfidens,
            primaersignal=PrimærSignal.historisk_moenster,
            begrunnelse=begrunnelse,
        )

    log.debug("lag2_mindretall_ferdig", sak_id=sak_id, n_partier=len(resultat))
    return resultat


def _korr_til_sannsynlighet_mindretall(avg_korr: float) -> float:
    """Mapper gjennomsnittlig stemmekorrelasjon med forslagsstillerne til sannsynlighet FOR mindretallsforslag.
    Base-rate er lav — minoritetsforslag er typisk mer ambisiøse enn flertallet vil godta."""
    if avg_korr >= 0.75:
        return 0.45
    if avg_korr >= 0.60:
        return 0.30
    if avg_korr >= 0.45:
        return 0.20
    return 0.10


async def _hent_korrelasjoner_mindretall(
    factory: async_sessionmaker,
    partier: list[str],
    saksfelt: list[str],
) -> dict[tuple[str, str], tuple[float, int]]:
    """Henter beste korrelasjon per parti-par. Saksfelt-spesifikt foretrekkes over _total."""
    saksfelter_inkl_total = list(set(saksfelt)) + ["_total"]
    async with factory() as session:
        rows = await session.execute(
            text("""
                SELECT parti_a, parti_b, saksfelt, andel_lik_stemme, antall_voteringer
                FROM parti_korrelasjon
                WHERE saksfelt = ANY(:sf)
                  AND parti_a = ANY(:p)
                  AND parti_b = ANY(:p)
                  AND antall_voteringer >= :min_n
                ORDER BY
                  CASE WHEN saksfelt != '_total' THEN 0 ELSE 1 END,
                  antall_voteringer DESC
            """),
            {"sf": saksfelter_inkl_total, "p": partier, "min_n": _MIN_N},
        )
    result: dict[tuple[str, str], tuple[float, int]] = {}
    for row in rows:
        key = (row.parti_a, row.parti_b)
        rev = (row.parti_b, row.parti_a)
        if key not in result:
            v = (float(row.andel_lik_stemme), int(row.antall_voteringer))
            result[key] = v
            result[rev] = v
    return result
