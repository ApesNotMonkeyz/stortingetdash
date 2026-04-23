# Prompting — prinsipper for dette prosjektet

Prompting er der mye av kvaliteten avgjøres. Disse prinsippene gjelder alle LLM-kall i prosjektet.

## LLM brukes kun til tolkningssteg

Viktig kontekst: I denne arkitekturen brukes Claude ikke til å ekstrahere forslagspunkter eller strukturelle elementer — disse hentes deterministisk fra XML. Claude brukes kun til:

- **Forpliktelsesgrad-klassifisering** (utrede/vurdere/gjennomføre osv.) per forslagspunkt
- **Innholdsanalyse** (sammendrag, argumentasjonslinjer, verdier)
- **Politisk kontekst** (dimensjoner, kobling til eksisterende politikk)

Dette betyr at promptene er mye mer fokuserte enn hvis LLM skulle gjøre alt. Det gjør også kvalitetsmåling enklere: LLM-stegene har klart avgrensede output-schemaer.

## Språk

Prompts skrives på **norsk**. Dokumentene som analyseres er på norsk, domenebegrepene er norske, og nyansene (utrede/gjennomføre/vurdere) finnes ikke i engelsk med samme presisjon. Claude håndterer norsk utmerket.

Unntak: Pydantic-feltnavn og interne identifikatorer er på engelsk (konvensjon for kode), men feltbeskrivelser som Claude ser kan være på norsk.

## Struktur

Bruk XML-tagger for å skille seksjoner i prompten. Claude er trent på dette mønsteret og følger det pålitelig.

```
<rolle>
Du er en analytiker som …
</rolle>

<kontekst>
Dette forslaget er fremmet av [partier] og behandlet i [komité] …
</kontekst>

<oppgave>
Klassifiser forpliktelsesgraden for hvert forslagspunkt …
</oppgave>

<instruksjoner>
1. For hvert forslagspunkt: identifiser hovedverbet
2. …
</instruksjoner>

<forslagspunkter>
{strukturerte_punkter_fra_xml_parsing}
</forslagspunkter>
```

Merk: Vi bruker ikke `<dokument>`-tag med rå PDF eller XML. Vi sender ferdigstrukturerte utklipp fra XML-parsingen.

## System prompt vs brukermelding

- **System prompt**: rollen, generelle prinsipper. Holdes kort (under 500 ord).
- **Brukermelding**: selve oppgaven, eksempler, og innholdet som skal analyseres.

Grunn: system prompt caches av API-et, og du vil ikke blande selve inputen med den faste konteksten.

## Strukturerte utdata

**Bruk tool use til å tvinge strukturert JSON-respons.** Ikke be om JSON i teksten og parse selv — det er skjørt.

Definer et "tool" som matcher Pydantic-schemaet ditt. Claude vil da returnere et tool-call med validert JSON. Eksempel på tool-definisjon:

```python
tool = {
    "name": "lever_forpliktelsesklassifisering",
    "description": "Lever klassifisering av forpliktelsesgrad",
    "input_schema": ForpliktelsesklassifiseringsRespons.model_json_schema()
}
```

Sett `tool_choice={"type": "tool", "name": "lever_forpliktelsesklassifisering"}` for å garantere bruk.

## Few-shot eksempler

For hvert analysesteg — inkluder 1-3 eksempler på ønsket output. Dette hever kvaliteten dramatisk, særlig for:

- Forpliktelsesgrad-klassifisering (utrede/vurdere/gjennomføre)
- Grad av tolkning i politiske dimensjoner

Eksempler plasseres i brukermeldingen før selve oppgaven. Bruk helst ekte forslagspunkter fra historiske saker — disse er offentlige og gir realistiske mønstre.

## Skille fakta fra tolkning

For hvert analysefelt som involverer tolkning: inkluder et `sikkerhet`-felt i schemaet (`høy` / `middels` / `lav`), og et `begrunnelse`-felt. Prompten skal eksplisitt be om dette.

Eksempel:
> "For feltet `politiske_dimensjoner`: dette er din tolkning basert på forslagets innhold. Sett `sikkerhet` til `lav` hvis saken er tverrpolitisk eller teknisk; `middels` hvis det er flere rimelige tolkninger; `høy` kun hvis saken tydelig plasserer seg på en kjent politisk akse."

## Unngå ladet språk

Prompten skal ikke inneholde formuleringer som "kontroversielt", "ekstremt", "rimelig", "fornuftig". Disse påvirker modellens output. Beskriv alltid nøytralt.

Dårlig: "Vurder om forslaget er rimelig."
Bra: "Beskriv hvilke argumenter som fremmes for og imot, basert på teksten."

## Temperatur

- Alle analysesteg: `temperature=0`. Vi vil ha reproduserbarhet.

## Prompt-versjonering

Hver prompt har en versjon (f.eks. `FORPLIKTELSESKLASSIFISERING_V2`). Versjon er del av cache-nøkkelen. Ved endring av prompt: bump versjon, ikke overskriv i cache.

Versjonsstreng legges som konstant øverst i prompt-modulen og inkluderes i cache-nøkkelberegning.

## Testing av prompts

Test hver prompt mot et sett med 5-10 ekte saker som du har manuelt annotert med fasit. Kjør etter hver promptendring. Mål:

- For forpliktelsesklassifisering: treffsikkerhet (vs. fasit) per klasse
- For innholdsanalyse og politisk kontekst: menneskelig vurdering (ikke automatiserbar — lag et lite evalueringsskjema)

## Eksempel: forpliktelsesklassifisering

```
<rolle>
Du klassifiserer forpliktelsesgrad i forslag til stortingsvedtak.
</rolle>

<forpliktelsesgrader>
- utrede: be om utredning/rapport. Ingen forpliktelse til handling.
- vurdere: be regjeringen vurdere. Kan konkludere uten handling.
- legge_frem: krever konkret leveranse til Stortinget (f.eks. lovforslag).
- komme_tilbake: krever retur til Stortinget for ny behandling.
- sikre: forventet resultat uten metodefrihet i stor grad.
- gjennomfore: konkret handling pålagt.
</forpliktelsesgrader>

<eksempler>
"Stortinget ber regjeringen utrede mulighetene for…" → utrede
"Stortinget ber regjeringen legge frem en stortingsmelding om…" → legge_frem
"Stortinget ber regjeringen sikre at…" → sikre
"Stortinget ber regjeringen gjennomføre X innen 2027" → gjennomfore
</eksempler>

<oppgave>
For hvert punkt under, klassifiser forpliktelsesgraden og gi kort begrunnelse basert på hovedverbet.
</oppgave>

<forslagspunkter>
1. Stortinget ber regjeringen vurdere å innføre…
2. Stortinget ber regjeringen komme tilbake til Stortinget med…
</forslagspunkter>
```

## Hva IKKE skal gjøres

- Ikke inkluder "du er ekspert på norsk politikk" eller lignende autoritetsclaims. De hjelper ikke og kan forvrenge output.
- Ikke be modellen "være kreativ" i analysesteg.
- Ikke bland flere analysesteg i én prompt. Ett steg, én prompt.
- Ikke send hele samtalehistorikken hvis stegene er uavhengige. Hver prompt bør være selvstendig.
- Ikke skriv "svar på norsk" — Claude svarer på norsk når prompten er på norsk. Men feltnavn i JSON er engelske (schema-konvensjon).
- Ikke send rå XML eller hele dokumentet til Claude. Send ferdigstrukturerte utklipp.
