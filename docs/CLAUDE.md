# Saksanalyse — AI-drevet analyse av norske stortingssaker

## Hva dette prosjektet er

Et backend-verktøy som analyserer politiske saker fra Stortinget (representantforslag/Dok 8, proposisjoner, meldinger) ved hjelp av Claude. Systemet skal produsere strukturerte sammendrag av saksinnhold og — i senere faser — predikere hvordan partiene vil stille seg til forslagene.

Verktøyet kalles fra en eksisterende nettside som allerede henter sakstitler og metadata fra Stortinget. Denne tjenesten leverer analysen av selve dokumentinnholdet.

## Faser og status

### Fase 1: Saksanalyse ✅ FERDIG
Gitt en sak-ID fra Stortinget, produser en strukturert analyse av sakens innhold: sammendrag, forslagspunkter, politiske dimensjoner, og kobling til eksisterende politikk.
- Pipeline steg 1-6 implementert og testet
- `GET /api/v1/analyse/{sak_id}` operativt med caching
- Frontend-integrert med utvidbart analysepanel

### Fase 2: Prediksjon av partistandpunkter ← AKTIV FASE
Gitt en analysert sak, prediker hvordan hvert parti sannsynligvis vil stemme. Se `docs/prediksjon.md` for fullstendig plan.

Implementeringsrekkefølge:
1. Database-oppsett (PostgreSQL — erstatter også dict-cache fra fase 1)
2. Voteringsinnhenting fra Stortingets API
3. Baseline-analyse (beregn empiriske mønstre fra voteringsdata)
4. Lag 1-2 prediksjon (deterministisk + historisk mønstermatching)
5. Lag 3 prediksjon (LLM-assistert for vanskelige saker)
6. API-endepunkt og frontend-integrasjon
7. Evaluering mot holdout-sett

## Hva som skal optimaliseres

**Analysekvalitet først.** Dette er en ekspertsak der brukere vil oppdage feil umiddelbart. Kostnad og hastighet er sekundært for selve analysen.

**Kostnadsoptimalisering for prediksjon.** Prediksjonsmodulen er designet i tre lag der billigste/raskeste forsøkes først. LLM brukes bare som siste utvei. Alle resultater caches. Mål: >80% av saker løses uten LLM-kall.

**Alle sannsynligheter beregnes fra data.** Ingen hardkodede prosenttall. Regelbaserte mønstre verifiseres empirisk mot historiske voteringer i baseline-analysen før de brukes.

**Innsikt over spådom.** Systemets verdi ligger i å forklare *hvorfor* partiene sannsynligvis stemmer slik, ikke i å gi et binært ja/nei-svar. Begrunnelse og kildehenvisninger er viktigere enn prosenttallet. Bruk "sannsynlighetsindikasjon", ikke "prediksjon".

## Kilde og format for dokumenter

Dokumenter hentes via Stortingets publikasjon-endepunkt:
`https://data.stortinget.no/eksport/publikasjon?publikasjonid={ID}`

**XML er primærkilden.** Stortingets dokumenter publiseres i et strukturert XML-format basert på egne DTD-er (`innstillinger.dtd` for innstillinger/representantforslag/proposisjoner fra 2016-2017 og nyere). Dette gir deterministisk tilgang til dokumentstruktur: `<Forslag>`-elementer, `<Fraksjon>` for partifraksjoner, `<VedtakS>`/`<VedtakL>` for vedtakstekst, osv.

HTML (`?format=html`) brukes kun som fallback for eldre dokumenter eller tilfeller hvor XML-parsing feiler.

PDF er IKKE primærkilde. Vi laster ikke ned PDF-er fra `stortinget.no`.

Detaljer om API-et i `docs/stortinget-api.md`.

## Viktige prinsipper

1. **XML-parsing for struktur, LLM for tolkning.** Det som er strukturelt entydig i XML-en (forslagspunkter, fraksjoner, seksjoner, metadata) ekstraheres deterministisk. Claude brukes bare til steg som krever tolkning: forpliktelsesgrad-klassifisering, sammendrag, politisk kontekst. Dette gir høyere kvalitet (ingen risiko for at LLM "glemmer" et forslagspunkt), lavere kostnad, og enklere testing.

2. **Skill mellom fakta og tolkning.** Det dokumentet faktisk sier skal ekstraheres ordrett fra XML. Politiske implikasjoner og vurderinger skal være tydelig markert som tolkning, ikke presentert som fakta.

3. **Politisk nøytralitet i prompts og kode.** Prompts skal ikke inneholde ladede formuleringer eller forhåndsantakelser om hva som er "rimelig" eller "ekstremt". La modellen beskrive saker på deres egne premisser.

4. **Strukturerte utdata, alltid.** All LLM-output skal valideres mot Pydantic-schemaer. Ingen frihåndstekst som "sluttprodukt" — fri tekst kan forekomme inne i strukturerte felt, men selve responsobjektet skal alltid være typet.

5. **Pipeline-tenkning.** Analysen bygges som en sekvens av steg med klare inn-/utdata. Ikke én stor "analyser()"-funksjon.

## Teknologi

- **Python 3.11+**
- **FastAPI** som web-rammeverk
- **Pydantic v2** for schemaer og validering
- **lxml** for XML-parsing (robust håndtering av DTD, entities, trykkeriformat)
- **anthropic** (offisiell SDK) for Claude-kall
- **httpx** for HTTP mot Stortinget
- **PostgreSQL** for lagring (voteringsdata, analyser, prediksjoner, aggregater)
- **asyncpg** eller **sqlalchemy[asyncio]** for async databasetilgang
- **pytest** for testing

Detaljer i `docs/arkitektur.md`.

## Domenekunnskap (KRITISK å lese før du skriver prompts eller analyselogikk)

Se `docs/domene-stortinget.md` for hvordan Stortinget fungerer, hva dokumenttypene er, og hvilke språklige nyanser som har betydning (særlig forskjellen mellom "utrede", "vurdere" og "gjennomføre").

## Stortingets API og XML-format

Se `docs/stortinget-api.md` for endepunkter, rate limits, DTD-struktur, og kvirker. Oppsummert: Publikasjoner hentes via `/eksport/publikasjon?publikasjonid=...`. Metadata om saken hentes via `/eksport/sak?sakid=...&format=json`. XML følger `innstillinger.dtd` for nyere dokumenter — sentrale elementer er `<Forslag>`, `<Fraksjon>`, `<KomTilrading>`, `<VedtakS>`, `<Vedlegg>`.

## Prediksjon av partistandpunkter

Se `docs/prediksjon.md` for fullstendig plan, og `Parlytics_prediksjon_forskning.docx` for underliggende forskningsgjennomgang. Oppsummert: tre-lags modell der billigste signal forsøkes først (1: direkte fraksjonsinformasjon fra XML, 2: regelbasert + historisk mønster fra voteringsdata, 3: LLM-tolkning). Alle sannsynligheter beregnes fra data. Baseline-analyse verifiserer empirisk at antatte mønstre faktisk holder. Fokuser analyseressurser på kontroversielle saker (koalisjon, balanse, personvotering) — rutinesaker løses deterministisk.

## Prompting

Se `docs/prompting.md` for prinsipper. Oppsummert: norsk språk i prompts, XML-tagger for struktur, few-shot eksempler for hvert analysesteg, eksplisitt skille mellom "hva står det" og "hva betyr det".

## Kodekonvensjoner

Se `docs/kodekonvensjoner.md`. Oppsummert: type hints overalt, Pydantic for alle datamodeller, norsk i docstrings for domenespesifikk kode, engelsk for generisk infrastrukturkode.

## Ting som IKKE skal gjøres

- Ikke last ned PDF-er fra `stortinget.no` med mindre XML og HTML begge feiler. Primærkilden er publikasjon-endepunktets XML.
- Ikke bruk LLM til å ekstrahere forslagspunkter, titler, eller seksjonsstruktur. Disse hentes fra XML-tagger. LLM brukes kun til tolkende steg.
- Ikke bruk regex til å parse stortingsdokumenter. Bruk `lxml` og XPath.
- Ikke introduser politiske antakelser i prompts ("dette er et kontroversielt forslag", "venstresiden mener typisk…"). La modellen analysere fritt.
- Ikke lag én stor monolittisk analyseprompt. Del opp i steg.
- Ikke hardkod sak-ID-er, sesjoner, eller publikasjon-ID-er som kan endres. Bruk config.
- Ikke cache Claude-responser på tvers av promptversjoner. Inkluder prompt-hash i cache-nøkkelen.
- Ikke anta at alle felt i XML alltid er til stede. DTD-en har mange `#IMPLIED` og valgfrie elementer. Skriv defensiv parsing.
- Ikke hardkod sannsynligheter i prediksjonsmodulen. Alle prosenttall beregnes fra voteringsdata.
- Ikke bruk LLM for prediksjon der deterministiske signaler (fraksjonsinformasjon, regjeringsposisjon) gir høy konfidens.
- Ikke hardkod regjeringssammensetning. Konfigurer per stortingsperiode.
- Ikke presenter prediksjoner som fakta. Alltid vis sannsynlighet, konfidens og begrunnelse.

## Arbeidsmåte med Claude Code

- Jobb i små, verifiserbare steg. Ett analysesteg om gangen.
- Lag planen først, implementer etterpå. Be om en plan hvis oppgaven er større enn én fil.
- Test mot ekte saker fra Stortinget, ikke mocks. Bruk sak-ID 47163 som standard testtilfelle.
- Hvis du er usikker på XML-struktur — inspiser DTD-en (`docs/stortinget-api.md` har lenke) eller hent en ekte publikasjon og se. Ikke gjett på elementnavn.
- Ikke legg til avhengigheter uten å begrunne det. Sjekk om eksisterende bibliotek dekker behovet først.

## Hemmeligheter

API-nøkler leses fra miljøvariabler (`.env` lokalt, systemvariabler i produksjon). Aldri hardkodet. Aldri committet. `ANTHROPIC_API_KEY` er navnet.
