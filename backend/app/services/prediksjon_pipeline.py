"""
Prediksjonspipeline — orkestrerer lag 1, lag 2, og lag 3.

Flyt:
  1. Sjekk DB-cache (saksprediksjoner-tabellen) — inkl. prompt-versjon.
  2. Hent saksanalyse (kall analyse-pipeline om ikke cachet).
  3. Hent sak-metadata fra Stortinget API.
  4. Hent tilradingsrater og lav-predikabilitet-saksfelter fra DB.
  5. Kjor lag 1 for alle partier.
  6. Identifiser partier med lav konfidens — kjor lag 2.
  7. Identifiser partier fortsatt med lav konfidens — kjor lag 3 (LLM, Sonnet).
  8. Cache resultat i saksprediksjoner.
  9. Returner Saksprediksjon.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import Settings, regjering_partier_for_dato
from app.db.models import DbSaksprediksjon
from app.db.session import get_session_factory
from app.models.prediksjon import (
    Konfidens,
    PartiPrediksjon,
    Saksprediksjon,
    Sakskategori,
    SamletUtfall,
    VoteringPrediksjon,
    VoteringType,
)
from app.services.pipeline import run_pipeline
from app.services.stortinget import StortingetClient
from app.services.stortinget_cache import CachedStortingetClient
from app.steps.prediksjon_lag1 import (
    beregn_samlet_utfall,
    klassifiser_sakskategori,
    lag1_mindretallsforslag_prediksjoner,
    lag1_prediker,
)
from app.steps.prediksjon_lag2 import lag2_mindretallsforslag_prediker, lag2_prediker
from app.steps.prediksjon_lag3 import lag3_mindretallsforslag_prediker, lag3_prediker
from app.utils.partier import KJERNE_PARTIER

log = structlog.get_logger()

_LAG2_TRIGGERE = {Konfidens.lav}
_LAG3_TRIGGERE = {Konfidens.lav}

_PROMPT_VERSJON = "lag1-3/v3"


async def run_prediksjon(
    sak_id: int,
    settings: Settings,
    *,
    force: bool = False,
    stortinget_client: StortingetClient | CachedStortingetClient | None = None,
) -> Saksprediksjon:
    """
    Kjorer prediksjonspipelinen og returnerer Saksprediksjon.

    force=True hopper over cache-oppslag.
    """
    sak_id = int(sak_id)
    factory = get_session_factory()

    if not force and factory:
        cached = await _cache_hent(sak_id, factory, _PROMPT_VERSJON)
        if cached is not None:
            log.info("prediksjon_cache_treff", sak_id=sak_id)
            return cached

    if stortinget_client is None:
        stortinget_client = CachedStortingetClient(settings, factory)

    # ── Steg 1: Hent saksanalyse ──────────────────────────────────────────────
    log.info("prediksjon_steg1_saksanalyse", sak_id=sak_id)
    analyse = await run_pipeline(sak_id, settings, stortinget_client=stortinget_client)

    # ── Steg 2: Hent sak-metadata og dokumentstruktur ─────────────────────────
    log.info("prediksjon_steg2_metadata", sak_id=sak_id)
    sak = await stortinget_client.hent_sak(sak_id)

    from app.services.xml_parser import parse_dokument
    xml_bytes, fmt = await stortinget_client.hent_publikasjon(sak)
    dok = parse_dokument(xml_bytes, pub_id=analyse.pub_id)

    dato = await _hent_sak_votering_dato(sak_id, factory) or date.today()

    saksfelt = await _hent_saksfelt(sak_id, factory) or []

    # ── Steg 3: Last baseline-rater ───────────────────────────────────────────
    tilraading_for_rate = await _hent_tilraading_rater(factory) if factory else {}
    lav_predik_saksfelter = await _hent_lav_predikabilitet(factory) if factory else set()

    rp = regjering_partier_for_dato(dato)
    alle_partier = KJERNE_PARTIER

    # ── Steg 4: Lag 1 ─────────────────────────────────────────────────────────
    log.info("prediksjon_lag1", sak_id=sak_id)
    lag1_resultat = lag1_prediker(
        dok=dok,
        sak=sak,
        alle_partier=alle_partier,
        dato=dato,
        tilraading_for_rate=tilraading_for_rate,
    )

    if not lag1_resultat:
        from app.steps.prediksjon_lag1 import _signal3_tilraading
        lag1_resultat = _signal3_tilraading(sak_id, alle_partier, rp, tilraading_for_rate)

    # ── Steg 5: Lag 2 for partier med lav konfidens ───────────────────────────
    partier_lag2 = [
        p for p, pred in lag1_resultat.items()
        if pred.konfidens in _LAG2_TRIGGERE
    ]

    lag2_resultat: dict[str, PartiPrediksjon] = {}
    if partier_lag2 and factory and saksfelt:
        log.info("prediksjon_lag2", sak_id=sak_id, partier=partier_lag2)
        lag2_resultat = await lag2_prediker(
            sak_id=sak_id,
            saksfelt=saksfelt,
            partier=partier_lag2,
            factory=factory,
            dato=dato,
        )

    endelig_etter_lag2: dict[str, PartiPrediksjon] = {**lag1_resultat, **lag2_resultat}

    # ── Steg 6: Lag 3 for partier fortsatt med lav konfidens ─────────────────
    partier_lag3 = [
        p for p, pred in endelig_etter_lag2.items()
        if pred.konfidens in _LAG3_TRIGGERE
    ]

    lag3_resultat: dict[str, PartiPrediksjon] = {}
    if partier_lag3:
        log.info("prediksjon_lag3", sak_id=sak_id, partier=partier_lag3)
        lag3_resultat = await lag3_prediker(
            sak_id=sak_id,
            analyse=analyse,
            partier=partier_lag3,
            lag1_resultat=lag1_resultat,
            lag2_resultat=lag2_resultat,
            saksfelt=saksfelt,
            rp=rp,
            sakskategori=_hent_sakskategori_str(endelig_etter_lag2, rp, lav_predik_saksfelter, saksfelt),
            settings=settings,
            factory=factory,
        )

    # Slå sammen: lag 3 overstyrer lag 2 overstyrer lag 1
    endelig: dict[str, PartiPrediksjon] = {**endelig_etter_lag2, **lag3_resultat}

    # ── Steg 7: Bygg Saksprediksjon ───────────────────────────────────────────
    sakskategori_str = _hent_sakskategori_str(endelig, rp, lav_predik_saksfelter, saksfelt)
    utfall_str, samlet_konfidens = beregn_samlet_utfall(endelig)

    tilraading_votering = VoteringPrediksjon(
        votering_type=VoteringType.tilrading,
        tittel="Tilrådingen",
        prediksjoner=list(endelig.values()),
        samlet_utfall=SamletUtfall(utfall_str),
    )
    mindretall_voteringer = await _bygg_mindretall_voteringer(
        dok=dok,
        sak_id=sak_id,
        analyse=analyse,
        alle_partier=alle_partier,
        saksfelt=saksfelt,
        dato=dato,
        rp=rp,
        factory=factory,
        settings=settings,
    )
    voteringer = [tilraading_votering] + mindretall_voteringer

    signalkilder = ["lag1"]
    if lag2_resultat:
        signalkilder.append("lag2")
    if lag3_resultat:
        signalkilder.append("lag3")

    prediksjon = Saksprediksjon(
        sak_id=sak_id,
        sakskategori=Sakskategori(sakskategori_str),
        voteringer=voteringer,
        samlet_utfall=SamletUtfall(utfall_str),
        samlet_konfidens=samlet_konfidens,
        signalkilder_brukt=signalkilder,
        baseline_ville_gitt=_naiv_baseline_tekst(alle_partier, rp),
        prompt_versjon=_PROMPT_VERSJON,
    )

    # ── Steg 8: Cache ─────────────────────────────────────────────────────────
    if factory:
        await _cache_sett(prediksjon, factory, permanent=sak.ferdigbehandlet)

    log.info(
        "prediksjon_ferdig",
        sak_id=sak_id,
        kategori=sakskategori_str,
        utfall=utfall_str,
        lag1=len(lag1_resultat) - len(lag2_resultat) - len(lag3_resultat),
        lag2=len(lag2_resultat),
        lag3=len(lag3_resultat),
    )
    return prediksjon


def _hent_sakskategori_str(
    prediksjoner: dict[str, PartiPrediksjon],
    rp: set[str],
    lav_predik: set[str],
    saksfelt: list[str],
) -> str:
    return klassifiser_sakskategori(prediksjoner, rp, lav_predik, saksfelt)


# ── Cache ─────────────────────────────────────────────────────────────────────


async def _cache_hent(
    sak_id: int,
    factory,  # type: ignore[type-arg]
    prompt_versjon: str,
) -> Saksprediksjon | None:
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    async with factory() as session:
        row: DbSaksprediksjon | None = await session.get(DbSaksprediksjon, sak_id)
        if row is None:
            return None
        # Ugyldig hvis prompt-versjon er utdatert
        if row.prompt_versjon != prompt_versjon:
            log.info("prediksjon_cache_versjon_utdatert", sak_id=sak_id,
                     lagret=row.prompt_versjon, forventet=prompt_versjon)
            await session.delete(row)
            await session.commit()
            return None
        row_utloper = row.utloper.replace(tzinfo=None) if row.utloper and row.utloper.tzinfo else row.utloper
        if row_utloper is not None and row_utloper < now:
            await session.delete(row)
            await session.commit()
            return None
        return Saksprediksjon.model_validate(row.prediksjoner_json)


async def _cache_sett(
    prediksjon: Saksprediksjon,
    factory,  # type: ignore[type-arg]
    *,
    permanent: bool,
) -> None:
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    utloper = None if permanent else datetime.fromtimestamp(time.time() + 86_400, tz=timezone.utc).replace(tzinfo=None)
    stmt = (
        pg_insert(DbSaksprediksjon)
        .values(
            sak_id=prediksjon.sak_id,
            prediksjoner_json=prediksjon.model_dump(mode="json"),
            signalkilder=prediksjon.signalkilder_brukt,
            prompt_versjon=prediksjon.prompt_versjon,
            opprettet=now,
            utloper=utloper,
        )
        .on_conflict_do_update(
            index_elements=["sak_id"],
            set_={
                "prediksjoner_json": prediksjon.model_dump(mode="json"),
                "signalkilder": prediksjon.signalkilder_brukt,
                "prompt_versjon": prediksjon.prompt_versjon,
                "utloper": utloper,
            },
        )
    )
    async with factory() as session:
        await session.execute(stmt)
        await session.commit()


# ── DB-hjelpere ───────────────────────────────────────────────────────────────


async def _hent_sak_votering_dato(sak_id: int, factory) -> date | None:  # type: ignore[type-arg]
    if factory is None:
        return None
    async with factory() as session:
        row = await session.execute(
            text("SELECT MAX(dato) FROM voteringer WHERE sak_id = :sid"),
            {"sid": sak_id},
        )
        val = row.scalar()
        return val if isinstance(val, date) else None


async def _hent_saksfelt(sak_id: int, factory) -> list[str]:  # type: ignore[type-arg]
    if factory is None:
        return []
    async with factory() as session:
        row = await session.execute(
            text("""
                SELECT saksfelt FROM voteringer
                WHERE sak_id = :sid AND saksfelt IS NOT NULL
                LIMIT 1
            """),
            {"sid": sak_id},
        )
        val = row.scalar()
        return list(val) if val else []


async def _hent_tilraading_rater(factory) -> dict[str, float]:  # type: ignore[type-arg]
    if factory is None:
        return {}
    async with factory() as session:
        rows = await session.execute(
            text("""
                SELECT parti, andel_for FROM parti_moenster
                WHERE saksfelt = '_total' AND dokumentgruppe = 'tilraading'
            """)
        )
    return {row.parti: float(row.andel_for) for row in rows}


async def _hent_lav_predikabilitet(factory) -> set[str]:  # type: ignore[type-arg]
    return set()


async def _bygg_mindretall_voteringer(
    dok,  # DokumentStruktur — avoid import cycle
    sak_id: int,
    analyse,  # Saksanalyse — avoid import cycle
    alle_partier: list[str],
    saksfelt: list[str],
    dato,  # date | None
    rp: set[str],
    factory,  # type: ignore[type-arg]
    settings: Settings,
) -> list[VoteringPrediksjon]:
    """Orkestrerer lag 1–3 for hvert mindretallsforslag og returnerer VoteringPrediksjon-liste."""
    from app.models.prediksjon import Konfidens as _K

    lag1_voteringer = lag1_mindretallsforslag_prediksjoner(dok, alle_partier)
    resultat: list[VoteringPrediksjon] = []

    for vot in lag1_voteringer:
        for_partier: set[str] = set(vot.forslagsstillere)
        non_proposers = [p for p in alle_partier if p not in for_partier]

        lag1_dict: dict[str, PartiPrediksjon] = {p.parti: p for p in vot.prediksjoner}

        # Lag 2 for non-proposers
        non_proposers_lag2 = [p for p in non_proposers if lag1_dict[p].konfidens == _K.lav]
        lag2_dict: dict[str, PartiPrediksjon] = {}
        if non_proposers_lag2 and factory and saksfelt:
            try:
                lag2_dict = await lag2_mindretallsforslag_prediker(
                    sak_id=sak_id,
                    for_partier=for_partier,
                    non_proposers=non_proposers_lag2,
                    saksfelt=saksfelt,
                    factory=factory,
                )
            except Exception as exc:
                log.warning("mindretall_lag2_feil", sak_id=sak_id, exc=str(exc))

        endelig_lag12: dict[str, PartiPrediksjon] = {**lag1_dict, **lag2_dict}

        # Lag 3 for non-proposers still with lav konfidens
        non_proposers_lag3 = [p for p in non_proposers if endelig_lag12[p].konfidens == _K.lav]
        lag3_dict: dict[str, PartiPrediksjon] = {}
        if non_proposers_lag3 and settings:
            try:
                lag3_dict = await lag3_mindretallsforslag_prediker(
                    sak_id=sak_id,
                    forslag_tittel=vot.tittel,
                    forslagstekst=vot.forslagstekst or "",
                    forslagsstillere=vot.forslagsstillere,
                    non_proposers=non_proposers_lag3,
                    analyse=analyse,
                    lag12_result=endelig_lag12,
                    saksfelt=saksfelt,
                    rp=rp,
                    settings=settings,
                    factory=factory,
                )
            except Exception as exc:
                log.warning("mindretall_lag3_feil", sak_id=sak_id, exc=str(exc))

        endelig: dict[str, PartiPrediksjon] = {**endelig_lag12, **lag3_dict}
        utfall_str, _ = beregn_samlet_utfall(endelig)

        resultat.append(VoteringPrediksjon(
            votering_type=vot.votering_type,
            tittel=vot.tittel,
            forslagstekst=vot.forslagstekst,
            forslagsstillere=vot.forslagsstillere,
            prediksjoner=list(endelig.values()),
            samlet_utfall=SamletUtfall(utfall_str),
        ))

    return resultat


def _naiv_baseline_tekst(alle_partier: list[str], rp: set[str]) -> str:
    for_partier = sorted(rp & set(alle_partier))
    mot_partier = sorted(set(alle_partier) - rp)
    return (
        f"Naiv baseline: {', '.join(for_partier)} FOR tilradingen; "
        f"{', '.join(mot_partier)} MOT."
    )
