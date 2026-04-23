# Arkitektur

## Overordnet

Backend-tjeneste som eksponerer et HTTP-API mot en eksisterende frontend. Tjenesten tar inn en sak-ID fra Stortinget og returnerer strukturert analyse.

```
Frontend (eksisterende) --> FastAPI --> Analysepipeline --> Claude API
                                    |--> Stortingets API (metadata JSON + publikasjon XML)
                                    |--> PostgreSQL (cache/lagring)
```

## Grunnleggende tilnærming: XML-struktur først, LLM for tolkning

Stortingets XML-dokumenter er strukturerte i henhold til `innstillinger.dtd`. Dette gir oss deterministisk tilgang til:

- Forslagspunkter (`<Forslag>`)
- Partifraksjoner (`<Fraksjon Fra="...">`)
- Vedtakstekst (`<VedtakS>` / `<VedtakL>`)
- Seksjoner og kapitler (`<Kapittel>`, `<Subsek2>`, osv.)
- Originalforslaget (ofte som `<Vedlegg>` i innstillinger)

Vi bruker `lxml` til å parse XML og ekstrahere disse strukturene deterministisk. Claude brukes deretter bare til steg som faktisk krever tolkning.

**Hvorfor:** LLM-ekstraksjon av strukturerte elementer har en ikke-null feilrate (et forslagspunkt kan bli oversett, en fraksjon kan bli feillabelet). Når kilden allerede er strukturert, er det dumt å gi fra seg den sikkerheten. LLM reserveres for det som faktisk er tolkning.

## Pipeline-steg

Hvert steg har typet input og output (Pydantic), og kan testes isolert.

### Steg 1: Metadata-henting
- Hent saksmetadata fra `/eksport/sak?sakid={ID}&format=json`
- Parse `publikasjon_referanse_liste` for å finne relevante publikasjon-ID-er
- Output: `Sak`-objekt med metadata, sesjon, dokumentgruppe, komité, forslagstillere, publikasjon-referanser

### Steg 2: Publikasjon-henting
- For valgt publikasjon (primært innstilling hvis tilgjengelig, ellers originalforslag): hent XML fra `/eksport/publikasjon?publikasjonid=...`
- Hvis XML-parsing feiler: fall tilbake til HTML (`?format=html`)
- Output: `Publikasjon`-objekt med rå XML-tre og metadata om format

### Steg 3: Strukturell parsing (deterministisk, ingen LLM)
- Parse XML med `lxml` etter mønstrene fra `innstillinger.dtd`
- Ekstraher:
  - Seksjonsstruktur (hovedkapitler og undertitler)
  - Alle `<Forslag>`-elementer med `Nr`, `Fra`, tittel og brødtekst
  - `<KomTilrading>` / `<ForslagTilVedtak>` (komiteens tilråding)
  - Eventuelle vedlegg
- Output: `DokumentStruktur`-objekt med seksjonsliste, forslagsliste, vedtaksforslag, vedlegg

### Steg 4: Forpliktelsesgrad-klassifisering (LLM)
- For hvert forslagspunkt: klassifiser forpliktelsesgrad basert på verbvalg (utrede/vurdere/legge_frem/komme_tilbake/sikre/gjennomfore)
- Dette er det eneste tolkningsinnslaget i forslagsekstraksjonen; selve teksten er allerede hentet deterministisk
- Output: `list[Forslagspunkt]` med klassifisert `forpliktelsesgrad`

### Steg 5: Innholdsanalyse (LLM)
- Sammendrag av forslagstillernes problembeskrivelse
- Argumentasjonslinjer og verdier som trekkes på
- Input: relevante seksjoner (typisk bakgrunn + merknader fra forslagstillerne)
- Output: `Innholdsanalyse`

### Steg 6: Politisk kontekst (LLM)
- Politiske dimensjoner (venstre/høyre, sentrum/periferi, marked/stat, osv.)
- Kobling til eksisterende politikk (reversering? opptrapping? nytt?)
- Eksplisitt merket som tolkning med `sikkerhet`-felt
- Output: `PolitiskKontekst`

### Samlet output
- `Saksanalyse` — toppnivå-objekt som inneholder alle ovenstående

## Hvorfor denne strukturen

1. **Testbarhet.** Hvert steg kan kjøres og verifiseres isolert. Strukturell parsing (steg 3) testes uten LLM-kall.
2. **Kvalitet.** Strukturelle elementer hentes deterministisk — ingen hallusinasjon mulig.
3. **Kostnadskontroll.** Kun tolkningssteg bruker LLM. Kortere prompts siden vi kan sende nøyaktig de seksjonene som er relevante for hvert steg.
4. **Feilisolering.** Hvis forpliktelsesgrad er feilklassifisert, er det tydelig hvor problemet ligger.
5. **Iterasjon.** Du kan endre én prompt uten å måtte teste hele pipelinen på nytt.
6. **Caching.** Mellomresultater kan caches; du slipper å kjøre hele pipelinen hvis bare ett steg er endret.

## Claude API-bruk

- Modell: `claude-opus-4-7` som standard
- Strukturerte utdata via tool use: definer et "tool" som tvinger JSON-respons matching Pydantic-schemaet
- Temperatur: 0 for alle analysesteg
- Input til Claude: ferdigstrukturert tekst (utklipp fra XML-parsingen), IKKE rå XML
- System prompt: kort, fokusert på rollen. Domenekunnskap legges i brukermelding med eksempler.

## Dokumentvalg: hvilken publikasjon analyserer vi?

En sak har ofte flere publikasjoner: originalforslaget/proposisjonen, innstillingen fra komiteen, eventuelt referat.

**Primærvalg: Innstilling (Innst.)** når den finnes. Innstillingen inneholder:
- Selve saken (ofte som vedlegg — originalforslaget)
- Komiteens behandling og merknader
- Mindretallsforslag per fraksjon
- Komiteens tilråding og foreslåtte vedtak

Dette er det mest informasjonsrike dokumentet og optimalt for analyse.

**Fallback 1: Originaldokumentet** (representantforslag, proposisjon, melding) hvis innstilling ikke finnes (saken er ikke ferdigbehandlet i komité).

**Fallback 2: HTML-versjonen** hvis XML-parsing feiler.

Pipelinen velger publikasjon basert på sakens status i steg 1-2.

## Caching

Cache på Claude-kall-nivå, ikke pipeline-nivå. Nøkkel: `hash(prompt_template_version + input_content_hash + model_id)`. Dette lar deg iterere på prompts uten å ødelegge cachen for andre steg.

XML-publikasjoner caches separat på `publikasjonid`.

## Feilhåndtering

- Stortingets API: exponential backoff, maks 3 forsøk
- Claude API: SDK håndterer retries for transient errors; logg men ikke svelg permanente feil
- XML-parsing: hvis DTD ikke matcher forventet struktur, logg hvilken struktur som faktisk ble funnet og fall tilbake til HTML eller marker saken som "kan ikke analyseres"
- Manglende publikasjoner: marker saken med status og grunn; ikke kræsj

## Observabilitet

- Strukturert logging (JSON) med sak-ID, publikasjon-ID, steg, modell, token-bruk, varighet
- Ingen PII i logger (stortingsdokumenter er offentlige, så dette er mest for hygiene)

## Database (PostgreSQL)

Brukes til tre formål:

### 1. Analyse-cache (erstatter dict-cache)
- Tabell `saksanalyser`: sak_id (PK), analyse_json, opprettet, utloper (NULL = permanent)
- Ferdigbehandlede saker: permanent. Andre: TTL 24 timer.

### 2. Voteringsdata (permanent historikk)
- Tabell `voteringer`: votering_id (PK), sak_id, dato, tema, vedtatt (bool)
- Tabell `voteringsresultat_parti`: votering_id + parti (PK), for_stemmer, mot_stemmer, fraværende
- Hentes fra Stortingets API én gang per sak, oppdateres inkrementelt for gjeldende sesjon

### 3. Aggregerte mønstre og prediksjoner
- Tabell `parti_moenster`: parti, saksfelt, antall_voteringer, andel_for, sist_oppdatert
- Tabell `parti_korrelasjon`: parti_a, parti_b, andel_lik_stemme, antall_voteringer
- Tabell `saksprediksjoner`: sak_id (PK), prediksjoner_json, signalkilder, prompt_versjon, opprettet

Migreringer med `alembic` eller rene SQL-filer — ikke auto-create.

## Prediksjonsmodul

Fullstendig plan i `docs/prediksjon.md`. Arkitektonisk er det en separat pipeline som bygger på saksanalysens output:

```
Saksanalyse (eksisterende) → Prediksjons-pipeline:
  Lag 1: Fraksjonsinformasjon (fra XML) + regjeringsposisjon (regelbasert)
  Lag 2: Historisk mønstermatching (database-oppslag)
  Lag 3: LLM-assistert tolkning (kun ved behov, caches)
→ Saksprediksjon JSON
```

Eget endepunkt: `GET /api/v1/prediksjon/{sak_id}`

Prediksjonen avhenger av at baseline-analysen er kjørt først — den produserer de empiriske mønstrene som lag 1 og 2 bruker.

## Hva som er ute av scope

- Analyse av referater og debatter
- Automatisk medieovervåkning (manuelt input for relevante utspill er støttet)
- ML-modelltrening (datamengden er for liten; regelbasert + LLM-tolkning gir bedre resultater)
- Prediksjon på individnivå (kun partinivå)
