from __future__ import annotations

import structlog

from app.exceptions import AnalyseFeilet
from app.models.analyse import (
    KoblingEksisterendePolitikk,
    KoblingType,
    PolitiskDimensjon,
    PolitiskKontekst,
    Sikkerhetsnivaa,
)
from app.models.dokument import DokumentStruktur, Forslagspunkt
from app.prompts import politisk_kontekst as prompt_mod
from app.services.claude import ClaudeClient

log = structlog.get_logger()

_TOOL_NAME = "lever_politisk_kontekst"

# Alle enum-verdier er ASCII (Anthropic API-krav).
_SIKKERHET_ENUM = [n.value for n in Sikkerhetsnivaa]   # ["hoy", "middels", "lav"]
_KOBLING_ENUM = [k.value for k in KoblingType]          # ["reversering", ...]

_TOOL: dict = {
    "name": _TOOL_NAME,
    "description": "Lever analyse av politisk kontekst og dimensjoner for et stortingsforslag",
    "input_schema": {
        "type": "object",
        "properties": {
            "politiske_dimensjoner": {
                "type": "array",
                "description": "Relevante politiske dimensjoner identifisert i teksten",
                "items": {
                    "type": "object",
                    "properties": {
                        "akse": {
                            "type": "string",
                            "description": "Navn på aksen, f.eks. 'marked/stat', 'sentrum/periferi'",
                        },
                        "plassering": {
                            "type": "string",
                            "description": "Forslagets plassering på denne aksen",
                        },
                        "sikkerhet": {
                            "type": "string",
                            "enum": _SIKKERHET_ENUM,
                            "description": "hoy=høy, middels=middels, lav=lav",
                        },
                        "begrunnelse": {
                            "type": "string",
                            "description": "Kortfattet begrunnelse forankret i dokumentteksten",
                        },
                    },
                    "required": ["akse", "plassering", "sikkerhet", "begrunnelse"],
                },
            },
            "kobling_eksisterende_politikk": {
                "type": "object",
                "description": "Hvordan forslaget forholder seg til gjeldende politikk",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": _KOBLING_ENUM,
                        "description": (
                            "reversering=bryter med, opptrapping=bygger videre på, "
                            "nytt=ingen klar forgjenger, videroforing=viderefører eksisterende"
                        ),
                    },
                    "sikkerhet": {
                        "type": "string",
                        "enum": _SIKKERHET_ENUM,
                    },
                    "begrunnelse": {
                        "type": "string",
                        "description": "Hva i dokumentet som begrunner koblingen",
                    },
                },
                "required": ["type", "sikkerhet", "begrunnelse"],
            },
        },
        "required": ["politiske_dimensjoner", "kobling_eksisterende_politikk"],
    },
}


async def analyser_politisk_kontekst(
    dok: DokumentStruktur,
    forslag: list[Forslagspunkt],
    claude: ClaudeClient,
) -> PolitiskKontekst:
    """
    Steg 6: analyser politiske dimensjoner og kobling til eksisterende politikk.

    Alle tolkningsfelter har sikkerhet (hoy/middels/lav) og begrunnelse.
    """
    user_msg = prompt_mod.brukermelding(dok, forslag)
    result = await claude.tool_call(
        system=prompt_mod.SYSTEM,
        user=user_msg,
        tool=_TOOL,
        tool_name=_TOOL_NAME,
    )

    try:
        dimensjoner = [
            PolitiskDimensjon.model_validate(d)
            for d in result.get("politiske_dimensjoner", [])
        ]
        kobling_raw = result.get("kobling_eksisterende_politikk")
        kobling = KoblingEksisterendePolitikk.model_validate(kobling_raw) if kobling_raw else None
    except Exception as exc:
        raise AnalyseFeilet(f"Kunne ikke validere politisk-kontekst-respons: {exc}") from exc

    log.info(
        "politisk_kontekst_ok",
        pub_id=dok.pub_id,
        dimensjoner=len(dimensjoner),
        kobling=kobling.type.value if kobling else None,
    )
    return PolitiskKontekst(
        politiske_dimensjoner=dimensjoner,
        kobling_eksisterende_politikk=kobling,
    )
