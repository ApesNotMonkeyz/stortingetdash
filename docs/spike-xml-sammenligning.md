# Spike: XML-struktur i Stortingets publikasjoner

**Dato:** 2026-04-20  
**Saker analysert:**
- Ny DTD — Innstilling: `inns-202425-176s` (Innst. 176 S (2024–2025), nordisk produktivitetskommisjon)
- Ny DTD — Dok 8: `dok8-202324-173s` (Dok 8:173 S (2023–2024), nordisk produktivitetskommisjon)
- Gammel DTD — Innstilling: `inns-201011-109` (Innst. 109 S (2010–2011), transportetat)
- Gammel DTD — Dok 8: `dok8-200910-175` (Dok 8:175 S (2009–2010), transportetat)

Råfilene ligger i `tests/fixtures/spike/`. Alle fire er UTF-8 og parse med `lxml.etree.fromstring()` uten feil.

---

## DTD 1: Ny DTD (`innstillinger.dtd`, 2016–2017 og nyere)

### Gjelder for
Både innstillinger OG representantforslag (Dok 8) fra og med sesjonen 2016–2017. **Begge dokumenttypene bruker samme rootelement og samme overordnede struktur.** Eneste strukturelle skilletegn er innholdet, ikke elementnavnene.

### Rootelement

```xml
<Innstilling Status="Komplett">
```

Atributt `Status` er alltid `"Komplett"` i ferdige dokumenter. PascalCase gjennomgående.

### Toppnivåstruktur

```
<Innstilling>
  <Startseksjon>          ← metadata
  <Hovedseksjon>          ← hoveddokument
  <Sluttseksjon>          ← tilråding + signatur
  <Vedlegg>               ← kun innstillinger; Dok 8 mangler dette elementet
```

### `<Startseksjon>` — metadata

```xml
<Startseksjon>
  <Navn>Innst. 176\nS</Navn>           <!-- dokumentreferanse, kan ha linjeskift -->
  <Aar>(2024–2025)</Aar>               <!-- sesjon med en-dash (U+2013) -->
  <Doktit>Innstilling til Stortinget fra finanskomiteen</Doktit>
  <Kildedok>Dokument 8:173 S (2023–2024)</Kildedok>
  <Ingress>Innstilling fra finanskomiteen om ...</Ingress>
  <TilStortinget>Til Stortinget</TilStortinget>
</Startseksjon>
```

XPath for tittel: `//Startseksjon/Ingress/text()`  
XPath for sesjon: `//Startseksjon/Aar/text()`  
XPath for kildedokument: `//Startseksjon/Kildedok/text()`

### `<Hovedseksjon>` — innhold

```xml
<Hovedseksjon>
  <Kapittel Num="Nei">
    <Tittel>Bakgrunn</Tittel>
    <A Type="Innrykk">...</A>
    <A Type="Blanklinjeminnrykk">«sitert forslagstekst»</A>
    <Subsek2>                          <!-- underseksjoner i Dok 8 -->
      <Tittel>...</Tittel>
      <A Type="Innrykk">...</A>
    </Subsek2>
  </Kapittel>

  <Kapittel Num="Nei">
    <Tittel>Komiteens merknader</Tittel>
    <A Type="Innrykk">
      <Uth Type="Sperret">Komiteen, ... fra Høyre, ...</Uth>
      ...tekst...
    </A>
  </Kapittel>

  <!-- KUN i innstillinger, ikke i Dok 8: -->
  <ForslagFraMindretall Num="Nei">
    <Tittel>Forslag fra mindretall</Tittel>
    <Fraksjon Fra="Høyre, Fremskrittspartiet, Venstre, Kristelig Folkeparti">
      <Tittel>Forslag fra Høyre, ...</Tittel>
      <Forslag Nr="1">
        <Tittel>Forslag 1</Tittel>
        <A Type="Innrykk">Stortinget ber regjeringen ...</A>
      </Forslag>
    </Fraksjon>
  </ForslagFraMindretall>
</Hovedseksjon>
```

#### XPath — forslagspunkter (mindretall)
```python
# Alle mindretallsforslag
tree.xpath("//ForslagFraMindretall/Fraksjon/Forslag")

# Fraksjonsinfo (kommaseparert, fulle partinavn)
tree.xpath("//ForslagFraMindretall/Fraksjon/@Fra")

# Tekst i ett forslag (Nr-atributt er tall som streng)
forslag.xpath("A//text()")

# Forslagsnummer
forslag.get("Nr")  # → "1", "2", ...
```

**Viktig:** `@Fra` inneholder fulle partinavn (`"Høyre, Fremskrittspartiet, Venstre, Kristelig Folkeparti"`), ikke forkortelser. Parser må normalisere til standard ID-er.

#### Inline-formatering i `<A>`
```xml
<A Type="Innrykk">
  <Uth Type="Sperret">Komiteen, ... fra Høyre, ...</Uth>
  , viser til ...
</A>
```
- `<Uth Type="Sperret">` = sperret (spaced-out) skrift, brukes for partilistene i komiteens merknader
- `<Uth Type="Halvfet">` = halvfet
- `<Uth Type="Kursiv">` = kursiv
- For LLM-input: bruk `''.join(element.itertext())` — henter all tekst inkl. inline

#### Andre elementer i `<Hauptseksjon>`
- `<Figgrp>` med `<Fig>` — figurer/bilder (ignorér for analyse)
- `<Tbl>` med `<table>` (DITA/DocBook-stil) — tabeller (ignorér eller flatten)
- `<Kilde>` — kildehenvisning for figur/tabell

### `<Sluttseksjon>` — tilråding

```xml
<Sluttseksjon>
  <KomTilrading Num="Nei">
    <Tittel>Komiteens tilråding</Tittel>    <!-- eller bare "Forslag" i Dok 8 -->
    <A Type="Innrykk">Komiteens tilråding fremmes av ...</A>
    <Komiteen>
      <A Type="Innrykk">Komiteen har for øvrig ...</A>
    </Komiteen>
    <ForslagTilVedtak>
      <VedtakS>                            <!-- S = stortingsvedtak -->
        <Tittel>vedtak:</Tittel>
        <A Type="Innrykk">Dokument 8:173 S ... – vedtas ikke.</A>
      </VedtakS>
      <!-- eller VedtakL for lovvedtak -->
    </ForslagTilVedtak>
  </KomTilrading>
  <Sign>...</Sign>
</Sluttseksjon>
```

```python
# Komiteens tilråding (stortingsvedtak)
tree.xpath("//KomTilrading/ForslagTilVedtak/VedtakS")
tree.xpath("//KomTilrading/ForslagTilVedtak/VedtakL")

# Vedtakstekst
''.join(vedtak_element.itertext()).strip()
```

**Forskjell mellom Dok 8 og innstilling i `<KomTilrading>`:**
- Innstilling: `<Tittel>Komiteens tilråding</Tittel>` + vedtakstekst er flertallets vedtak (ofte "vedtas ikke" for forkastede Dok 8)
- Dok 8: `<Tittel>Forslag</Tittel>` + vedtakstekst er selve forslagspunktet fra proposisjonene

### `<Vedlegg>`

I innstillinger: finnes, men er tom peker til PDF:
```xml
<Vedlegg>
  <VedlNr>Vedlegg</VedlNr>
  <A Type="Innrykk">Vedlegg finnes kun i PDF, se merknadsfelt.</A>
</Vedlegg>
```

I Dok 8 (ny DTD): **mangler helt** — Dok 8-XML er fullstendig uten vedlegg-element.

### Oppsummering: Ny DTD XPath-tabell

| Hva | XPath |
|-----|-------|
| Ingress/tittel | `//Startseksjon/Ingress/text()` |
| Sesjon | `//Startseksjon/Aar/text()` |
| Kildedokument | `//Startseksjon/Kildedok/text()` |
| Seksjoner | `//Hovedseksjon/Kapittel` |
| Seksjonstittel | `Kapittel/Tittel/text()` |
| Seksjonens tekst | `''.join(Kapittel.itertext())` |
| Mindretallsforslag (finnes?) | `bool(tree.xpath("//ForslagFraMindretall"))` |
| Alle fraksjoner | `//ForslagFraMindretall/Fraksjon` |
| Fraksjonspartier | `Fraksjon/@Fra` |
| Forslagspunkter i fraksjon | `Fraksjon/Forslag` |
| Forslagsnummer | `Forslag/@Nr` |
| Forslagstekst | `''.join(Forslag.itertext())` |
| Komiteens vedtak (S) | `//KomTilrading/ForslagTilVedtak/VedtakS` |
| Komiteens vedtak (L) | `//KomTilrading/ForslagTilVedtak/VedtakL` |
| Vedtakstekst | `''.join(vedtak.itertext())` |

---

## DTD 2: Gammel innstilling (`innst_xml.dtd`, før 2016–2017)

### Rootelement

```xml
<innstilling id="Nr.109.2011">
```

**Lowercase gjennomgående.** Atributt `id` inneholder innstillingsnummeret.

### Toppnivåstruktur

```
<innstilling>
  <front>       ← metadata
  <til>         ← hoveddokument
  <sign>        ← signatur
  <vedlegg>     ← faktisk innhold (brev, etc.) — IKKE bare PDF-peker!
```

### `<front>` — metadata

```xml
<front>
  <titgrp>
    <innst>Innst. 109 S</innst>           <!-- med U+00A0 mellom nr og S -->
    <aar>(2010–2011)</aar>
    <doktit>Innstilling til Stortinget fra transport- og kommunikasjonskomiteen</doktit>
    <kildedok>Dokument 8:175 S (2009–2010)</kildedok>
    <tit>Innstilling fra transport- og kommunikasjonskomiteen om ...</tit>
  </titgrp>
</front>
```

```python
tree.xpath("//front/titgrp/tit/text()")   # full tittel
tree.xpath("//front/titgrp/aar/text()")   # sesjon
tree.xpath("//front/titgrp/kildedok/text()")
```

### `<til>` — hoveddokument

```xml
<til>
  <a type="innrykk">Til Stortinget</a>
  <kapittel>
    <tit>Sammendrag</tit>
    <a type="innrykk">...</a>
  </kapittel>
  <kapittel>
    <tit>Komiteens merknader</tit>
    <uttalelse>
      <a type="innrykk">
        <uttal>Komiteens flertall, ... fra Arbeiderpartiet, ...</uttal>
        , viser til ...
      </a>
    </uttalelse>
    <blksit>
      <sitat>«sitert tekst»</sitat>
    </blksit>
    ...
  </kapittel>

  <forslagfram>
    <tit>Forslag fra mindretall</tit>
    <fraksjon fra="Arbeiderpartiet, Sosialistisk Venstreparti og Senterpartiet">
      <tit>Forslag fra Arbeiderpartiet, ...</tit>
      <forsl nr="1">
        <tit>Forslag 1</tit>
        <a type="innrykk">Dokument 8:175 S ... – vedlegges protokollen.</a>
      </forsl>
    </fraksjon>
  </forslagfram>

  <komtilr>
    <tit>Komiteens tilråding</tit>
    <uttalelse>...</uttalelse>
    <forslag-til-vedtak>
      <tit>vedtak:</tit>
      <vedtak>
        <vedtakstekst>
          <a type="uinnrykk">Stortinget ber regjeringen ...</a>
        </vedtakstekst>
      </vedtak>
    </forslag-til-vedtak>
  </komtilr>
</til>
```

#### XPath — forslagspunkter
```python
tree.xpath("//forslagfram/fraksjon/forsl")    # alle forslagspunkter
fraksjon.get("fra")                            # partier (lowercase attributt)
forsl.get("nr")                                # forslagsnummer (lowercase)
''.join(forsl.itertext())                      # forslagstekst inkl. U+00A0
```

#### XPath — vedtak
```python
tree.xpath("//komtilr/forslag-til-vedtak/vedtak/vedtakstekst")
```

**Merk:** Vedtakstekst i gammel DTD har `<a type="uinnrykk">` (uten innrykk), ikke `<a type="innrykk">`. Atributtverdier er lowercase.

### `<vedlegg>` — faktisk innhold

I gammel DTD inneholder `<vedlegg>` **faktisk tekstinnhold** (f.eks. brev fra departement), ikke bare en PDF-peker. Strukturen er `<vedlnr>`, `<kapittel>`, `<seksjon>`, `<a>` — samme logikk som `<til>`.

### Oppsummering: Gammel innstilling XPath-tabell

| Hva | XPath |
|-----|-------|
| Full tittel | `//front/titgrp/tit/text()` |
| Sesjon | `//front/titgrp/aar/text()` |
| Kildedokument | `//front/titgrp/kildedok/text()` |
| Seksjoner | `//til/kapittel` |
| Seksjonstittel | `kapittel/tit/text()` |
| Mindretallsforslag (finnes?) | `bool(tree.xpath("//forslagfram"))` |
| Alle fraksjoner | `//forslagfram/fraksjon` |
| Fraksjonspartier | `fraksjon/@fra` |
| Forslagspunkter | `fraksjon/forsl` |
| Forslagsnummer | `forsl/@nr` |
| Forslagstekst | `''.join(forsl.itertext())` |
| Komiteens vedtak | `//komtilr/forslag-til-vedtak/vedtak/vedtakstekst` |
| Vedtakstekst | `''.join(vedtakstekst.itertext())` |

---

## DTD 3: Gammel Dok 8 (`innst_xml.dtd` eller eldre, Dok 8-varianten)

### Rootelement

```xml
<dok8>
```

### Toppnivåstruktur

```
<dok8>
  <forslag>
    <doktit>   ← dokumentreferanse
    <tit>      ← "fra stortingsrepresentantene ..."
    <fnr>      ← "Dokument 8:175 S"
    <aar>      ← "(2009–2010)"
    <sak>      ← hoveddokument
```

### `<sak>` — hoveddokument

```xml
<sak>
  <tit>Representantforslag fra ... om å utrede ...</tit>
  <til>Til Stortinget</til>
  <seksjon>
    <tit>Bakgrunn</tit>
    <a>...</a>
    <subsek>
      <tit>Samfunnsbygging</tit>
      <a>...</a>
    </subsek>
  </seksjon>
  <fremforsl>
    <tit>Forslag</tit>
    <a>Forslagsstillerne vil på denne bakgrunn fremme følgende</a>
    <utit><uth type="sperret">forslag:</uth></utit>
    <a>Stortinget ber regjeringen utrede ...</a>   ← selve forslagsteksten!
  </fremforsl>
  <dato>18. juni 2010</dato>
</sak>
```

**Kritisk:** Det er ingen strukturell tag som isolerer hvert forslagspunkt. `<fremforsl>` inneholder en blanding av innledende tekst og selve forslaget som plain `<a>`-elementer. Forslagspunkter kan ikke hentes deterministisk med XPath alene.

**Strategi for gammel Dok 8:** Hent all tekst i `//fremforsl` og send til LLM for ekstraksjon, eller nøy deg med `//sak/fremforsl/a[last()]/text()` som en heuristikk for siste (typisk det faktiske forslaget).

---

## Encoding og spesielle tegn

Alle fire filer:
- **Content-Type:** `text/xml; charset=utf-8`
- **Faktisk encoding:** UTF-8 (verifisert — `lxml.etree.fromstring(bytes)` parser uten feil)
- **Ingen XML-deklarasjon** (`<?xml version="1.0"?>`) i noen av filene

| Tegn | Unicode | Forekomster (per fil) | Kilde |
|------|---------|----------------------|-------|
| `–` EN DASH | U+2013 | 2–17 | Årsintervaller: "(2023–2024)" |
| ` ` NBSP | U+00A0 | 1–8 | Mellom nummer og S: "109 S", "175 S" |

**Konsekvenser:**
- `replace('\u2013', '-')` ved behov for normalisering av årsintervaller
- `replace('\u00a0', ' ')` ved tekstekstraksjon for å unngå \xa0 i output
- `''.join(element.itertext()).replace('\u00a0', ' ').strip()` er trygg standardoppskrift

Ingen XML-entities observert utover standard (`&amp;`, `&lt;`, etc.). `lxml` håndterer disse automatisk.

---

## Sammenligning: Ny vs. gammel DTD

| Egenskap | Ny DTD (2016–) | Gammel innstilling | Gammel Dok 8 |
|----------|---------------|-------------------|--------------|
| Rootelement | `<Innstilling>` | `<innstilling>` | `<dok8>` |
| Case | PascalCase | lowercase | lowercase |
| Mindretallsforslag | `//ForslagFraMindretall/Fraksjon/Forslag` | `//forslagfram/fraksjon/forsl` | Ikke strukturert |
| Fraksjon-atributt | `@Fra` | `@fra` | N/A |
| Fraksjonsformat | Fulle navn: "Høyre, FrP, ..." | Fulle navn: "Ap, SV og Sp" (med "og") | N/A |
| Vedtakstekst | `//KomTilrading/ForslagTilVedtak/VedtakS` | `//komtilr/forslag-til-vedtak/vedtak/vedtakstekst` | N/A |
| Vedlegg | Tom PDF-peker | Faktisk innhold (brev, etc.) | Finnes ikke |
| Dok 8-rootelement | Samme `<Innstilling>` | N/A | `<dok8>` |
| Forslagstekst i Dok 8 | `//KomTilrading/ForslagTilVedtak/VedtakS` | N/A | `//fremforsl/a` (ustrukturert) |

**Avgjørende skille:** Ny DTD har `<ForslagFraMindretall>` kun i innstillinger, IKKE i Dok 8. Ny Dok 8 har forslagspunktet i `<KomTilrading>/<ForslagTilVedtak>`. Begge bruker `<Innstilling>` som rot.

---

## Anbefaling: Én parsermodul med tre ruter

```python
def parse_dokument(xml_bytes: bytes) -> DokumentStruktur:
    tree = etree.fromstring(xml_bytes)
    root_tag = tree.tag  # case-sensitive

    if root_tag == "Innstilling":
        # Ny DTD — gjelder både innstilling og Dok 8
        if tree.xpath("//ForslagFraMindretall"):
            return _parse_ny_innstilling(tree)
        else:
            return _parse_ny_dok8(tree)

    elif root_tag == "innstilling":
        # Gammel DTD innstilling
        return _parse_gammel_innstilling(tree)

    elif root_tag == "dok8":
        # Gammel DTD Dok 8 — begrenset strukturell parsing
        return _parse_gammel_dok8(tree)

    else:
        raise ValueError(f"Ukjent rootelement: {root_tag!r}")
```

**Svar på spørsmålet:** Én parsermodul er riktig. Forgreningspunktet er `tree.tag` (tre mulige verdier: `"Innstilling"`, `"innstilling"`, `"dok8"`). Intern logikk deles via hjelpefunksjoner siden ny innstilling og ny Dok 8 har identisk struktur bortsett fra `<ForslagFraMindretall>`.

**Det hardeste tilfellet er gammel Dok 8** (`<dok8>`): forslagspunktene er ikke strukturelt isolert. Her er to alternativer:
1. Hent `//fremforsl`-teksten samlet og send til LLM for ekstraksjon (mindre deterministisk)
2. Bruk `//sak/fremforsl/a[last()]` som heuristikk for selve forslaget (fungerer i enkle tilfeller)

For primærbrukstilfelle (saker fra 2016– med ny DTD) trenger vi ikke å prioritere gammel Dok 8 i første implementering. Innstillingen (`<Innstilling>`) er primærdokumentet og dekker 100 % av ferdigbehandlede saker.

---

## Neste steg

1. Implementer `app/services/publikasjon.py` — HTTP-henting av XML via `/eksport/publikasjon?publikasjonid=...`
2. Implementer `app/steps/xml_parser.py` med `parse_dokument()` og de tre rutene
3. Start med `_parse_ny_innstilling()` — dekker primærbrukstilfelle
4. Test mot `inns-202425-176s` og `inns-201011-109` (begge er i `tests/fixtures/spike/`)
5. Gammel Dok 8 (`<dok8>`) kan parkeres til vi har behov for analyse av saker fra før 2016
