from __future__ import annotations

from app.models.dokument import DokumentStruktur

INNHOLDSANALYSE_V1 = "INNHOLDSANALYSE_V1"

SYSTEM = """\
<rolle>
Du analyserer innholdet i norske stortingsdokumenter og produserer strukturerte sammendrag.
</rolle>

<instruksjoner>
- Basert utelukkende på det som faktisk står i teksten.
- Problemforståelse: hva beskriver forslagstillerne som problemet?
- Løsningsforslag: hva foreslår de konkret gjort? (ikke bakgrunnsbeskrivelsen)
- Argumentasjonslinjer: hvilke verdier, hensyn og fakta bruker de som begrunnelse?
- Ikke tilskriv intensjoner som ikke er eksplisitt uttrykt i teksten.
- Ikke vurder om argumentene er gode eller dårlige.
</instruksjoner>\
"""


def brukermelding(dok: DokumentStruktur) -> str:
    bakgrunn = _hent_bakgrunn(dok)
    forslag_tekst = _hent_forslagstekst(dok)
    return f"""\
<eksempel>
Bakgrunn: "Norske kommuner mangler i dag et helhetlig system for digital innrapportering til stat. \
Det fører til dobbeltarbeid og ineffektiv ressursbruk."
Forslag: "Stortinget ber regjeringen utrede mulighetene for et felles digitalt rapporteringssystem \
for kommunene."

Analyse:
- Problemforståelse: Kommunene mangler et felles system for digital innrapportering, noe som gir \
dobbeltarbeid og ineffektivitet.
- Løsningsforslag: Utrede et felles digitalt rapporteringssystem.
- Argumentasjonslinjer: Effektivitetsgevinst for kommunene; forenkling av offentlig forvaltning.
</eksempel>

<oppgave>
Analyser dokumentet nedenfor og lever strukturert analyse.
</oppgave>

<bakgrunn>
{bakgrunn}
</bakgrunn>

<forslag>
{forslag_tekst}
</forslag>\
"""


def _hent_bakgrunn(dok: DokumentStruktur) -> str:
    relevante = [
        s for s in dok.seksjoner
        if any(
            kw in s.tittel.lower()
            for kw in ("bakgrunn", "begrunnelse", "merknad", "innledning", "vurdering")
        )
    ]
    if relevante:
        return "\n\n".join(s.tekst[:3000] for s in relevante[:3])
    if dok.seksjoner:
        return dok.seksjoner[0].tekst[:3000]
    return "(Ingen bakgrunnsseksjoner funnet)"


def _hent_forslagstekst(dok: DokumentStruktur) -> str:
    if dok.mindretallsforslag:
        return "\n".join(f"{p.nr}. {p.tekst}" for p in dok.mindretallsforslag)
    if dok.vedtakstekst:
        return dok.vedtakstekst
    return "(Ingen forslagstekst funnet)"
