from __future__ import annotations

import structlog

from app.exceptions import AnalyseFeilet
from app.models.analyse import Innholdsanalyse
from app.models.dokument import DokumentStruktur
from app.prompts import innholdsanalyse as prompt_mod
from app.services.claude import ClaudeClient

log = structlog.get_logger()

_TOOL_NAME = "lever_innholdsanalyse"

# Alle property-navn og enum-verdier er ASCII (Anthropic API-krav).
_TOOL: dict = {
    "name": _TOOL_NAME,
    "description": "Lever strukturert innholdsanalyse av stortingsdokument",
    "input_schema": {
        "type": "object",
        "properties": {
            "problemforstaelse": {
                "type": "string",
                "description": "Hva forslagstillerne beskriver som problemet (2-4 setninger)",
            },
            "losningsforslag": {
                "type": "string",
                "description": "Kort sammendrag av hva som faktisk foreslås gjort (1-3 setninger)",
            },
            "argumentasjonslinjer": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Verdier, hensyn og fakta forslagstillerne bygger på",
                "minItems": 1,
            },
        },
        "required": ["problemforstaelse", "losningsforslag", "argumentasjonslinjer"],
    },
}


async def analyser_innhold(
    dok: DokumentStruktur,
    claude: ClaudeClient,
) -> Innholdsanalyse:
    """
    Steg 5: analyser bakgrunn og forslagstekst, returner strukturert innholdsanalyse.
    """
    user_msg = prompt_mod.brukermelding(dok)
    result = await claude.tool_call(
        system=prompt_mod.SYSTEM,
        user=user_msg,
        tool=_TOOL,
        tool_name=_TOOL_NAME,
    )

    try:
        analyse = Innholdsanalyse.model_validate(result)
    except Exception as exc:
        raise AnalyseFeilet(f"Kunne ikke validere innholdsanalyse-respons: {exc}") from exc

    log.info(
        "innholdsanalyse_ok",
        pub_id=dok.pub_id,
        argumentasjonslinjer=len(analyse.argumentasjonslinjer),
    )
    return analyse
