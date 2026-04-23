"""
Lag 3 — LLM-assistert sannsynlighetsindikasjon (claude-sonnet-4-6).

Kalles nar lag 1-2 ikke gir tilstrekkelig konfidens for ett eller flere partier.
Input: saksanalyse, historiske monstre fra DB, lag 1-2 resultater.
Output: PartiPrediksjon per lav-konfidens parti.

Begrunnelsen MÅ referere til konkrete historiske data (sak-ID-er, FOR-rater, n-verdier).
"""
from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import text

from app.config import Settings
from app.exceptions import AnalyseFeilet
from app.models.analyse import Saksanalyse
from app.models.prediksjon import Konfidens, PartiPrediksjon, PrimærSignal
from app.prompts import prediksjon as prompt_mod
from app.services.claude import ClaudeClient

log = structlog.get_logger()

_SONNET = "claude-sonnet-4-6"
_MIN_N = 5
_TOOL_NAME = "lever_prediksjon"

_TOOL: dict = {
    "name": _TOOL_NAME,
    "description": "Lever sannsynlighetsindikasjon for partier med lav konfidens",
    "input_schema": {
        "type": "object",
        "properties": {
            "prediksjoner": {
                "type": "array",
                "description": "En prediksjon per parti i listen",
                "items": {
                    "type": "object",
                    "properties": {
                        "parti": {
                            "type": "string",
                            "description": "Partikode, f.eks. 'H', 'FrP', 'SV'",
                        },
                        "sannsynlighet_for": {
                            "type": "number",
                            "description": "P(partiet stemmer FOR tilradingen) [0.0-1.0]",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "konfidens": {
                            "type": "string",
                            "enum": ["hoy", "middels", "lav"],
                            "description": "hoy: n>=30 og tydelig signal, middels: n>=10 eller god proxy, lav: lite data",
                        },
                        "begrunnelse": {
                            "type": "string",
                            "description": (
                                "Begrunnelse som MÅ referere til konkrete tall "
                                "(FOR-rater, n-verdier, korrelasjonsverdier fra historikk-seksjonen) "
                                "eller konkrete sak-ID-er."
                            ),
                        },
                        "historiske_saker": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Sak-ID-er for refererte historiske saker (kan vaere tom)",
                        },
                    },
                    "required": ["parti", "sannsynlighet_for", "konfidens", "begrunnelse"],
                },
            }
        },
        "required": ["prediksjoner"],
    },
}


async def lag3_prediker(
    sak_id: int,
    analyse: Saksanalyse,
    partier: list[str],
    lag1_resultat: dict[str, PartiPrediksjon],
    lag2_resultat: dict[str, PartiPrediksjon],
    saksfelt: list[str],
    rp: set[str],
    sakskategori: str,
    settings: Settings,
    factory=None,  # type: ignore[type-arg]
) -> dict[str, PartiPrediksjon]:
    """
    Kjorer lag 3 for partier med lav konfidens etter lag 1-2.

    Henter historiske monstre fra DB hvis factory er tilgjengelig.
    Returnerer PartiPrediksjon per parti i 'partier'-listen.
    """
    if not partier:
        return {}

    moenster: dict[str, dict[str, tuple[float, int]]] = {}
    korrelasjoner: dict[tuple[str, str], float] = {}
    if factory is not None and saksfelt:
        moenster = await _hent_moenster(factory, saksfelt, partier)
        korrelasjoner = await _hent_korrelasjoner(factory, partier)

    endelig_lag12: dict[str, PartiPrediksjon] = {**lag1_resultat, **lag2_resultat}

    user_msg = prompt_mod.brukermelding(
        sak_id=sak_id,
        analyse=analyse,
        partier_trenger_vurdering=partier,
        rp=rp,
        sakskategori=sakskategori,
        endelig_lag12=endelig_lag12,
        moenster=moenster,
        korrelasjoner=korrelasjoner,
        saksfelt=saksfelt,
    )

    claude = ClaudeClient(settings)
    try:
        raw = await claude.tool_call(
            system=prompt_mod.SYSTEM,
            user=user_msg,
            tool=_TOOL,
            tool_name=_TOOL_NAME,
            model=_SONNET,
        )
    except Exception as exc:
        raise AnalyseFeilet(
            f"Lag 3 LLM-kall feilet for sak {sak_id}: {exc}"
        ) from exc

    resultat: dict[str, PartiPrediksjon] = {}
    expected = set(partier)
    for item in raw.get("prediksjoner", []):
        p = str(item.get("parti", ""))
        if p not in expected:
            log.warning("lag3_ukjent_parti", parti=p, sak_id=sak_id)
            continue
        try:
            k = Konfidens(item["konfidens"])
        except (KeyError, ValueError):
            k = Konfidens.lav

        resultat[p] = PartiPrediksjon(
            parti=p,
            sannsynlighet_for=float(item["sannsynlighet_for"]),
            konfidens=k,
            primaersignal=PrimærSignal.llm_analyse,
            begrunnelse=item.get("begrunnelse", ""),
            historiske_saker=[int(x) for x in item.get("historiske_saker", [])],
        )

    # Fallback for partier som LLM ikke besvarte
    for p in expected:
        if p not in resultat:
            log.warning("lag3_mangler_parti_svar", parti=p, sak_id=sak_id)
            resultat[p] = PartiPrediksjon(
                parti=p,
                sannsynlighet_for=0.5,
                konfidens=Konfidens.lav,
                primaersignal=PrimærSignal.ikke_tilgjengelig,
                begrunnelse=f"Lag 3 returnerte ikke vurdering for {p}.",
            )

    log.info("lag3_ferdig", sak_id=sak_id, n_partier=len(resultat))
    return resultat


# ── DB-hjelpere ───────────────────────────────────────────────────────────────


async def _hent_moenster(
    factory,  # type: ignore[type-arg]
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
    factory,  # type: ignore[type-arg]
    partier: list[str],
) -> dict[tuple[str, str], float]:
    """Henter parti-par-korrelasjoner (_total) for angitte partier."""
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


_TOOL_MINDRETALL: dict = {
    "name": "lever_prediksjon_mindretall",
    "description": "Lever sannsynlighetsindikasjon for partier som vurderes FOR mindretallsforslaget",
    "input_schema": {
        "type": "object",
        "properties": {
            "prediksjoner": {
                "type": "array",
                "description": "En prediksjon per parti i listen",
                "items": {
                    "type": "object",
                    "properties": {
                        "parti": {"type": "string"},
                        "sannsynlighet_for": {
                            "type": "number",
                            "description": "P(partiet stemmer FOR dette mindretallsforslaget) [0.0-1.0]",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "konfidens": {
                            "type": "string",
                            "enum": ["hoy", "middels", "lav"],
                        },
                        "begrunnelse": {
                            "type": "string",
                            "description": (
                                "Begrunnelse som MA referere til korrelasjonsdata eller "
                                "andre konkrete data fra konteksten. "
                                "Ikke generaliser om partienes ideologi uten datatilknytning."
                            ),
                        },
                        "historiske_saker": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Sak-ID-er for refererte historiske saker (kan vaere tom)",
                        },
                    },
                    "required": ["parti", "sannsynlighet_for", "konfidens", "begrunnelse"],
                },
            }
        },
        "required": ["prediksjoner"],
    },
}


async def lag3_mindretallsforslag_prediker(
    sak_id: int,
    forslag_tittel: str,
    forslagstekst: str,
    forslagsstillere: list[str],
    non_proposers: list[str],
    analyse: Saksanalyse,
    lag12_result: dict[str, PartiPrediksjon],
    saksfelt: list[str],
    rp: set[str],
    settings: Settings,
    factory=None,  # type: ignore[type-arg]
) -> dict[str, PartiPrediksjon]:
    """
    Lag 3 for mindretallsforslag: LLM-analyse for partier med lav konfidens.

    Bruker forslagstekst og korrelasjonsdata som kontekst.
    """
    if not non_proposers:
        return {}

    korrelasjoner: dict[tuple[str, str], float] = {}
    if factory is not None and saksfelt:
        alle_relevante = list(set(non_proposers) | set(forslagsstillere))
        from app.steps.prediksjon_lag2 import _hent_korrelasjoner_mindretall
        korr_data = await _hent_korrelasjoner_mindretall(factory, alle_relevante, saksfelt)
        # Convert to flat dict for prompt formatting
        sett_par: set[frozenset] = set()
        for (pa, pb), (v, _n) in korr_data.items():
            par = frozenset([pa, pb])
            if par not in sett_par:
                korrelasjoner[(pa, pb)] = v
                sett_par.add(par)

    user_msg = prompt_mod.brukermelding_mindretallsforslag(
        sak_id=sak_id,
        analyse=analyse,
        forslag_tittel=forslag_tittel,
        forslagstekst=forslagstekst,
        forslagsstillere=forslagsstillere,
        partier_trenger_vurdering=non_proposers,
        rp=rp,
        saksfelt=saksfelt,
        endelig_lag12=lag12_result,
        korrelasjoner=korrelasjoner,
    )

    claude = ClaudeClient(settings)
    tool_name = "lever_prediksjon_mindretall"
    try:
        raw = await claude.tool_call(
            system=prompt_mod.SYSTEM_MINDRETALL,
            user=user_msg,
            tool=_TOOL_MINDRETALL,
            tool_name=tool_name,
            model=_SONNET,
        )
    except Exception as exc:
        raise AnalyseFeilet(
            f"Lag 3 mindretallsforslag LLM-kall feilet for sak {sak_id}: {exc}"
        ) from exc

    resultat: dict[str, PartiPrediksjon] = {}
    expected = set(non_proposers)
    for item in raw.get("prediksjoner", []):
        p = str(item.get("parti", ""))
        if p not in expected:
            log.warning("lag3_mindretall_ukjent_parti", parti=p, sak_id=sak_id)
            continue
        try:
            k = Konfidens(item["konfidens"])
        except (KeyError, ValueError):
            k = Konfidens.lav
        resultat[p] = PartiPrediksjon(
            parti=p,
            sannsynlighet_for=float(item["sannsynlighet_for"]),
            konfidens=k,
            primaersignal=PrimærSignal.llm_analyse,
            begrunnelse=item.get("begrunnelse", ""),
            historiske_saker=[int(x) for x in item.get("historiske_saker", [])],
        )

    for p in expected:
        if p not in resultat:
            log.warning("lag3_mindretall_mangler_parti", parti=p, sak_id=sak_id)
            resultat[p] = PartiPrediksjon(
                parti=p,
                sannsynlighet_for=0.15,
                konfidens=Konfidens.lav,
                primaersignal=PrimærSignal.ikke_tilgjengelig,
                begrunnelse=f"Lag 3 returnerte ikke vurdering for {p} på mindretallsforslag.",
            )

    log.info("lag3_mindretall_ferdig", sak_id=sak_id, n_partier=len(resultat))
    return resultat
