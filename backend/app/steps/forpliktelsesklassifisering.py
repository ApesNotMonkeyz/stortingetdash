from __future__ import annotations

import structlog

from app.exceptions import AnalyseFeilet
from app.models.dokument import Forslagspunkt, Forpliktelsesgrad
from app.prompts import forpliktelsesklassifisering as prompt_mod
from app.services.claude import ClaudeClient

log = structlog.get_logger()

_TOOL_NAME = "lever_forpliktelsesklassifisering"

_TOOL: dict = {
    "name": _TOOL_NAME,
    "description": "Lever klassifisering av forpliktelsesgrad for alle forslagspunkter",
    "input_schema": {
        "type": "object",
        "properties": {
            "klassifiseringer": {
                "type": "array",
                "description": "Én klassifisering per forslagspunkt, i samme rekkefølge som input",
                "items": {
                    "type": "object",
                    "properties": {
                        "nr": {
                            "type": "string",
                            "description": "Forslagsnummeret slik det sto i input (f.eks. '1')",
                        },
                        "forpliktelsesgrad": {
                            "type": "string",
                            "enum": [g.value for g in Forpliktelsesgrad],
                        },
                        "begrunnelse": {
                            "type": "string",
                            "description": "Kort begrunnelse basert på nøkkelverbet i teksten",
                        },
                    },
                    "required": ["nr", "forpliktelsesgrad", "begrunnelse"],
                },
            }
        },
        "required": ["klassifiseringer"],
    },
}


async def klassifiser_forpliktelsesgrad(
    forslag: list[Forslagspunkt],
    claude: ClaudeClient,
) -> list[Forslagspunkt]:
    """
    Steg 4: ta inn Forslagspunkt-liste fra XML-parsing og returner samme liste
    med forpliktelsesgrad og begrunnelse_klassifisering utfylt via Claude.

    Tomme lister returneres urørt uten API-kall.
    """
    if not forslag:
        return forslag

    user_msg = prompt_mod.brukermelding(forslag)
    result = await claude.tool_call(
        system=prompt_mod.SYSTEM,
        user=user_msg,
        tool=_TOOL,
        tool_name=_TOOL_NAME,
    )

    by_nr: dict[str, dict] = {str(k["nr"]): k for k in result["klassifiseringer"]}
    log.info(
        "forpliktelsesklassifisering_ok",
        antall=len(forslag),
        klassifisert=len(by_nr),
    )

    oppdaterte: list[Forslagspunkt] = []
    for i, punkt in enumerate(forslag):
        # Prøv nr-oppslag, faller tilbake til posisjonsoppslag (1-indeksert)
        k = by_nr.get(punkt.nr) or by_nr.get(str(i + 1))
        if k is None:
            log.warning("forpliktelsesklassifisering_mangler_nr", nr=punkt.nr)
            oppdaterte.append(punkt)
            continue

        try:
            grad = Forpliktelsesgrad(k["forpliktelsesgrad"])
        except ValueError as exc:
            raise AnalyseFeilet(
                f"Ugyldig forpliktelsesgrad {k['forpliktelsesgrad']!r} for forslag {punkt.nr}"
            ) from exc

        oppdaterte.append(
            punkt.model_copy(update={
                "forpliktelsesgrad": grad,
                "begrunnelse_klassifisering": k["begrunnelse"],
            })
        )
    return oppdaterte
