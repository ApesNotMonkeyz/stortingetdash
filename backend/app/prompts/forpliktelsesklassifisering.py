from __future__ import annotations

from app.models.dokument import Forslagspunkt

FORPLIKTELSESKLASSIFISERING_V1 = "FORPLIKTELSESKLASSIFISERING_V1"

SYSTEM = """\
<rolle>
Du klassifiserer forpliktelsesgrad i forslag til stortingsvedtak.
</rolle>

<forpliktelsesgrader>
- utrede: be om utredning eller rapport. Ingen forpliktelse til konkret handling.
- vurdere: be regjeringen vurdere et tiltak. Kan konkludere uten å gjennomføre noe.
- legge_frem: krever at regjeringen leverer noe konkret til Stortinget (f.eks. lovforslag, stortingsmelding).
- komme_tilbake: krever at regjeringen returnerer til Stortinget for ny behandling.
- sikre: forventer et bestemt resultat, men med metodefrihet. Verbformuleringer som "sikre", "sørge for".
- gjennomfore: pålegger konkret handling. Verbformuleringer som "gjennomføre", "innføre", "etablere", "opprette".
</forpliktelsesgrader>\
"""


def brukermelding(forslag: list[Forslagspunkt]) -> str:
    punkter_tekst = "\n".join(
        f'Forslag {p.nr}: "{p.tekst}"' for p in forslag
    )
    return f"""\
<eksempler>
Tekst: "Stortinget ber regjeringen utrede mulighetene for å etablere en nasjonal digital infrastruktur."
Forpliktelsesgrad: utrede
Begrunnelse: Nøkkelverbet er "utrede" — forslaget ber om en undersøkelse, ingen forpliktelse til handling.

Tekst: "Stortinget ber regjeringen vurdere å innføre krav om obligatorisk merking av matvarer."
Forpliktelsesgrad: vurdere
Begrunnelse: Nøkkelverbet er "vurdere" — regjeringen kan konkludere med at krav ikke bør innføres.

Tekst: "Stortinget ber regjeringen legge frem en stortingsmelding om nasjonal produktivitetspolitikk."
Forpliktelsesgrad: legge_frem
Begrunnelse: Nøkkelverbet er "legge frem" — krever en konkret leveranse (stortingsmelding) til Stortinget.

Tekst: "Stortinget ber regjeringen komme tilbake til Stortinget med en helhetlig plan for …"
Forpliktelsesgrad: komme_tilbake
Begrunnelse: Nøkkelverbet er "komme tilbake" — krever retur til Stortinget for ny behandling.

Tekst: "Stortinget ber regjeringen sikre at alle kommuner har tilgang til fullverdig bredbånd innen 2026."
Forpliktelsesgrad: sikre
Begrunnelse: Nøkkelverbet er "sikre" — forventer et bestemt resultat, men metodefrihet er til stede.

Tekst: "Stortinget ber regjeringen gjennomføre en nasjonal satsing på videreutdanning innen 2027."
Forpliktelsesgrad: gjennomfore
Begrunnelse: Nøkkelverbet er "gjennomføre" med frist — pålegger konkret handling.
</eksempler>

<oppgave>
Klassifiser forpliktelsesgraden for hvert forslagspunkt nedenfor. Identifiser nøkkelverbet og forklar kort hvorfor det plasserer forslaget i den valgte kategorien. Bruk forslagsnummeret (f.eks. "1") fra teksten som "nr"-felt i svaret.
</oppgave>

<forslagspunkter>
{punkter_tekst}
</forslagspunkter>\
"""
