from __future__ import annotations

import structlog

from app.config import Settings
from app.db.cache import cache_hent, cache_sett, cache_tøm as _cache_tøm  # noqa: F401
from app.exceptions import AnalyseFeilet
from app.models.analyse import Saksanalyse
from app.services.claude import ClaudeClient
from app.services.stortinget import StortingetClient
from app.services.stortinget_cache import CachedStortingetClient
from app.services.xml_parser import parse_dokument
from app.steps.forpliktelsesklassifisering import klassifiser_forpliktelsesgrad
from app.steps.innholdsanalyse import analyser_innhold
from app.steps.politisk_kontekst import analyser_politisk_kontekst

log = structlog.get_logger()

# Re-eksporter cache_tøm slik at eksisterende importeringer ikke brekker
cache_tøm = _cache_tøm


async def run_pipeline(
    sak_id: int | str,
    settings: Settings,
    *,
    force: bool = False,
    stortinget_client: StortingetClient | CachedStortingetClient | None = None,
) -> Saksanalyse:
    """
    Orkestrerer steg 1–6 i sekvens og returnerer et samlet Saksanalyse-objekt.

    Sjekker cache (dict eller DB avhengig av DATABASE_URL) før kjøring.
    Ferdigbehandlede saker caches permanent; andre med 24 timers TTL.
    force=True hopper over cache-oppslag.

    Steg 1: saksmetadata (Stortinget API)
    Steg 2: publikasjonsnedlasting (XML, HTML-fallback)
    Steg 3: strukturell XML-parsing (deterministisk)
    Steg 4: forpliktelsesgrad-klassifisering (LLM)
    Steg 5: innholdsanalyse (LLM)
    Steg 6: politisk kontekst (LLM)
    """
    sak_id = int(sak_id)

    if not force:
        cached = await cache_hent(sak_id)
        if cached is not None:
            log.info("cache_treff", sak_id=sak_id)
            return cached

    if stortinget_client is None:
        from app.db.session import get_session_factory
        stortinget_client = CachedStortingetClient(settings, get_session_factory())
    stortinget = stortinget_client
    claude = ClaudeClient(settings)

    # Steg 1
    log.info("pipeline_steg1_start", sak_id=sak_id)
    sak = await stortinget.hent_sak(sak_id)
    log.info("pipeline_steg1_ok", sak_id=sak.id, tittel=sak.tittel[:60])

    # Steg 2
    log.info("pipeline_steg2_start", sak_id=sak.id)
    xml_bytes, fmt = await stortinget.hent_publikasjon(sak)
    if fmt != "xml":
        raise AnalyseFeilet(
            f"Sak {sak.id}: publikasjonen er ikke tilgjengelig som gyldig XML "
            f"(format={fmt!r}). Kan ikke analyseres."
        )

    # Steg 3
    pub_id = sak.analyse_publikasjon.eksport_id if sak.analyse_publikasjon else ""
    log.info("pipeline_steg3_start", sak_id=sak.id, pub_id=pub_id)
    dok = parse_dokument(xml_bytes, pub_id=pub_id)
    log.info(
        "pipeline_steg3_ok",
        dok_type=dok.dok_type,
        seksjoner=len(dok.seksjoner),
        forslag=len(dok.mindretallsforslag),
    )

    # Steg 4
    log.info("pipeline_steg4_start", sak_id=sak.id)
    forslag = await klassifiser_forpliktelsesgrad(dok.mindretallsforslag, claude)
    log.info("pipeline_steg4_ok", klassifisert=len(forslag))

    # Steg 5
    log.info("pipeline_steg5_start", sak_id=sak.id)
    innhold = await analyser_innhold(dok, claude)
    log.info("pipeline_steg5_ok", sak_id=sak.id)

    # Steg 6
    log.info("pipeline_steg6_start", sak_id=sak.id)
    kontekst = await analyser_politisk_kontekst(dok, forslag, claude)
    log.info("pipeline_steg6_ok", sak_id=sak.id)

    analyse = Saksanalyse(
        sak_id=sak.id,
        pub_id=pub_id,
        dok_type=dok.dok_type,
        tittel=dok.tittel or sak.tittel,
        sesjon=dok.sesjon or sak.sak_sesjon,
        forslag=forslag,
        innholdsanalyse=innhold,
        politisk_kontekst=kontekst,
    )

    await cache_sett(sak.id, analyse, permanent=sak.ferdigbehandlet)
    return analyse
