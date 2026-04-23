# Domene: Stortinget og norsk politikk

Dette dokumentet inneholder domenekunnskap som er nødvendig for å bygge korrekt saksanalyse. Les dette før du skriver prompts eller analyselogikk.

## Dokumenttyper

Stortinget behandler flere typer dokumenter. Analysen må tilpasses typen.

### Representantforslag (Dokument 8)

Forslag fremmet av en eller flere stortingsrepresentanter (ikke regjeringen). Referanseformat: "Dok 8:123 S (2024-2025)" hvor `S` betyr Stortinget (ikke lovvedtak) og `L` betyr lovforslag.

Struktur:
- **Bakgrunn/begrunnelse** — hvorfor forslaget fremmes
- **Forslagstekst** — selve forslagspunktene, nummererte

Viktig: Forslagspunktene er det juridisk operative. Bakgrunnen er argumentasjon. Skill disse tydelig i analysen.

### Proposisjoner

Regjeringens forslag til Stortinget. To hovedtyper:

- **Prop. L** — lovforslag (endring av lov)
- **Prop. S** — stortingsvedtak (budsjett, traktater, samtykke, m.m.)

Referanseformat: "Prop. 45 L (2024-2025)".

Struktur er tyngre enn Dok 8: bakgrunn, gjeldende rett, departementets vurdering, høringsinstansenes syn, lovtekst/vedtakstekst.

### Meldinger til Stortinget (Meld. St.)

Regjeringens orienteringer og strategidokumenter. Ikke direkte operative — Stortinget tar dem "til etterretning" eller "vedlegger protokollen", evt. fatter egne vedtak basert på dem. Ofte lange (100+ sider) og brede.

### Innstillinger (Innst.)

Komiteens behandling av en sak. Inneholder komiteens vurdering og forslag til vedtak. Her kommer også partienes merknader — ofte første gang du ser hvordan partiene faktisk posisjonerer seg. Viktig kilde for fremtidig prediksjonsmodell.

**I vår arkitektur er innstillingen primærdokumentet** når den er tilgjengelig, fordi den både inneholder komiteens behandling OG originalforslaget (som vedlegg). Mindretallsforslag fra fraksjoner fremgår eksplisitt med `<Fraksjon Fra="...">`-tagger i XML-en.

## Språklige nyanser som har betydning

Dette er KRITISK for analysekvalitet. Forslagsteksters verbvalg bestemmer forpliktelsesgrad:

| Formulering | Betydning |
|---|---|
| "Stortinget ber regjeringen **utrede**…" | Svakest. Be om rapport/vurdering. Ingen forpliktelse til handling. |
| "Stortinget ber regjeringen **vurdere**…" | Også svak. Regjeringen kan konkludere med å ikke gjøre noe. |
| "Stortinget ber regjeringen **legge frem**…" | Middels. Krever konkret leveranse (f.eks. lovforslag), men innholdet er åpent. |
| "Stortinget ber regjeringen **komme tilbake til Stortinget med**…" | Middels/sterk. Krever retur til Stortinget for ny behandling. |
| "Stortinget ber regjeringen **sørge for**…" / "**sikre**…" | Sterk. Forventet resultat. |
| "Stortinget ber regjeringen **gjennomføre**…" / "**innføre**…" | Sterkest. Konkret handling pålagt. |

Analysen må fange dette. Et forslag om å "utrede X" er politisk helt forskjellig fra å "innføre X", selv om temaet er det samme.

## Fraksjoner og mindretallsforslag

I komitébehandlingen dannes ofte fraksjoner — grupperinger av partier som står sammen om merknader og forslag. XML-tagger som `<Fraksjon Fra="H, FrP">` angir eksplisitt hvilke partier som står bak hver merknad og hvert mindretallsforslag.

Vanlige konstellasjoner:
- **"Flertallet"** = partiene som har flertall i komiteen
- **"Mindretallet"** = resten
- Innimellom finnes **flere mindretall** (f.eks. "et annet mindretall" eller "et tredje mindretall") når uenigheten er gradert

Hver fraksjon kan fremme egne forslag som ender opp i `<ForslagFraMindretall>`. Disse voteres over i plenum, men faller typisk (fordi de er fremmet av mindretallet).

Komiteens tilråding (`<KomTilrading>` med `<ForslagTilVedtak>`) er flertallets innstilling — det er dette Stortinget primært voterer over.

## Komitésystemet

Saker fordeles til en av Stortingets fagkomiteer. Komitétilhørighet påvirker hvilke partier/representanter som blir saksordførere og hvordan saken behandles. Komitéstrukturen endres noen ganger mellom stortingsperioder.

Eksempler på faste komiteer: Finanskomiteen, Kommunal- og forvaltningskomiteen, Transport- og kommunikasjonskomiteen, Arbeids- og sosialkomiteen, Helse- og omsorgskomiteen, Utenriks- og forsvarskomiteen, Justiskomiteen, Utdannings- og forskningskomiteen, Energi- og miljøkomiteen, Kontroll- og konstitusjonskomiteen, Familie- og kulturkomiteen, Næringskomiteen.

## Partier (stortingsperioden 2025–2029)

Standardforkortelser som brukes konsistent:
- **A** — Arbeiderpartiet
- **H** — Høyre
- **FrP** — Fremskrittspartiet
- **SV** — Sosialistisk Venstreparti
- **Sp** — Senterpartiet
- **R** — Rødt
- **V** — Venstre
- **KrF** — Kristelig Folkeparti
- **MDG** — Miljøpartiet De Grønne

Partisammensetningen etter valget 2025 må verifiseres via Stortingets API — ikke anta at sammensetningen er identisk med forrige periode.

**Merk:** I XML-en kan partikoder forekomme i ulike varianter (`H`, `Høyre`, `Høyre Fra="H"`). Parse defensivt og normaliser til standardforkortelsen.

## Saksgang

Forenklet flyt for et representantforslag:
1. **Fremming** i Stortinget
2. **Komitébehandling** — inkluderer evt. åpen høring
3. **Innstilling** fra komiteen
4. **Debatt og votering** i plenum
5. **Vedtak** — typisk: bifalt, forkastet, eller "vedlegges protokollen"

Merk: "Vedlegges protokollen" betyr i praksis at forslaget ikke blir vedtatt, men heller ikke formelt forkastet. Vanlig utfall for representantforslag som faller.

## Hva analysen skal fange

For hvert dokument:

1. **Strukturell informasjon** — dokumenttype, referansenummer, forslagstillere/avsender, dato, komité, saksfelt.

2. **Hva problemet er** — hvordan forslagstillerne/regjeringen beskriver problemstillingen.

3. **Hva som faktisk foreslås** — hvert forslagspunkt isolert og ordrett (eller nær-ordrett). Ikke slå sammen punkter. Ikke tolk bort nyanser. Hentes direkte fra XML `<Forslag>` og `<VedtakS>`/`<VedtakL>`.

4. **Forpliktelsesgrad per forslagspunkt** — basert på verbtabellen over. LLM-klassifisering.

5. **Begrunnelse/argumentasjon** — hvilke verdier, hensyn og fakta forslagstillerne bygger på. LLM-sammendrag.

6. **Politiske dimensjoner** — hvilke akser saken beveger seg på. Marker som tolkning.

7. **Kobling til eksisterende politikk** — reversering? opptrapping? nytt? Marker som tolkning når usikkert.

8. **Fraksjonsoversikt** — hvilke partier har fremmet mindretallsforslag, og hva er forskjellen fra flertallets tilråding. Hentes direkte fra XML.

## Fallgruver

- **Ikke forveksle bakgrunnsbeskrivelsen med forslaget.** Bakgrunnen kan beskrive et stort problem; forslaget kan være et lite steg.
- **Ikke utvid forslaget.** Hvis teksten sier "utrede", skriv "utrede" — ikke "innføre".
- **Ikke anta partitilhørighet påvirker innhold.** Vurder forslaget på egne premisser. Partitilhørighet er metadata.
- **Vær forsiktig med "implisitte" forslag.** Hvis noe ikke står i forslagsteksten, står det ikke der.
- **Skill mellom opprinnelig forslag og komitens tilråding.** Et Dok 8-forslag kan bli omformulert, delt opp eller sammenslått når komiteen tilrår. Analysen bør vise begge hvis de er forskjellige.
