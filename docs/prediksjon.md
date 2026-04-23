# Prediksjon — partistandpunkter og sannsynlighetsindikasjon

## Formål

Gitt en analysert stortingssak, gi en sannsynlighetsindikasjon for hvordan hvert parti vil stemme. Returner sannsynlighet, konfidensnivå, og — viktigst — en forklarende begrunnelse per parti.

## Verdipropposisjon: innsikt, ikke spådom

Forskningslitteraturen (se `Parlytics_prediksjon_forskning.docx`) er tydelig: i parlamenter med høy partidisiplin som Stortinget er baseline-treffsikkerheten for "stem som partiet" sannsynligvis 95-98%. En sofistikert modell kan bare forbedre de resterende 2-5%.

**Systemets primære verdi er derfor innsikt og forklaring — ikke binær prediksjon.** Brukere trenger å forstå *hvorfor* partiene sannsynligvis vil stemme slik, hvilke historiske mønstre som ligger bak, og — viktigst — hvilke saker som avviker fra det normale mønsteret.

Sannsynlighetsprosentene er sekundære til begrunnelsen. Bruk alltid formuleringen "sannsynlighetsindikasjon", ikke "prediksjon" — forskjellen er viktig for tilliten til produktet.

## Grunnprinsipper

1. **Alle sannsynligheter beregnes fra data, ikke antatt.** Ingen hardkodede prosenttall. Regelbaserte mønstre verifiseres empirisk i baseline-analysen.

2. **Begrunnelse er viktigere enn prosent.** Hver sannsynlighetsindikasjon må ha en menneskelesbar forklaring som refererer til konkrete kilder (historiske voteringer, fraksjonsinformasjon, partiprogram).

3. **Fokuser analyseressurser der det har verdi.** De fleste saker er forutsigbare. Systemet skal automatisk identifisere kontroversielle saker og gi dem dypere analyse.

4. **Transparens om usikkerhet og historisk treffsikkerhet.** Vis alltid konfidensnivå, og gjør historisk treffsikkerhet per parti og sakstype tilgjengelig for brukere.

5. **Test for LLM-bias.** Forskning dokumenterer at LLM-er har systematisk ideologisk skjevhet mot sentrum/venstre. Mål dette eksplisitt og korriger ved behov.

## Sakskategorier: hvor prediksjon har verdi

Ikke alle saker er like verdifulle å analysere. Systemet skal automatisk klassifisere saker i kategorier og allokere analyseressurser deretter.

### Rutinesaker (lav verdi — lag 1 holder)
Regjeringsproposisjoner som følger vanlig prosedyre. Dok 8-forslag som tydelig plasserer seg i én blokks politikk. Utfallet er forutsigbart fra saksopphav og fraksjonsinformasjon alene. Typisk 80-90% av alle saker.

### Kontroversielle saker (høy verdi — bruk lag 2-3)
Tre underkategorier:

**Koalisjonssaker:** Hvilke opposisjonspartier kan tenkes å støtte et regjeringsforslag? Relevant når regjeringen mangler flertall alene og trenger støttepartier.

**Balansesaker:** Saker der regjeringskoalisjonen selv er delt. Typisk saker med sterk geografisk eller verdimessig dimensjon som krysser partigrensene (distriktspolitikk, bompenger, etikk).

**Personvoteringer:** De sjeldne sakene med åpen votering — etiske spørsmål, lokaliseringssaker. Her bryter partidisiplinen, og individuelle representanters holdninger blir relevante.

Systemet bør automatisk flagge saker som potensielt kontroversielle basert på: historisk lav konsensus på saksfeltet, kryssende fraksjonsinformasjon i komiteen, temaer som erfaringsmessig splitter koalisjoner.

## Signalkilder, rangert etter prediktiv styrke

### Signal 1: Fraksjonsinformasjon fra komitéinnstilling (sterkest — direkte observasjon)

For saker som er komitébehandlet: `<Fraksjon Fra="...">` i innstillingens XML forteller direkte hvilke partier som støtter hva. `<ForslagFraMindretall>` viser hvem som fremmer alternative forslag. `<KomTilrading>` viser flertallets tilråding.

**Dette er ikke prediksjon — det er observasjon av allerede avklarte posisjoner.** Partier avviker sjelden fra egen komitéfraksjon i plenum (konfidens for dette skal verifiseres i baseline-analysen).

- Kilde: XML fra innstillingen (allerede tilgjengelig fra saksanalyse-pipelinen, steg 3)
- Konfidens: svært høy — verifiseres empirisk
- Kostnad: null (deterministisk fra XML, ingen LLM eller API-kall)

### Signal 2: Regjeringsposisjon / saksopphav

Sterk strukturell faktor. Regler (alle verifiseres i baseline-analysen — IKKE bruk før de er verifisert):
- Regjeringsproposisjon → regjeringspartier stemmer for
- Dok 8 fra opposisjon → regjeringspartier stemmer mot
- Dok 8 fra regjeringsparti → sjeldent, krever spesialbehandling

- Kilde: saksmetadata (dokumentgruppe + forslagstillere) + regjeringssammensetning
- Konfidens: avhenger av empirisk verifisering
- Kostnad: null (regelbasert)

**Viktig:** Regjeringssammensetning endrer seg. Konfigurerbar per stortingsperiode. Hent fra `/eksport/regjering` eller konfigurer manuelt.

### Signal 3: Historiske voteringer på lignende saker

Mest verdifull for saker der signal 1 og 2 ikke gir tilstrekkelig svar.

1. Finn saker med overlappende emner/saksfelt i databasen
2. Hent voteringsresultat per parti for disse sakene
3. Beregn vektet sannsynlighet basert på historisk stemmemønster
4. Vekt nyere voteringer høyere enn eldre

Særlig nyttig for å identifisere kryss-blokksamarbeid — "SV og KrF har stemt likt på barnevernssaker 8 av 10 ganger" er et sterkt signal.

- Kilde: Stortingets API (voteringer + voteringsresultat) → lagret lokalt i database
- Konfidens: avhenger av antall lignende saker og tidsmessig relevans
- Kostnad: database-oppslag (gratis etter førstegangshenting)

### Signal 4: Partiprogram / ideologisk plassering

For saker uten voteringshistorikk eller komitébehandling. Minst presist — partier stemmer taktisk og avviker fra program.

- Kilde: valgprogrammer som tekst (krever innhenting og indeksering)
- Konfidens: lav til middels
- Kostnad: LLM-kall for å sammenligne sak mot programtekst (caches)

### Signal 5: Medieutspill og offentlige posisjoner (fremtidig fase)

Uttalelser i media, debatter, sosiale medier. Forskning (Ma et al. 2025) fant begrenset dokumentert effekt av sosiale medier på presisjon i EU-sammenheng.

- Status: **ikke i scope for V1**
- Arkitekturen har felt for "eksterne signaler" som er tomt i V1
- Alternativ i V1: manuelt input — brukere kan legge inn relevante utspill

## Baseline-analyse (MÅ kjøres og verifiseres før prediksjonsmodulen bygges)

Hent voteringsdata for 3-4 sesjoner (f.eks. 2021-2022, 2022-2023, 2023-2024, 2024-2025) og beregn følgende. Alle tall lagres i databasen og vises i en rapport.

### Beregning 0: Naiv baseline-skåre

**Den viktigste beregningen.** Hvor godt treffer en enkel "stem som partiet"-modell?

Beregn på to nivåer:
- Partinivå: "regjeringspartier stemmer for regjeringsforslag, mot opposisjonsforslag" — treffsikkerhet?
- Utfallsnivå: "regjeringsforslag vedtas, opposisjonsforslag forkastes" — treffsikkerhet?

Disse tallene er baseline. Enhver modell som ikke tydelig slår dette har ingen reell prediktiv verdi. Forventet baseline for Norge: 95-98% (verifiseres — IKKE anta).

### Beregning 1: Regjeringslojalitet

Av alle voteringer der regjeringen fremmet proposisjon, hvor ofte stemte hvert regjeringsparti for? Bryt ned per saksfelt.

### Beregning 2: Opposisjonsblokade

Av alle Dok 8-forslag fra opposisjonspartier, hvor ofte stemte regjeringspartiene mot? Bryt ned per saksfelt.

### Beregning 3: Fraksjon-til-plenum-konsistens

**Ny beregning, kritisk for signal 1.** Av alle saker der fraksjonsinformasjon finnes i innstillingens XML: hvor ofte stemte partiene i plenum i samsvar med sin komitéfraksjon? Bryt ned per parti og saksfelt. Dette gir oss konfidensverdien for signal 1.

### Beregning 4: Krysspress-saker

Identifiser voteringer der et regjeringsparti stemte mot egen regjering, eller der et opposisjonsparti stemte for et forslag fra "feil" side. Kategoriser etter saksfelt. Disse sakene er de mest interessante — de viser begrensningene til regelbaserte prediksjoner og er kandidater for der LLM-lag gir verdi.

### Beregning 5: Parti-par-korrelasjon

Hvor ofte stemmer hvert parti-par likt? Produser en korrelasjonamatrise. F.eks. SV-R, H-FrP, SV-KrF. Bryt ned per saksfelt der det gir nyttige mønstre.

### Beregning 6: Saksfelt-predikabilitet

Er noen saksfelter mer forutsigbare enn andre? Beregn varians i voteringsmønster per saksfelt. Forventet: budsjettavstemninger er svært forutsigbare; samvittighetssaker er det ikke.

### Beregning 7: LLM-bias per parti

Etter at lag 3 (LLM-prediksjon) er implementert: kjør prediksjoner på historiske saker og sammenlign med faktisk utfall per parti. Har Claude systematisk skjevhet? Forskning dokumenterer at LLM-er overestimerer sentrum/venstre-partier og underestimerer høyrepopulistiske partier. Verifiser for norsk kontekst.

### Output fra baseline

- Rapport (markdown): faktiske prosenttall for hvert mønster, konklusjon om hvilke regler som holder
- Databasetabeller: aggregerte resultater for runtime-oppslag
- Naiv baseline-skåre: det tallet alle andre modeller måles mot
- Identifiserte kontroversielle saksfelter: der baseline feiler oftest

## Prediksjonsalgoritme

Tre lag, fra billigst/raskest til dyrest:

### Lag 1: Deterministisk (null kostnad)

1. Er innstilling med fraksjonsinformasjon tilgjengelig? → Bruk direkte. Map `<Fraksjon Fra="...">` til partistandpunkter.
2. Er det en regjeringsproposisjon? → Regjeringspartier for, opposisjon mot (med verifisert konfidens fra baseline).
3. Er det Dok 8 fra et bestemt parti/blokk? → Regjeringspartier mot (med verifisert konfidens).

Sett konfidens per parti basert på baseline-tallene. Hvis konfidens er over terskel for alle partier → ferdig. Returner uten videre analyse.

### Lag 2: Historisk mønstermatching (database-oppslag, null LLM-kostnad)

For partier der lag 1 ikke gir tilstrekkelig konfidens:

1. Finn saker med overlappende emner i databasen
2. Hent voteringsresultat for disse sakene
3. Beregn vektet sannsynlighet (nyere saker vektes høyere)
4. Inkluder parti-par-korrelasjon som støttesignal

Krav: minst 5 lignende saker for at resultatet brukes. Hvis færre → merk som lav konfidens.

### Lag 3: LLM-assistert tolkning (dyrest, caches)

For saker der lag 1 og 2 ikke gir tilstrekkelig konfidens, eller som er flagget som kontroversielle:

1. Samle kontekst: saksanalyse (fra fase 1-pipeline), historiske voteringer på lignende saker, regjeringsposisjon, parti-par-korrelasjoner
2. Send til Claude med strukturert prompt som ber om sannsynlighetsvurdering og begrunnelse per parti
3. **Krev at Claude refererer til konkrete historiske saker og partiprogramavsnitt** — ikke aksepter generelle vurderinger uten forankring
4. Returner med kildehenvisninger

LLM-kallet caches permanent for ferdigbehandlede saker.

**Etter implementering:** Kjør beregning 7 (LLM-bias) for å verifisere at Claude ikke har systematisk skjevhet per parti. Hvis skjevhet dokumenteres, vurder kalibrering eller eksplisitt motinstruksjon i prompt.

## Datamodell

### Prediksjon per parti
```
PartiPrediksjon:
  parti: str                    # "FrP", "H", "SV" etc.
  sannsynlighet_for: float      # 0.0-1.0
  konfidens: str                # hoy/middels/lav
  primaersignal: str            # "fraksjon_xml" / "regjeringsposisjon" / "historisk_moenster" / "llm_analyse"
  begrunnelse: str              # menneskelesbar forklaring med kildehenvisninger
  historiske_saker: list[int]   # sak-ID-er brukt som grunnlag
  avvik_fra_baseline: bool      # True hvis dette avviker fra naiv baseline
```

### Samlet sannsynlighetsindikasjon for en sak
```
Saksprediksjon:
  sak_id: int
  sakskategori: str             # "rutine" / "koalisjonssak" / "balansesak" / "personvotering"
  prediksjoner: list[PartiPrediksjon]
  samlet_utfall: str            # "sannsynlig_bifalt" / "sannsynlig_forkastet" / "usikkert"
  samlet_konfidens: str
  signalkilder_brukt: list[str] # hvilke lag som ble brukt
  baseline_ville_gitt: str      # hva naiv baseline ville predikert (for sammenligning)
  eksterne_signaler: list[str]  # manuelt innlagt kontekst (V1: typisk tom)
  beregnet_tidspunkt: datetime
  prompt_versjon: str | None    # bare satt hvis LLM ble brukt
```

## Lagrings- og optimaliseringsstrategi

### Voteringsdata (permanent, hentes én gang)
- Hent alle voteringer for relevante sesjoner fra Stortingets API
- Lagre i PostgreSQL: `voteringer`, `voteringsresultat_parti`
- Oppdater inkrementelt: sjekk nye saker i gjeldende sesjon periodisk
- Rate limit: 100 kall/min — bruk batching med pauser ved massehenting

### Aggregerte mønstre (beregnet, oppdateres ved nye voteringer)
- Naiv baseline-skåre per parti og saksfelt
- Regjeringslojalitet per parti per saksfelt
- Fraksjon-til-plenum-konsistens per parti
- Parti-par-korrelasjon (total og per saksfelt)
- Saksfelt-predikabilitet (varians)
- Lagres som egne tabeller, oppdateres som periodisk jobb

### Prediksjoner (cachet per sak)
- Ferdigbehandlede saker: cache permanent
- Saker under behandling: TTL 24 timer
- Cache-nøkkel inkluderer prompt-versjon hvis LLM ble brukt

### Token-budsjettering
- Lag 1 og 2: null tokens
- Lag 3: estimert ~2000-3000 tokens per sannsynlighetsindikasjon
- Med caching: lag 3 kjøres maks én gang per sak
- Mål: >80% av saker løses i lag 1-2 uten LLM-kall (justert opp fra 70% basert på at fraksjonsinformasjon dekker svært mange saker)

## Implementeringsrekkefølge

1. **Database-oppsett:** PostgreSQL-tabeller for voteringer, voteringsresultat, aggregater, prediksjoner. Migrer saksanalyse-cachen fra dict til database.
2. **Voteringsinnhenting:** Script som henter alle voteringer for valgte sesjoner og lagrer i databasen. Kjøres én gang, deretter inkrementelt.
3. **Baseline-analyse:** Beregn alle mønstre (beregning 0-6). Produser rapport med faktiske tall. **Stopp og evaluer rapporten før du bygger videre.** Tallene bestemmer hvilke regler som er pålitelige nok til å bruke.
4. **Lag 1-2 prediksjon:** Implementer deterministisk og historisk-basert sannsynlighetsindikasjon. Test mot kjente voteringer (holdout-sett).
5. **Lag 3 prediksjon:** LLM-assistert sannsynlighetsindikasjon for saker der lag 1-2 ikke gir tilstrekkelig konfidens.
6. **LLM-bias-evaluering:** Kjør beregning 7. Dokumenter og korriger om nødvendig.
7. **API-endepunkt:** `GET /api/v1/prediksjon/{sak_id}` som returnerer sannsynlighetsindikasjon.
8. **Evaluering:** Kjør mot holdout-sett og mål total treffsikkerhet vs naiv baseline.

## Evaluering og kvalitetsmåling

### Holdout-sett
Sett av 20% av sakene fra siste sesjon som holdout. Kjør sannsynlighetsindikasjon uten at disse sakene er i treningsdataene. Mål:

- Treffsikkerhet per parti (stemte partiet som indikert?)
- Kalibrering (når modellen sier 80%, stemmer det ~80% av tiden?)
- Konfidens-separasjon (gir høy-konfidens-indikasjoner høyere treffsikkerhet enn lav?)
- Verdi over baseline (slår modellen naiv baseline? med hvor mye?)

### Baseline-sammenligning (kritisk)
Sammenlign mot naiv baseline: "regjeringspartier stemmer for regjeringsforslag, mot opposisjonsforslag". Modellen MÅ tydelig slå dette for å rettferdiggjøre sin eksistens. Mål:
- Total treffsikkerhet vs baseline
- Treffsikkerhet på kontroversielle saker (koalisjon/balanse/person) vs baseline
- Treffsikkerhet per parti vs baseline

Hvis modellen ikke slår baseline på kontroversielle saker: den har ingen reell prediktiv verdi. Revurder arkitekturen.

### LLM-bias per parti
Etter lag 3 er implementert: sammenlign Claude-sannsynligheter med faktisk utfall per parti. Se spesifikt etter:
- Overestimering av venstre/sentrum-partier (dokumentert i forskning)
- Underestimering av høyrepopulistiske partier (dokumentert for FrP-tilsvarende i EU)
- Systematiske avvik for småpartier (MDG, R, KrF)

Dokumenter eventuelle skjevheter åpent i produktet.

## Forskning som underbygger arkitekturen

Se `Parlytics_prediksjon_forskning.docx` for fullstendig gjennomgang. Nøkkelreferanser:

- **Mizrahi et al. (2025, VPF):** 85% presisjon på tvers av 5 land. Bekrefter at kombinasjon av voteringshistorikk + aktørtrekk + tekst gir best resultat.
- **Guadarrama Rios et al. (2025):** EU-parlamentet, Random Forest 73-74%. Mest relevant sammenligningsgrunnlag for flerpartisystem.
- **Li et al. (2024, PAA):** Første LLM-agentbasert prediksjon. Sammenlignbar presisjon med tradisjonell ML, men med begrunnelser.
- **Ma et al. (2025):** LLM-er sliter med ytterpartier og har sentrum/venstre-bias. Sosiale medier ga ikke betydelig presisjonsforbedring.
- **Cox, Fiva & Smith (2019):** Norsk partidisiplin historisk. Bekrefter at baseline er svært høy.

## Hva som IKKE skal gjøres

- Ikke hardkod sannsynligheter. Beregn fra data.
- Ikke presenter sannsynlighetsindikasjon som sikker prediksjon. Alltid vis konfidens og begrunnelse.
- Ikke bruk LLM der deterministiske signaler (fraksjonsinformasjon, regjeringsposisjon) gir høy konfidens.
- Ikke tren en klassisk ML-modell (Random Forest, SVM). Datamengden i norsk kontekst er for liten; regelbasert + LLM-tolkning passer bedre.
- Ikke anta at regjeringssammensetningen er statisk. Konfigurer per periode.
- Ikke prøv å predikere individuelle representanters stemme. Prediker på partinivå.
- Ikke ignorer "vedlegges protokollen" som utfall. Det er en tredje kategori utover for/mot.
- Ikke bruk like mye analyseressurser på rutinesaker som på kontroversielle saker. Alloker smart.
- Ikke ignorer LLM-bias. Mål det, dokumenter det, vis det i produktet.
- Ikke selg dette som "prediksjon". Selg det som "sannsynlighetsindikasjon med innsikt og begrunnelse".
