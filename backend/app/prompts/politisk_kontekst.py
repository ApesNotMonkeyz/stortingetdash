from __future__ import annotations

from app.models.dokument import DokumentStruktur, Forslagspunkt
from app.models.analyse import Sikkerhetsnivaa, KoblingType

POLITISK_KONTEKST_V1 = "POLITISK_KONTEKST_V1"

# Sikkerhetsverdier: hoy=høy, middels=middels, lav=lav (ASCII for API-kompatibilitet)
SYSTEM = """\
<rolle>
Du analyserer politisk kontekst for norske stortingsforslag.
</rolle>

<instruksjoner>
- All analyse er tolkning — behandle den deretter.
- Identifiser bare dimensjoner som er tydelig forankret i dokumentteksten.
- Sett sikkerhet til 'lav' for saker som er tekniske eller bredt støttet på tvers av partier.
- Sett sikkerhet til 'middels' hvis det finnes flere rimelige tolkninger av plasseringen.
- Sett sikkerhet til 'hoy' (betyr høy) bare hvis saken klart plasserer seg på en kjent politisk akse.
- Bruk nøytralt språk. Ikke karakteriser forslag som radikale, moderate, ekstreme eller fornuftige.
- Kobling til eksisterende politikk: beskriv om forslaget bryter med, bygger på eller er nytt \
sammenlignet med gjeldende politikk — basert kun på det dokumentet sier.
</instruksjoner>

<gyldige_sikkerhetsnivaa>
hoy (=høy), middels, lav
</gyldige_sikkerhetsnivaa>

<gyldige_koblingstyper>
reversering, opptrapping, nytt, videroforing (=videreføring)
</gyldige_koblingstyper>\
"""


def brukermelding(dok: DokumentStruktur, forslag: list[Forslagspunkt]) -> str:
    bakgrunn = _hent_bakgrunn(dok)
    forslag_tekst = _hent_forslagstekst(dok, forslag)
    return f"""\
<eksempel>
Bakgrunn: "Norske klimagassutslipp fra industrien har økt siden 2020. Representantene mener \
markedet alene ikke vil løse dette."
Forslag: "Stortinget ber regjeringen innføre strengere CO2-avgifter for industrien."

Politisk kontekst:
- Dimensjon: stat/marked — plassering: statlig inngripen (sikkerhet: høy, \
fordi forslaget eksplisitt avviser markedsløsning)
- Kobling: opptrapping (sikkerhet: middels, fordi eksisterende CO2-avgifter allerede finnes — \
dette er en skjerpelse)
</eksempel>

<oppgave>
Analyser den politiske konteksten for dokumentet nedenfor. Identifiser relevante politiske \
dimensjoner og kobling til eksisterende politikk. Merk at dette er tolkning — bruk \
sikkerhetsnivåene korrekt.
</oppgave>

<bakgrunn>
{bakgrunn}
</bakgrunn>

<forslagspunkter>
{forslag_tekst}
</forslagspunkter>\
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
        return "\n\n".join(s.tekst[:2500] for s in relevante[:3])
    if dok.seksjoner:
        return dok.seksjoner[0].tekst[:2500]
    return "(Ingen bakgrunnsseksjoner funnet)"


def _hent_forslagstekst(dok: DokumentStruktur, forslag: list[Forslagspunkt]) -> str:
    # Foretrekk de klassifiserte forslagspunktene fra steg 4
    if forslag:
        linjer = []
        for p in forslag:
            linje = f"{p.nr}. {p.tekst}"
            if p.forpliktelsesgrad:
                linje += f" [forpliktelsesgrad: {p.forpliktelsesgrad.value}]"
            linjer.append(linje)
        return "\n".join(linjer)
    if dok.vedtakstekst:
        return dok.vedtakstekst
    return "(Ingen forslagspunkter funnet)"
