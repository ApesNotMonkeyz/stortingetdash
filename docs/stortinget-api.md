# Stortingets API og XML-format

Offisiell dokumentasjon: https://data.stortinget.no/dokumentasjon-og-hjelp/

## Base-URL

`https://data.stortinget.no/eksport/`

## Format

- **Metadata-endepunkter** (sak, saker, partier, komiteer, osv.): Bruk `?format=json`. Enklere å jobbe med enn XML.
- **Publikasjon-endepunktet** (selve dokumentene): Returnerer XML som standard. Dette er primærkilden for analyse. HTML er tilgjengelig med `?format=html`, men XML er mer strukturert og foretrukket.

## Rate limit

100 kall/minutt per klient. Får du `429 Too Many Requests`, vent og prøv igjen (exponential backoff). Stortinget oppfordrer til at kilden oppgis og at `User-Agent` settes med kontaktinfo.

## Arbeidsflyt for å analysere en sak

Gitt en sak-ID:

1. Hent sakmetadata via `/eksport/sak?sakid={ID}&format=json`
2. Parse `publikasjon_referanse_liste` — finn publikasjon-ID-er for relevante dokumenter
3. For hver publikasjon: hent XML via `/eksport/publikasjon?publikasjonid={PUB_ID}`
4. Parse XML i henhold til `innstillinger.dtd`
5. Send strukturerte seksjoner videre til LLM-tolkningssteg

## Metadata-endepunkter

### Sakdetaljer
```
GET /eksport/sak?sakid={ID}&format=json
```
Returnerer metadata for saken: dokumentgruppe (`representantforslag`, `proposisjon`, `melding`), komité, emner, saksordfører, forslagstillere, publikasjon-referanser, henvisning (f.eks. "Dokument 8:175 S (2009-2010)").

**Viktig:** Feltet `publikasjon_referanse_liste` inneholder referanser til tilhørende publikasjoner. Disse refererer både til selve representantforslaget/proposisjonen og til eventuell innstilling fra komiteen.

### Saker i en sesjon
```
GET /eksport/saker?sesjonid={SESJON}&format=json
```
F.eks. `sesjonid=2024-2025`. Returnerer liste over alle saker.

### Partier
```
GET /eksport/partier?SesjonId={SESJON}&format=json
```

### Komiteer
```
GET /eksport/komiteer?sesjonid={SESJON}&format=json
```

### Voteringer for en sak (senere fase)
```
GET /eksport/voteringer?sakid={ID}&format=json
```
Ikke relevant i saksanalyse-fasen.

## Publikasjon-endepunktet (primær dokumentkilde)

```
GET /eksport/publikasjon?publikasjonid={PUB_ID}
```

Returnerer XML etter DTD. For HTML-fallback: `&format=html`.

**Publikasjon-ID-format:** Eksempler: `dok8-202425-001`, `inns-202425-123-s`, `prop-202425-45-l`. Disse kommer fra `publikasjon_referanse_liste` i sak-responsen — ikke konstruer dem manuelt.

### XML-struktur (fra `innstillinger.dtd`)

Root-element: `<Innstilling>` (eller lignende for andre dokumenttyper — strukturen er analog).

```
<Innstilling Status="Komplett">
  <Startseksjon>
    <Innhfrt>...</Innhfrt>        <!-- Innholdsfortegnelse, valgfri -->
    <Navn>...</Navn>              <!-- Dokumentnavn/referanse -->
    <Aar>...</Aar>                <!-- Sesjon, f.eks. "2024-2025" -->
    <Doktit>...</Doktit>          <!-- Dokumenttittel -->
    <Kildedok>...</Kildedok>      <!-- Referanse til kildedokument, f.eks. Dok 8-nummer -->
    <Ingress>...</Ingress>        <!-- Kort ingress -->
    <TilStortinget>...</TilStortinget>
  </Startseksjon>

  <Hovedseksjon>
    <!-- Innhold: Del eller Kapittel, nøstet -->
    <Kapittel>
      <Tittel>...</Tittel>
      <A>...</A>                  <!-- Avsnitt -->
      <Subsek2>...</Subsek2>      <!-- Underseksjoner -->
    </Kapittel>
    <ForslagFraMindretall>       <!-- Valgfri: forslag fra mindretall i komiteen -->
      <Fraksjon Fra="H, FrP">    <!-- Partifraksjon som fremmer forslaget -->
        <Tittel>...</Tittel>
        <Forslag Nr="1" Fra="H, FrP">
          <Tittel>Forslag 1</Tittel>
          <A>Stortinget ber regjeringen...</A>
        </Forslag>
      </Fraksjon>
    </ForslagFraMindretall>
  </Hovedseksjon>

  <Sluttseksjon>
    <KomTilrading>                <!-- Komiteens tilråding -->
      <Tittel>Komiteens tilråding</Tittel>
      <A>Komiteen har for øvrig ingen merknader...</A>
      <Komiteen>
        <A>...</A>
      </Komiteen>
      <ForslagTilVedtak>
        <VedtakS>                 <!-- Stortingsvedtak -->
          <Tittel>I</Tittel>
          <A>Stortinget ber regjeringen...</A>
        </VedtakS>
        <!-- eller VedtakL for lovvedtak -->
      </ForslagTilVedtak>
    </KomTilrading>
    <Sign>                        <!-- Signaturer -->
      <Dato>...</Dato>
      <Signtab>...</Signtab>
    </Sign>
  </Sluttseksjon>

  <Vedlegg fil="...">              <!-- Valgfri: vedlegg, ofte originalforslaget -->
    <VedlNr>Vedlegg 1</VedlNr>
    <Tittel>...</Tittel>
    <A>...</A>
  </Vedlegg>
</Innstilling>
```

### Sentrale elementer for analyse

- **`<Forslag>`** (i `<Fraksjon>` i `<ForslagFraMindretall>`): individuelle mindretallsforslag. Attributter: `Nr`, `Fra` (kommaseparerte partikoder). Innhold: `<Tittel>` + `<A>`-avsnitt (selve forslagsteksten).
- **`<Fraksjon>`**: partifraksjon i komiteen som fremmer forslag. `Fra`-attributtet indikerer hvilke partier.
- **`<VedtakS>` / `<VedtakL>`**: komiteens foreslåtte stortings-/lovvedtak. Dette er det som skal voteres over.
- **`<Kapittel>` med `<Tittel>`**: hovedseksjoner i dokumentet. Tittelen angir tema (f.eks. "Bakgrunn", "Komiteens merknader").
- **`<Vedlegg>`**: originalforslaget kommer ofte som vedlegg i innstillingen. Attributt `fil` kan peke til ekstern fil.

### Dokumenttyper og rot-elementer

Merk at `innstillinger.dtd` dekker flere dokumenttyper, og rot-elementet varierer:

- Innstilling (Innst.): `<Innstilling>`
- Representantforslag (Dok 8): publiseres separat og har andre tagger. Kan også finnes som `<Vedlegg>` i innstillingen.
- Proposisjon (Prop.): egen struktur, men mange samme elementer.
- Melding (Meld.St.): egen struktur.

**Anbefalt strategi:** Start med innstillingen (Innst.) når den finnes — den inneholder både originalforslaget (som vedlegg) OG komiteens behandling i ett dokument. Dette er optimalt for analyse.

Hvis innstilling ikke finnes ennå (saken er ikke komiteebehandlet), fall tilbake til representantforslaget/proposisjonen direkte.

## Tekstekstraksjon fra XML

Tekstinnhold i `<A>` kan inneholde inline-formatering: `<Uth Type="Kursiv">`, `<Sup>`, `<Sub>`, `<Fotnote>`, `<Xref>`. For LLM-tolkning er det typisk nok å ekstrahere tekstinnholdet ignorering formatering — men behold `<Fotnote>`-tekst som del av løpeteksten hvis det påvirker mening.

XPath-eksempler (med `lxml`):

```python
# Alle forslagspunkter (mindretallsforslag)
forslag = tree.xpath("//ForslagFraMindretall/Fraksjon/Forslag")

# Komiteens tilrådning
tilraading = tree.xpath("//KomTilrading/ForslagTilVedtak/*")

# Dokumenttittel
tittel = tree.xpath("//Startseksjon/Doktit/text()")

# Originalforslaget som vedlegg
vedlegg = tree.xpath("//Vedlegg[VedlNr='Vedlegg 1']")
```

## DTD-referanser

- Nyere dokumenter (2016-2017 og senere): `https://www.stortinget.no/dtd/innstillinger.dtd`
- Referater (samme periode): `https://www.stortinget.no/dtd/forhandlinger.dtd`
- Eldre dokumenter: `https://www.stortinget.no/dtd/innst_xml.dtd`
- Eldre referater: `https://www.stortinget.no/dtd/forhandl_xml.dtd`
- For konkret sammenligning av XML-strukturer på tvers av DTD-er, se docs/spike-xml-sammenligning.md

## Eksempler for testing

### Standard testsak
Sak-ID `47163`: Representantforslag om å utrede etablering av en transportetat. Henvisning: "Dokument 8:175 S (2009-2010), Innst. 109 S (2010-2011)". Bruker eldre DTD — kan være nyttig for å teste fallback-logikk.

For testing mot nyere DTD, velg en sak fra sesjonen 2023-2024 eller 2024-2025.

### Testkall
```bash
# Metadata
curl "https://data.stortinget.no/eksport/sak?sakid=47163&format=json"

# XML-publikasjon (eksempel fra DTD-dokumentasjon)
curl "https://data.stortinget.no/eksport/publikasjon?publikasjonid=dok8-201617-002"

# HTML-fallback
curl "https://data.stortinget.no/eksport/publikasjon?publikasjonid=dok8-201617-002&format=html"
```

## Viktige felt i sak-responsen

- `id` — sak-ID (samme som input)
- `dokumentgruppe` — `"representantforslag"`, `"proposisjon"`, `"melding"`, osv.
- `henvisning` — menneskelig lesbar referanse
- `korttittel` / `innstillingstekst` — ulike titler
- `emne_liste` — tematiske tags
- `komite` — ansvarlig komité
- `sak_opphav.forslagstiller_liste` — representanter (for Dok 8)
- `saksordfoerer_liste` — saksordfører(e)
- `status` — `"behandlet"` betyr ferdigbehandlet i komité
- `ferdigbehandlet` — boolean
- `publikasjon_referanse_liste` — referanser til publikasjoner
- `sak_sesjon` — sesjon (f.eks. "2024-2025")

## Fallgruver

- **DTD-en er "trykkeriformat"** — laget for publisering, ikke strukturert analyse. Elementer kan være brukt inkonsistent mellom dokumenter. Skriv parsing defensivt; ikke anta at et felt alltid finnes.
- **Eldre dokumenter bruker eldre DTD** — saker fra før sesjonen 2016-2017 følger `innst_xml.dtd`. Elementene overlapper mye, men ikke 100 %. Sjekk DTD hvis parsing feiler.
- **Publikasjon-ID-er må hentes fra sakresponsen**, ikke konstrueres. URL-mønstre endres over tid.
- **`Fra`-attributtet på `<Forslag>` og `<Fraksjon>`** inneholder kommaseparerte partikoder (f.eks. `"H, FrP, KrF"`). Parse med bevissthet om mellomrom og variasjoner.
- **Entity `&shy;`** (soft hyphen) kan forekomme i tekst — enten fjern eller behold bevisst. Påvirker ikke mening, men kan gi rare strenger hvis ikke håndtert.

## Ikke gjør dette

- Ikke parse XML med regex. Bruk `lxml`.
- Ikke hardkod URL-er til enkeltdokumenter. Gå alltid via sak-API-et for å finne gjeldende publikasjon-ID.
- Ikke hamre API-et uten caching. Metadata og publikasjoner endrer seg sjelden — cache lokalt.
- Ikke glem `User-Agent`-header med kontaktinfo. Stortingets bruksvilkår ber om at kilden oppgis.
- Ikke send rå XML til Claude. Ekstraher relevante seksjoner som tekst/struktur først.
