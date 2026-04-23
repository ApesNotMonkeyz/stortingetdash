from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.exceptions import AnalyseFeilet, DokumentUtilgjengelig, SakIkkeFunnet
from app.models.analyse import Saksanalyse
from app.models.prediksjon import Saksprediksjon
from app.services.pipeline import run_pipeline
from app.services.prediksjon_pipeline import run_prediksjon

router = APIRouter()


@router.get(
    "/analyse/{sak_id}",
    response_model=Saksanalyse,
    summary="Analyser en stortingssak",
    description=(
        "Kjører hele analysepipelinen (steg 1–6) for gitt sak-ID og returnerer "
        "strukturert Saksanalyse-objekt."
    ),
)
async def hent_analyse(
    sak_id: int,
    force: bool = False,
    settings: Settings = Depends(get_settings),
) -> Saksanalyse:
    try:
        return await run_pipeline(sak_id, settings, force=force)
    except SakIkkeFunnet as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DokumentUtilgjengelig as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AnalyseFeilet as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/prediksjon/{sak_id}",
    response_model=Saksprediksjon,
    summary="Sannsynlighetsindikasjon for partienes stemmegivning",
    description=(
        "Kjører prediksjonspipelinen (lag 1–2) for gitt sak-ID og returnerer "
        "Saksprediksjon med sannsynlighetsindikasjon per parti. "
        "Lag 1 er deterministisk (null LLM-kostnad). Lag 2 bruker historiske mønstre fra DB. "
        "Lag 3 (LLM) er ikke implementert ennå."
    ),
)
async def hent_prediksjon(
    sak_id: int,
    force: bool = False,
    settings: Settings = Depends(get_settings),
) -> Saksprediksjon:
    try:
        return await run_prediksjon(sak_id, settings, force=force)
    except SakIkkeFunnet as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DokumentUtilgjengelig as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AnalyseFeilet as exc:
        raise HTTPException(status_code=500, detail=str(exc))
