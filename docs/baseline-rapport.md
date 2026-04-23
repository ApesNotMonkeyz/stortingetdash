# Baseline-analyse — Stortinget voteringsmønstre

Generert: 2026-04-21

> **Stopp-og-evaluer-steg.** Les denne rapporten og vurder tallene før
> prediksjonsmodulen (lag 1–2) bygges videre. Tallene her bestemmer hvilke
> regler som er empirisk verifiserte og pålitelige nok til å bruke.

---

## Datagrunnlag

- Sesjoner i databasen: 2021-2022, 2022-2023, 2023-2024, 2024-2025
- Totalt voteringer: 7218
- Totalt parti-resultat-rader: 74482
- Partier representert: A, FrP, H, KrF, MDG, PF, R, SV, Sp, Uav, V

Tall basert på lite data (n < 10) er merket ⚠ og bør ikke brukes som grunnlag for regler.

---

## Beregning 0: Voteringsstruktur og seleksjonsbias

### Korrekt forståelse av «mindretallsforslag»

«Mindretallsforslag» er forslag fremmet av mindretallet **i komiteen** — partier som
ikke fikk komitéflertall for sin posisjon. Det er **ikke** automatisk forslag fra
opposisjonspartier generelt.

Støre-regjeringen er en **mindretallsregjering** uten flertall i Stortinget.
Konsekvens: opposisjonen har ofte flertall i komiteene, og regjeringens versjon
havner i mindretall. Regjeringspartiene fremmer da **egne** mindretallsforslag i
plenum — og stemmer FOR disse. Tilrådingen er ofte opposisjonens versjon, som
regjeringen stemmer MOT.

Voteringstemaet inneholder «på vegne av PARTI» som identifiserer forslagsstilleren.
Mindretallsforslag klassifiseres nå i tre grupper:

| Kategori | Forslagsstiller | Forventet data-retning (majority_vote) | Betydning |
| --- | --- | --- | --- |
| mindretallsforslag_rp | Minst ett regjeringsparti | **mot** (mot tilrådingen) | Støtter egne forslag |
| mindretallsforslag_opp | Utelukkende opposisjonspartier | **for** (for tilrådingen) | Motarbeider opp-forslag |
| mindretallsforslag_ukjent | Parti ikke identifisert fra tema | — | — |

### Enstemmige voteringer er ikke i databasen

Stortingets API returnerer tomme voteringsresultatlister for **enstemmige voteringer**
(`votering_resultat_type=5`). Databasen inneholder kun *omstridte* voteringer.
FOR-rater nedenfor gjelder utelukkende omstridte saker.

### Regjeringssammensetning per periode

| Regjering | Fra (inkl.) | Til (ekskl.) | Partier |
| --------- | ----------- | ------------ | ------- |
| Støre I   | 2021-10-14  | 2025-01-30   | A, Sp   |
| Støre II  | 2025-01-30  | (sittende)   | A       |

Sp er regjeringsparti for voteringer t.o.m. 2025-01-29. Fra 2025-01-30 behandles Sp som opposisjonsparti.

### Voteringstype-distribusjon

| Voteringstype               | Antall voteringer |
| --------------------------- | ----------------- |
| Mindretallsforslag (RP)     | 131               |
| Mindretallsforslag (opp)    | 4741              |
| Mindretallsforslag (ukjent) | 46                |
| Komiteens tilråding         | 798               |
| Alternativ votering         | 882               |
| Annet / prosedyre           | 620               |

### Stemme-semantikk og FOR-rate

**`for_stemmer`** = stemte **for tilrådingen** (komiteens flertallsposisjon).
**`mot_stemmer`** = stemte **mot tilrådingen** = for det alternative forslagets vedtagelse.

FOR-rate = andel (votering × parti) der partiet stemte FOR tilrådingen.

Forventet FOR-rate for regjeringspartier:
- **mindretallsforslag_rp ≈ 0 %**: regjeringen stemmer MOT tilrådingen (dvs. FOR egne forslag).
- **mindretallsforslag_opp ≈ 100 %**: regjeringen stemmer FOR tilrådingen (dvs. MOT opposisjonens forslag).
- **Proposisjon + tilråding ≈ 100 %**: regjeringen støtter tilrådingen på egne proposisjoner.

### FOR-rate for regjeringspartier per (dok-type, voteringstype)

| Dok-type     | Voteringstype               | FOR-andel (rp) | n (votering×parti) |
| ------------ | --------------------------- | -------------- | ------------------ |
| Lovforslag   | Alternativ votering         | 48.5%          | 264                |
| Lovforslag   | Annet / prosedyre           | 1.7%           | 345                |
| Lovforslag   | Mindretallsforslag (opp)    | 99.2%          | 2546               |
| Lovforslag   | Mindretallsforslag (RP)     | 0.0%           | 127                |
| Lovforslag   | Mindretallsforslag (ukjent) | 62.5%          | 8                  |
| Lovforslag   | Komiteens tilråding         | 4.7%           | 921                |
| Proposisjon  | Mindretallsforslag (opp)    | 99.5%          | 1327               |
| Proposisjon  | Mindretallsforslag (RP)     | 0.0%           | 49                 |
| Proposisjon  | Mindretallsforslag (ukjent) | 100.0%         | 8                  |
| Proposisjon  | Komiteens tilråding         | 24.6%          | 126                |
| dok=3        | Mindretallsforslag (opp)    | 97.9%          | 190                |
| Repr.forslag | Alternativ votering         | 49.6%          | 1245               |
| Repr.forslag | Annet / prosedyre           | 4.5%           | 664                |
| Repr.forslag | Mindretallsforslag (opp)    | 99.6%          | 3573               |
| Repr.forslag | Mindretallsforslag (RP)     | 0.0%           | 38                 |
| Repr.forslag | Mindretallsforslag (ukjent) | 100.0%         | 21                 |
| Repr.forslag | Komiteens tilråding         | 18.6%          | 221                |
| Grunnlov     | Annet / prosedyre           | 0.0%           | 21                 |
| Grunnlov     | Mindretallsforslag (opp)    | 28.6%          | 7                  |
| Grunnlov     | Mindretallsforslag (RP)     | 9.1%           | 11                 |
| Grunnlov     | Komiteens tilråding         | 0.0%           | 13                 |
| Innstilling  | Alternativ votering         | 50.0%          | 16                 |
| Innstilling  | Mindretallsforslag (opp)    | 97.1%          | 68                 |
| Innstilling  | Mindretallsforslag (ukjent) | 100.0%         | 9                  |
| Innstilling  | Komiteens tilråding         | 0.0%           | 9                  |
| dok=7        | Alternativ votering         | 50.0%          | 10                 |
| dok=7        | Annet / prosedyre           | 17.6%          | 17                 |
| dok=7        | Mindretallsforslag (opp)    | 98.1%          | 53                 |
| dok=7        | Mindretallsforslag (ukjent) | 88.5%          | 26                 |

**Tolkning:**
- mindretallsforslag_rp + FOR ≈ 0 %: ✓ Forventet — regjeringen stemmer MOT tilrådingen (FOR egne forslag).
- mindretallsforslag_opp + FOR ≈ 100 %: ✓ Forventet — regjeringen stemmer FOR tilrådingen (MOT opposisjonsforslag).
- Avvik i opp-kategorien: forhandlede pakker (regjeringen støtter opposisjonsforslag som del av flertallsforlik).
- Tilråding + lav FOR: ✓ Forventet for mindretallsregjering — opposisjonens versjon er tilrådingen.

> **Konklusjon beregning 0:** Semantikken er bekreftet: `for_stemmer` = for tilrådingen,
> `mot_stemmer` = for alternativet. For prediksjon: RP-parti på RP-forslag → predict «mot».
> RP-parti på Opp-forslag → predict «for». Avvik er forhandlede flertallspakker.

---

## Beregning 1: Parti-saksfelt-profil (FOR-andel, alle omstridte voteringer)

For hvert parti: andel omstridte voteringer der partiet stemte FOR, per saksfelt.
Ekskluderer alternativvoteringer (50/50 per konstruksjon).
Brukes som empirisk prior for prediksjonsmodellen.

| Parti | FOR-andel (alle omstridte) | n    |
| ----- | -------------------------- | ---- |
| A     | 75.8%                      | 6132 |
| FrP   | 58.9%                      | 6150 |
| H     | 65.6%                      | 6157 |
| KrF   | 68.7%                      | 6152 |
| MDG   | 48.9%                      | 6120 |
| PF    | 36.5%                      | 4314 |
| R     | 68.3%                      | 3709 |
| SV    | 50.7%                      | 6191 |
| Sp    | 71.0%                      | 6136 |
| Uav   | 91.6%                      | 1826 |
| V     | 81.5%                      | 4301 |

> Tall gjelder omstridte voteringer. Enstemmige mangler fra DB.
> Reell FOR-andel er høyere — spesielt for konsensusnære partier.

### A og Sp — FOR-andel per saksfelt (n ≥ 5)

| Parti | Saksfelt                     | FOR-andel | n   |
| ----- | ---------------------------- | --------- | --- |
| A     | Havner                       | 95.6%     | 113 |
| Sp    | Havner                       | 95.6%     | 113 |
| A     | Ferger                       | 93.6%     | 140 |
| Sp    | Ferger                       | 92.9%     | 140 |
| A     | Riksrevisjonen               | 92.0%     | 25  |
| A     | Helseinstitusjoner           | 90.8%     | 173 |
| Sp    | Kongen                       | 90.0%     | 70  |
| A     | Statens pensjonsfond         | 88.6%     | 70  |
| Sp    | Statens pensjonsfond         | 88.6%     | 70  |
| A     | Husbanken                    | 88.2%     | 255 |
| A     | Norges bank                  | 88.1%     | 67  |
| Sp    | Riksrevisjonen               | 88.0%     | 25  |
| A     | Merverdiavgift               | 88.0%     | 216 |
| Sp    | Merverdiavgift               | 88.0%     | 216 |
| A     | Fylkeskommunenes økonomi     | 87.9%     | 422 |
| A     | Sjøfart                      | 87.9%     | 289 |
| Sp    | Norges bank                  | 87.7%     | 65  |
| Sp    | Sikkerhet til sjøs           | 87.7%     | 138 |
| A     | Husdyr                       | 87.7%     | 211 |
| Sp    | Sjøfart                      | 87.5%     | 289 |
| A     | Samferdsel                   | 87.4%     | 239 |
| A     | Luftfart                     | 87.4%     | 190 |
| Sp    | Luftfart                     | 87.4%     | 190 |
| A     | Vassdragsregulering          | 87.3%     | 110 |
| A     | Sykehus                      | 87.1%     | 272 |
| A     | Rusmidler                    | 87.1%     | 340 |
| A     | Sikkerhet til sjøs           | 87.1%     | 139 |
| A     | Kommunenes økonomi           | 86.9%     | 551 |
| A     | Psykisk helse                | 86.8%     | 456 |
| A     | Jernbaner                    | 86.8%     | 189 |
| Sp    | Reindrift                    | 86.8%     | 151 |
| Sp    | Husdyr                       | 86.7%     | 211 |
| Sp    | Husbanken                    | 86.7%     | 255 |
| Sp    | Atomvåpen                    | 86.7%     | 30  |
| A     | Industri                     | 86.5%     | 193 |
| A     | Høyere utdanning             | 86.3%     | 271 |
| A     | Utdanning                    | 86.2%     | 225 |
| A     | Kartverk                     | 86.0%     | 93  |
| Sp    | Kartverk                     | 86.0%     | 93  |
| Sp    | Industri                     | 86.0%     | 193 |
| Sp    | Høyere utdanning             | 86.0%     | 271 |
| A     | Boligsaker                   | 85.8%     | 386 |
| A     | Bergverk                     | 85.7%     | 84  |
| A     | Kringkasting                 | 85.7%     | 42  |
| Sp    | Kringkasting                 | 85.7%     | 42  |
| A     | Barnevern                    | 85.7%     | 251 |
| A     | Forurensning                 | 85.5%     | 643 |
| A     | Reindrift                    | 85.4%     | 151 |
| Sp    | Miljøvern                    | 85.4%     | 322 |
| A     | Omsorgstjenester             | 85.4%     | 328 |
| A     | Sykdommer                    | 85.3%     | 307 |
| Sp    | Fylkeskommunenes økonomi     | 85.3%     | 422 |
| A     | Kongen                       | 85.1%     | 74  |
| A     | Statlig eierskap             | 85.1%     | 188 |
| A     | Voksenopplæring              | 85.0%     | 140 |
| Sp    | Voksenopplæring              | 85.0%     | 140 |
| A     | Frivillighet                 | 84.9%     | 405 |
| Sp    | Samferdsel                   | 84.9%     | 238 |
| Sp    | Psykisk helse                | 84.8%     | 455 |
| A     | Fylker                       | 84.7%     | 236 |
| Sp    | Rusmidler                    | 84.7%     | 340 |
| Sp    | Sykdommer                    | 84.7%     | 307 |
| Sp    | Jernbaner                    | 84.7%     | 189 |
| A     | Miljøvern                    | 84.6%     | 325 |
| A     | Regjeringen                  | 84.6%     | 188 |
| A     | Reiselivsnæring              | 84.5%     | 168 |
| Sp    | Reiselivsnæring              | 84.5%     | 168 |
| A     | Næringsutvikling             | 84.4%     | 430 |
| Sp    | Regjeringen                  | 84.4%     | 186 |
| Sp    | Helseinstitusjoner           | 84.4%     | 173 |
| A     | Bygningsvesen                | 84.4%     | 307 |
| Sp    | Frivillighet                 | 84.2%     | 404 |
| A     | Naturskader                  | 84.0%     | 119 |
| Sp    | Kommunenes økonomi           | 84.0%     | 551 |
| A     | Fangst                       | 84.0%     | 50  |
| A     | Atomvåpen                    | 83.9%     | 31  |
| A     | Lokalforvaltning             | 83.7%     | 300 |
| Sp    | Økonomisk samarbeid          | 83.5%     | 85  |
| A     | Sosiale tjenester            | 83.5%     | 254 |
| Sp    | Svalbard                     | 83.4%     | 163 |
| Sp    | Boligsaker                   | 83.4%     | 386 |
| A     | Vegtrafikk                   | 83.3%     | 287 |
| Sp    | Forskning                    | 83.2%     | 399 |
| A     | Internasjonalt samarbeid     | 83.1%     | 419 |
| A     | Svangerskap                  | 83.1%     | 295 |
| Sp    | Internasjonalt samarbeid     | 83.0%     | 418 |
| A     | Svalbard                     | 82.9%     | 164 |
| A     | Utenrikshandel               | 82.9%     | 240 |
| A     | Priser og konkurranseforhold | 82.9%     | 572 |
| A     | Kunst                        | 82.9%     | 70  |
| Sp    | Kunst                        | 82.9%     | 70  |
| Sp    | Departementer                | 82.8%     | 384 |
| Sp    | Sykehus                      | 82.7%     | 272 |
| A     | Fn                           | 82.7%     | 133 |
| Sp    | Sosiale tjenester            | 82.7%     | 254 |
| Sp    | Statseiendommer              | 82.7%     | 173 |
| A     | Jordbruk                     | 82.6%     | 213 |
| A     | Departementer                | 82.6%     | 385 |
| Sp    | Utdanning                    | 82.6%     | 224 |
| Sp    | Forsvarsmateriell            | 82.6%     | 132 |
| Sp    | Forurensning                 | 82.6%     | 654 |
| A     | Økonomisk samarbeid          | 82.6%     | 86  |
| Sp    | Statlig eierskap             | 82.4%     | 188 |
| Sp    | Fn                           | 82.4%     | 131 |
| A     | Folkehelse                   | 82.4%     | 421 |
| Sp    | Naturskader                  | 82.4%     | 119 |
| A     | Post                         | 82.4%     | 17  |
| Sp    | Post                         | 82.4%     | 17  |
| A     | Fagskoler                    | 82.3%     | 96  |
| A     | Skoler                       | 82.3%     | 186 |
| A     | Forskning                    | 82.2%     | 400 |
| A     | Forsvarsmateriell            | 82.2%     | 135 |
| A     | Distriktspolitikk            | 82.2%     | 191 |
| A     | Statseiendommer              | 82.2%     | 174 |
| A     | Massemedier                  | 82.1%     | 84  |
| Sp    | Barnevern                    | 82.1%     | 251 |
| A     | Sysselsetting                | 82.1%     | 312 |
| A     | Funksjonshemmede             | 82.0%     | 300 |
| A     | Landbruksprodukter           | 82.0%     | 161 |
| A     | Olje og gass                 | 81.9%     | 277 |
| Sp    | Funksjonshemmede             | 81.9%     | 299 |
| A     | Statslån                     | 81.8%     | 292 |
| Sp    | Statslån                     | 81.8%     | 292 |
| Sp    | Veterinærvesen               | 81.8%     | 77  |
| A     | Naturvern                    | 81.8%     | 412 |
| A     | Kulturvern                   | 81.7%     | 208 |
| A     | Helsepersonell               | 81.7%     | 454 |
| A     | Vegvesen                     | 81.7%     | 257 |
| Sp    | Sysselsetting                | 81.7%     | 306 |
| Sp    | Omsorgstjenester             | 81.7%     | 327 |
| Sp    | Næringsutvikling             | 81.6%     | 429 |
| Sp    | Handel                       | 81.6%     | 38  |
| A     | Bibliotek og litteratur      | 81.5%     | 65  |
| A     | Kommuner                     | 81.5%     | 482 |
| A     | Kultur                       | 81.5%     | 157 |
| A     | Elektrisitet                 | 81.4%     | 667 |
| A     | Næringsliv                   | 81.4%     | 344 |
| Sp    | Fagskoler                    | 81.2%     | 96  |
| Sp    | Utviklingssamarbeid          | 81.2%     | 213 |
| Sp    | Kulturvern                   | 81.2%     | 207 |
| A     | Energi                       | 81.2%     | 467 |
| A     | Samer                        | 81.1%     | 122 |
| Sp    | Næringsliv                   | 81.1%     | 344 |
| A     | Samfunnssikkerhet            | 81.1%     | 417 |
| Sp    | Samer                        | 81.0%     | 121 |
| Sp    | Polarområder                 | 81.0%     | 126 |
| Sp    | Bergverk                     | 81.0%     | 84  |
| A     | Utviklingssamarbeid          | 80.8%     | 214 |
| Sp    | Massemedier                  | 80.7%     | 83  |
| A     | Kommunikasjonsteknologi      | 80.6%     | 495 |
| A     | Veterinærvesen               | 80.5%     | 77  |
| A     | Ungdommer                    | 80.5%     | 210 |
| Sp    | Trossamfunn                  | 80.5%     | 128 |
| Sp    | Priser og konkurranseforhold | 80.4%     | 572 |
| A     | Helsevesen                   | 80.3%     | 814 |
| A     | Polarområder                 | 80.3%     | 127 |
| A     | Idrett                       | 80.3%     | 127 |
| A     | Skattefradrag                | 80.2%     | 81  |
| Sp    | Skattefradrag                | 80.2%     | 81  |
| Sp    | Vegtrafikk                   | 80.1%     | 287 |
| Sp    | Landbruksprodukter           | 80.1%     | 161 |
| A     | Forbrukersaker               | 80.1%     | 351 |
| Sp    | Nato                         | 80.0%     | 45  |
| A     | Verftsindustri               | 80.0%     | 20  |
| A     | Universiteter                | 80.0%     | 105 |
| Sp    | Universiteter                | 80.0%     | 105 |
| A     | Skatteadministrasjon         | 80.0%     | 30  |
| Sp    | Bibliotek og litteratur      | 80.0%     | 65  |
| Sp    | Jordbruk                     | 79.9%     | 214 |
| Sp    | Samfunnssikkerhet            | 79.9%     | 417 |
| Sp    | Naturvern                    | 79.9%     | 412 |
| Sp    | Utenrikshandel               | 79.8%     | 238 |
| A     | Avgifter                     | 79.8%     | 247 |
| Sp    | Avgifter                     | 79.8%     | 247 |
| Sp    | Fylker                       | 79.7%     | 236 |
| Sp    | Svangerskap                  | 79.6%     | 299 |
| A     | Familie                      | 79.6%     | 284 |
| Sp    | Skoler                       | 79.6%     | 186 |
| Sp    | Folkehelse                   | 79.5%     | 419 |
| A     | Grunnskole                   | 79.3%     | 164 |
| Sp    | Distriktspolitikk            | 79.1%     | 191 |
| A     | Handel                       | 78.9%     | 38  |
| Sp    | Vegvesen                     | 78.9%     | 256 |
| A     | Lotteri og spill             | 78.7%     | 75  |
| Sp    | Lotteri og spill             | 78.7%     | 75  |
| A     | Trossamfunn                  | 78.6%     | 131 |
| Sp    | Utenrikssaker                | 78.6%     | 182 |
| A     | Nato                         | 78.3%     | 46  |
| Sp    | Elektrisitet                 | 78.2%     | 671 |
| A     | Likestilling                 | 77.9%     | 195 |
| Sp    | Kommunikasjonsteknologi      | 77.9%     | 493 |
| A     | Utenrikssaker                | 77.8%     | 185 |
| Sp    | Stortingsrepresentanter      | 77.8%     | 63  |
| A     | Kriminalomsorg               | 77.7%     | 103 |
| Sp    | Olje og gass                 | 77.6%     | 290 |
| A     | Høgskoler                    | 77.5%     | 111 |
| Sp    | Høgskoler                    | 77.5%     | 111 |
| A     | Varehandel                   | 77.5%     | 102 |
| A     | Fengsler                     | 77.4%     | 62  |
| A     | Landbruk                     | 77.3%     | 185 |
| Sp    | Vassdragsregulering          | 77.3%     | 110 |
| Sp    | Likestilling                 | 77.2%     | 193 |
| A     | Trygder                      | 76.8%     | 630 |
| A     | Videregående skoler          | 76.8%     | 99  |
| A     | Språk                        | 76.8%     | 198 |
| Sp    | Skatteadministrasjon         | 76.7%     | 30  |
| Sp    | Språk                        | 76.6%     | 197 |
| Sp    | Forsvar                      | 76.6%     | 154 |
| A     | Personvern                   | 76.4%     | 225 |
| A     | Stortingsrepresentanter      | 76.2%     | 63  |
| Sp    | Landbruk                     | 76.1%     | 184 |
| Sp    | Personvern                   | 76.0%     | 225 |
| A     | Studiefinansiering           | 75.9%     | 83  |
| Sp    | Forbrukersaker               | 75.8%     | 351 |
| Sp    | Den norske kirke             | 75.8%     | 66  |
| Sp    | Kommuner                     | 75.7%     | 481 |
| Sp    | Lokalforvaltning             | 75.7%     | 300 |
| Sp    | Bygningsvesen                | 75.7%     | 304 |
| Sp    | Trygder                      | 75.6%     | 624 |
| Sp    | Kultur                       | 75.5%     | 155 |
| A     | Forsvar                      | 75.5%     | 159 |
| A     | Fiskerier                    | 75.5%     | 106 |
| Sp    | Fiskerier                    | 75.5%     | 106 |
| Sp    | Statsbudsjettet              | 75.4%     | 760 |
| A     | Statsbudsjettet              | 75.3%     | 761 |
| A     | Barn                         | 75.2%     | 335 |
| A     | Barnehager                   | 75.0%     | 160 |
| A     | Sivilrett                    | 75.0%     | 76  |
| Sp    | Sivilrett                    | 75.0%     | 76  |
| Sp    | Verftsindustri               | 75.0%     | 20  |
| Sp    | Idrett                       | 75.0%     | 128 |
| Sp    | Energi                       | 74.9%     | 471 |
| A     | Lønn og inntekt              | 74.8%     | 270 |
| Sp    | Videregående skoler          | 74.7%     | 99  |
| Sp    | Studiefinansiering           | 74.7%     | 83  |
| Sp    | Familie                      | 74.6%     | 284 |
| Sp    | Helsevesen                   | 74.4%     | 821 |
| A     | Statsforvaltning             | 74.2%     | 151 |
| Sp    | Helsepersonell               | 74.0%     | 462 |
| Sp    | Fredsarbeid                  | 73.8%     | 42  |
| A     | Toll                         | 73.8%     | 42  |
| Sp    | Toll                         | 73.8%     | 42  |
| Sp    | Innvandrere                  | 73.7%     | 392 |
| Sp    | Strafferett                  | 73.7%     | 152 |
| A     | Den norske kirke             | 73.5%     | 68  |
| Sp    | Lønn og inntekt              | 73.5%     | 264 |
| A     | Innvandrere                  | 73.4%     | 394 |
| A     | Banker                       | 73.3%     | 101 |
| A     | Strafferett                  | 73.2%     | 153 |
| A     | Eu/eøs                       | 73.2%     | 481 |
| Sp    | Militært personell           | 73.2%     | 41  |
| A     | Privatskoler                 | 73.1%     | 78  |
| Sp    | Ungdommer                    | 72.7%     | 209 |
| Sp    | Rettferdsvederlag            | 72.7%     | 22  |
| Sp    | Fiskeomsetning               | 72.7%     | 55  |
| Sp    | Grunnskole                   | 72.6%     | 164 |
| A     | Skogbruk                     | 72.5%     | 51  |
| Sp    | Skogbruk                     | 72.5%     | 51  |
| Sp    | Banker                       | 72.3%     | 101 |
| A     | Havbruk                      | 72.2%     | 108 |
| A     | Fredsarbeid                  | 72.1%     | 43  |
| Sp    | Fangst                       | 72.0%     | 50  |
| A     | Nordisk samarbeid            | 71.9%     | 32  |
| Sp    | Varehandel                   | 71.6%     | 102 |
| Sp    | Sivilombudet                 | 71.4%     | 7   |
| A     | Spesialundervisning          | 71.4%     | 14  |
| Sp    | Spesialundervisning          | 71.4%     | 14  |
| A     | Skatter                      | 71.1%     | 159 |
| A     | Fiskeomsetning               | 70.9%     | 55  |
| Sp    | Eu/eøs                       | 70.9%     | 481 |
| Sp    | Barnehager                   | 70.4%     | 159 |
| Sp    | Skatter                      | 70.4%     | 159 |
| A     | Politi og påtalemyndighet    | 69.9%     | 246 |
| Sp    | Stortinget                   | 69.7%     | 76  |
| A     | Aksjer                       | 69.7%     | 76  |
| Sp    | Aksjer                       | 69.7%     | 76  |
| Sp    | Barn                         | 69.3%     | 335 |
| Sp    | Privatskoler                 | 69.2%     | 78  |
| A     | Arbeidsliv                   | 68.9%     | 264 |
| Sp    | Kriminalomsorg               | 68.9%     | 103 |
| Sp    | Redningstjeneste             | 68.8%     | 32  |
| Sp    | Politi og påtalemyndighet    | 68.7%     | 243 |
| Sp    | Internasjonal rett           | 68.6%     | 70  |
| A     | Arbeidsvilkår                | 68.6%     | 245 |
| A     | Arbeidsmiljø                 | 68.5%     | 108 |
| A     | Militært personell           | 68.2%     | 44  |
| A     | Rettferdsvederlag            | 68.2%     | 22  |
| A     | Internasjonal rett           | 68.1%     | 72  |
| A     | Traktater                    | 67.9%     | 28  |
| Sp    | Traktater                    | 67.9%     | 28  |
| Sp    | Nordisk samarbeid            | 67.7%     | 31  |
| Sp    | Statsforvaltning             | 67.3%     | 153 |
| Sp    | Arbeidsliv                   | 66.7%     | 258 |
| A     | Redningstjeneste             | 66.7%     | 33  |
| Sp    | Rettsvesen                   | 66.7%     | 87  |
| A     | Politiske partier            | 66.7%     | 33  |
| Sp    | Havbruk                      | 66.7%     | 108 |
| Sp    | Arbeidsvilkår                | 66.5%     | 239 |
| A     | Finanser                     | 65.9%     | 135 |
| A     | Menneskerettigheter          | 65.7%     | 327 |
| A     | Stortinget                   | 65.4%     | 81  |
| Sp    | Finanser                     | 65.2%     | 135 |
| Sp    | Menneskerettigheter          | 64.6%     | 325 |
| A     | Forsikring                   | 64.4%     | 59  |
| A     | Rettsvesen                   | 64.4%     | 87  |
| Sp    | Arbeidsmiljø                 | 63.9%     | 108 |
| Sp    | Fengsler                     | 62.9%     | 62  |
| Sp    | Politiske partier            | 62.9%     | 35  |
| A     | Sivilombudet                 | 62.5%     | 8   |
| Sp    | Fn-styrker                   | 61.5%     | 13  |
| Sp    | Forsikring                   | 61.0%     | 59  |
| A     | Fn-styrker                   | 57.1%     | 14  |
| A     | Statens personalpolitikk     | 57.0%     | 86  |
| Sp    | Statens personalpolitikk     | 57.0%     | 86  |
| Sp    | Europarådet                  | 55.6%     | 9   |
| A     | Valg                         | 55.6%     | 36  |
| A     | Domstoler                    | 54.9%     | 51  |
| Sp    | Domstoler                    | 54.9%     | 51  |
| Sp    | Valg                         | 54.1%     | 37  |
| A     | Europarådet                  | 50.0%     | 10  |
| A     | Grensespørsmål               | 50.0%     | 14  |
| Sp    | Grensespørsmål               | 50.0%     | 14  |
| A     | Grunnloven                   | 17.6%     | 34  |
| Sp    | Grunnloven                   | 12.5%     | 24  |

---

## Beregning 2: FOR-rate på omstridte tilrådinger (regjeringspartier)

Andel ganger regjeringspartiene stemte FOR på omstridte tilrådingsvoteringer.
Lav FOR-rate betyr at komiteen satte opposisjonens versjon som tilråding.

| Parti | FOR-andel (tilraading, omstridt) | n   |
| ----- | -------------------------------- | --- |
| A     | 10.0%                            | 797 |
| Sp    | 7.0%                             | 497 |

### Per saksfelt (n ≥ 5)

| Parti | Saksfelt                     | FOR-andel (tilraading) | n   |
| ----- | ---------------------------- | ---------------------- | --- |
| A     | Helseinstitusjoner           | 38.5%                  | 13  |
| Sp    | Helseinstitusjoner           | 38.5%                  | 13  |
| A     | Fangst                       | 36.4%                  | 11  |
| A     | Ferger                       | 33.3%                  | 6   |
| Sp    | Ferger                       | 33.3%                  | 6   |
| Sp    | Psykisk helse                | 32.0%                  | 50  |
| Sp    | Sykehus                      | 31.2%                  | 16  |
| A     | Sykdommer                    | 30.8%                  | 39  |
| Sp    | Sykdommer                    | 30.6%                  | 36  |
| Sp    | Samferdsel                   | 28.6%                  | 14  |
| A     | Psykisk helse                | 28.3%                  | 60  |
| A     | Vegvesen                     | 27.3%                  | 22  |
| A     | Sykehus                      | 26.3%                  | 19  |
| Sp    | Rusmidler                    | 25.8%                  | 31  |
| Sp    | Vegvesen                     | 25.0%                  | 16  |
| A     | Utdanning                    | 24.1%                  | 29  |
| A     | Samferdsel                   | 23.5%                  | 17  |
| A     | Høyere utdanning             | 23.5%                  | 17  |
| Sp    | Høyere utdanning             | 23.5%                  | 17  |
| A     | Vegtrafikk                   | 23.1%                  | 26  |
| Sp    | Sysselsetting                | 22.9%                  | 35  |
| A     | Omsorgstjenester             | 22.9%                  | 35  |
| A     | Rusmidler                    | 22.9%                  | 35  |
| Sp    | Vegtrafikk                   | 22.7%                  | 22  |
| Sp    | Omsorgstjenester             | 22.6%                  | 31  |
| Sp    | Veterinærvesen               | 22.2%                  | 9   |
| A     | Barnevern                    | 21.6%                  | 37  |
| A     | Svangerskap                  | 21.1%                  | 38  |
| Sp    | Svangerskap                  | 21.1%                  | 38  |
| A     | Politi og påtalemyndighet    | 20.9%                  | 43  |
| Sp    | Folkehelse                   | 20.8%                  | 53  |
| A     | Veterinærvesen               | 20.0%                  | 10  |
| A     | Arbeidsliv                   | 19.2%                  | 52  |
| A     | Husbanken                    | 18.2%                  | 22  |
| Sp    | Husbanken                    | 18.2%                  | 22  |
| Sp    | Fylker                       | 18.2%                  | 22  |
| A     | Folkehelse                   | 18.0%                  | 61  |
| A     | Ungdommer                    | 17.9%                  | 28  |
| A     | Sysselsetting                | 17.4%                  | 46  |
| Sp    | Helsevesen                   | 16.7%                  | 90  |
| A     | Helsepersonell               | 16.4%                  | 67  |
| Sp    | Funksjonshemmede             | 16.3%                  | 43  |
| A     | Merverdiavgift               | 16.0%                  | 25  |
| Sp    | Barnevern                    | 16.0%                  | 25  |
| Sp    | Merverdiavgift               | 16.0%                  | 25  |
| A     | Fylker                       | 16.0%                  | 25  |
| Sp    | Helsepersonell               | 15.9%                  | 63  |
| A     | Helsevesen                   | 15.7%                  | 102 |
| A     | Likestilling                 | 15.6%                  | 32  |
| Sp    | Boligsaker                   | 15.6%                  | 32  |
| A     | Funksjonshemmede             | 15.6%                  | 45  |
| Sp    | Personvern                   | 15.4%                  | 26  |
| Sp    | Jernbaner                    | 15.4%                  | 13  |
| A     | Idrett                       | 15.0%                  | 20  |
| A     | Personvern                   | 14.7%                  | 34  |
| A     | Boligsaker                   | 14.7%                  | 34  |
| Sp    | Utdanning                    | 14.3%                  | 21  |
| A     | Sosiale tjenester            | 14.3%                  | 28  |
| Sp    | Sosiale tjenester            | 14.3%                  | 28  |
| A     | Husdyr                       | 14.3%                  | 21  |
| A     | Jernbaner                    | 14.3%                  | 14  |
| Sp    | Kommuner                     | 13.6%                  | 44  |
| Sp    | Husdyr                       | 13.3%                  | 15  |
| A     | Lokalforvaltning             | 13.2%                  | 38  |
| Sp    | Sikkerhet til sjøs           | 12.5%                  | 16  |
| A     | Fagskoler                    | 12.5%                  | 16  |
| Sp    | Forurensning                 | 12.1%                  | 58  |
| A     | Sikkerhet til sjøs           | 11.8%                  | 17  |
| A     | Kommuner                     | 11.7%                  | 60  |
| Sp    | Fylkeskommunenes økonomi     | 11.6%                  | 43  |
| Sp    | Kommunikasjonsteknologi      | 11.6%                  | 69  |
| A     | Statslån                     | 11.4%                  | 35  |
| Sp    | Statslån                     | 11.4%                  | 35  |
| A     | Fylkeskommunenes økonomi     | 11.4%                  | 44  |
| A     | Forurensning                 | 11.3%                  | 62  |
| Sp    | Ungdommer                    | 11.1%                  | 18  |
| A     | Arbeidsmiljø                 | 11.1%                  | 18  |
| A     | Kommunikasjonsteknologi      | 11.0%                  | 73  |
| A     | Barn                         | 10.5%                  | 57  |
| Sp    | Frivillighet                 | 10.5%                  | 57  |
| A     | Reiselivsnæring              | 10.5%                  | 19  |
| A     | Luftfart                     | 10.5%                  | 19  |
| Sp    | Luftfart                     | 10.5%                  | 19  |
| A     | Strafferett                  | 10.5%                  | 19  |
| A     | Frivillighet                 | 10.3%                  | 58  |
| A     | Fengsler                     | 10.0%                  | 10  |
| A     | Naturvern                    | 9.7%                   | 62  |
| A     | Næringsutvikling             | 9.3%                   | 54  |
| Sp    | Internasjonalt samarbeid     | 8.9%                   | 56  |
| Sp    | Forskning                    | 8.9%                   | 45  |
| A     | Forskning                    | 8.7%                   | 46  |
| A     | Familie                      | 8.6%                   | 35  |
| Sp    | Kommunenes økonomi           | 8.5%                   | 59  |
| A     | Internasjonalt samarbeid     | 8.5%                   | 59  |
| A     | Miljøvern                    | 8.3%                   | 36  |
| A     | Industri                     | 8.0%                   | 25  |
| A     | Landbruksprodukter           | 8.0%                   | 25  |
| A     | Kommunenes økonomi           | 7.8%                   | 64  |
| A     | Finanser                     | 7.7%                   | 26  |
| Sp    | Samfunnssikkerhet            | 7.7%                   | 52  |
| Sp    | Sjøfart                      | 7.7%                   | 26  |
| A     | Sjøfart                      | 7.4%                   | 27  |
| Sp    | Eu/eøs                       | 7.2%                   | 69  |
| A     | Eu/eøs                       | 7.2%                   | 83  |
| A     | Samfunnssikkerhet            | 7.1%                   | 56  |
| Sp    | Naturskader                  | 7.1%                   | 14  |
| Sp    | Forsikring                   | 7.1%                   | 14  |
| A     | Privatskoler                 | 7.1%                   | 14  |
| Sp    | Arbeidsliv                   | 6.9%                   | 29  |
| Sp    | Departementer                | 6.9%                   | 58  |
| A     | Departementer                | 6.8%                   | 59  |
| A     | Kriminalomsorg               | 6.7%                   | 15  |
| A     | Naturskader                  | 6.7%                   | 15  |
| A     | Forsikring                   | 6.7%                   | 15  |
| A     | Avgifter                     | 6.5%                   | 31  |
| A     | Jordbruk                     | 6.2%                   | 32  |
| A     | Videregående skoler          | 6.2%                   | 16  |
| Sp    | Idrett                       | 6.2%                   | 16  |
| Sp    | Videregående skoler          | 6.2%                   | 16  |
| Sp    | Lotteri og spill             | 6.2%                   | 16  |
| A     | Trygder                      | 6.1%                   | 99  |
| A     | Innvandrere                  | 5.9%                   | 68  |
| A     | Lotteri og spill             | 5.9%                   | 17  |
| A     | Skoler                       | 5.6%                   | 18  |
| Sp    | Statsbudsjettet              | 5.3%                   | 75  |
| A     | Næringsliv                   | 5.1%                   | 39  |
| A     | Landbruk                     | 5.1%                   | 39  |
| Sp    | Rettsvesen                   | 5.0%                   | 20  |
| Sp    | Landbruksprodukter           | 5.0%                   | 20  |
| Sp    | Trygder                      | 4.9%                   | 81  |
| A     | Kultur                       | 4.8%                   | 21  |
| A     | Rettsvesen                   | 4.5%                   | 22  |
| Sp    | Likestilling                 | 4.3%                   | 23  |
| Sp    | Jordbruk                     | 4.2%                   | 24  |
| A     | Bygningsvesen                | 4.0%                   | 25  |
| Sp    | Lokalforvaltning             | 3.8%                   | 26  |
| A     | Statsforvaltning             | 3.7%                   | 27  |
| A     | Priser og konkurranseforhold | 3.7%                   | 54  |
| Sp    | Miljøvern                    | 3.4%                   | 29  |
| Sp    | Familie                      | 3.4%                   | 29  |
| A     | Språk                        | 3.4%                   | 29  |
| Sp    | Språk                        | 3.4%                   | 29  |
| Sp    | Innvandrere                  | 3.3%                   | 61  |
| A     | Statsbudsjettet              | 3.2%                   | 126 |
| Sp    | Barn                         | 3.0%                   | 33  |
| Sp    | Landbruk                     | 3.0%                   | 33  |
| Sp    | Naturvern                    | 2.5%                   | 40  |
| Sp    | Næringsutvikling             | 2.1%                   | 47  |
| Sp    | Energi                       | 2.0%                   | 49  |
| Sp    | Menneskerettigheter          | 1.8%                   | 57  |
| A     | Energi                       | 1.6%                   | 62  |
| A     | Menneskerettigheter          | 1.5%                   | 65  |
| Sp    | Elektrisitet                 | 1.4%                   | 69  |
| A     | Elektrisitet                 | 1.3%                   | 79  |
| A     | Lønn og inntekt              | 0.0%                   | 36  |
| Sp    | Lønn og inntekt              | 0.0%                   | 24  |
| Sp    | Næringsliv                   | 0.0%                   | 36  |
| Sp    | Finanser                     | 0.0%                   | 19  |
| A     | Samer                        | 0.0%                   | 15  |
| A     | Kunst                        | 0.0%                   | 11  |
| A     | Kulturvern                   | 0.0%                   | 33  |
| A     | Massemedier                  | 0.0%                   | 11  |
| Sp    | Kultur                       | 0.0%                   | 15  |
| Sp    | Samer                        | 0.0%                   | 15  |
| Sp    | Kunst                        | 0.0%                   | 9   |
| Sp    | Kulturvern                   | 0.0%                   | 32  |
| Sp    | Massemedier                  | 0.0%                   | 8   |
| A     | Redningstjeneste             | 0.0%                   | 10  |
| A     | Regjeringen                  | 0.0%                   | 15  |
| A     | Forsvar                      | 0.0%                   | 23  |
| A     | Forsvarsmateriell            | 0.0%                   | 15  |
| A     | Atomvåpen                    | 0.0%                   | 5   |
| A     | Utenrikshandel               | 0.0%                   | 27  |
| A     | Statseiendommer              | 0.0%                   | 25  |
| A     | Utenrikssaker                | 0.0%                   | 15  |
| A     | Fn                           | 0.0%                   | 18  |
| A     | Fn-styrker                   | 0.0%                   | 6   |
| A     | Europarådet                  | 0.0%                   | 5   |
| A     | Nordisk samarbeid            | 0.0%                   | 6   |
| A     | Økonomisk samarbeid          | 0.0%                   | 10  |
| A     | Utviklingssamarbeid          | 0.0%                   | 34  |
| A     | Polarområder                 | 0.0%                   | 22  |
| A     | Svalbard                     | 0.0%                   | 25  |
| A     | Nato                         | 0.0%                   | 7   |
| A     | Fredsarbeid                  | 0.0%                   | 10  |
| A     | Kongen                       | 0.0%                   | 6   |
| A     | Militært personell           | 0.0%                   | 10  |
| A     | Internasjonal rett           | 0.0%                   | 15  |
| Sp    | Redningstjeneste             | 0.0%                   | 9   |
| Sp    | Regjeringen                  | 0.0%                   | 13  |
| Sp    | Forsvar                      | 0.0%                   | 19  |
| Sp    | Forsvarsmateriell            | 0.0%                   | 12  |
| Sp    | Utenrikshandel               | 0.0%                   | 23  |
| Sp    | Politi og påtalemyndighet    | 0.0%                   | 22  |
| Sp    | Statseiendommer              | 0.0%                   | 24  |
| Sp    | Utenrikssaker                | 0.0%                   | 14  |
| Sp    | Fn                           | 0.0%                   | 14  |
| Sp    | Fn-styrker                   | 0.0%                   | 5   |
| Sp    | Nordisk samarbeid            | 0.0%                   | 5   |
| Sp    | Økonomisk samarbeid          | 0.0%                   | 9   |
| Sp    | Utviklingssamarbeid          | 0.0%                   | 31  |
| Sp    | Polarområder                 | 0.0%                   | 21  |
| Sp    | Svalbard                     | 0.0%                   | 24  |
| Sp    | Nato                         | 0.0%                   | 6   |
| Sp    | Fredsarbeid                  | 0.0%                   | 9   |
| Sp    | Kongen                       | 0.0%                   | 5   |
| Sp    | Militært personell           | 0.0%                   | 7   |
| Sp    | Internasjonal rett           | 0.0%                   | 14  |
| A     | Skatter                      | 0.0%                   | 28  |
| Sp    | Skatter                      | 0.0%                   | 28  |
| A     | Domstoler                    | 0.0%                   | 14  |
| A     | Sivilrett                    | 0.0%                   | 15  |
| A     | Høgskoler                    | 0.0%                   | 14  |
| A     | Grensespørsmål               | 0.0%                   | 5   |
| Sp    | Domstoler                    | 0.0%                   | 14  |
| Sp    | Sivilrett                    | 0.0%                   | 15  |
| Sp    | Kriminalomsorg               | 0.0%                   | 10  |
| Sp    | Fengsler                     | 0.0%                   | 5   |
| Sp    | Statsforvaltning             | 0.0%                   | 21  |
| Sp    | Høgskoler                    | 0.0%                   | 14  |
| Sp    | Grensespørsmål               | 0.0%                   | 5   |
| Sp    | Fagskoler                    | 0.0%                   | 14  |
| A     | Barnehager                   | 0.0%                   | 25  |
| A     | Politiske partier            | 0.0%                   | 9   |
| A     | Grunnskole                   | 0.0%                   | 16  |
| A     | Distriktspolitikk            | 0.0%                   | 24  |
| Sp    | Barnehager                   | 0.0%                   | 18  |
| Sp    | Politiske partier            | 0.0%                   | 7   |
| Sp    | Grunnskole                   | 0.0%                   | 12  |
| Sp    | Distriktspolitikk            | 0.0%                   | 24  |
| A     | Vassdragsregulering          | 0.0%                   | 11  |
| A     | Olje og gass                 | 0.0%                   | 31  |
| A     | Statlig eierskap             | 0.0%                   | 16  |
| A     | Reindrift                    | 0.0%                   | 13  |
| A     | Kartverk                     | 0.0%                   | 10  |
| Sp    | Vassdragsregulering          | 0.0%                   | 8   |
| Sp    | Olje og gass                 | 0.0%                   | 26  |
| Sp    | Reiselivsnæring              | 0.0%                   | 15  |
| Sp    | Statlig eierskap             | 0.0%                   | 16  |
| Sp    | Reindrift                    | 0.0%                   | 12  |
| Sp    | Kartverk                     | 0.0%                   | 10  |
| Sp    | Industri                     | 0.0%                   | 21  |
| A     | Fiskerier                    | 0.0%                   | 20  |
| A     | Handel                       | 0.0%                   | 5   |
| A     | Fiskeomsetning               | 0.0%                   | 12  |
| A     | Havbruk                      | 0.0%                   | 20  |
| A     | Varehandel                   | 0.0%                   | 9   |
| A     | Forbrukersaker               | 0.0%                   | 36  |
| A     | Bergverk                     | 0.0%                   | 7   |
| A     | Skogbruk                     | 0.0%                   | 11  |
| Sp    | Fiskerier                    | 0.0%                   | 20  |
| Sp    | Priser og konkurranseforhold | 0.0%                   | 49  |
| Sp    | Fiskeomsetning               | 0.0%                   | 12  |
| Sp    | Havbruk                      | 0.0%                   | 15  |
| Sp    | Varehandel                   | 0.0%                   | 9   |
| Sp    | Forbrukersaker               | 0.0%                   | 32  |
| Sp    | Bergverk                     | 0.0%                   | 6   |
| Sp    | Skogbruk                     | 0.0%                   | 11  |
| A     | Statens personalpolitikk     | 0.0%                   | 24  |
| A     | Arbeidsvilkår                | 0.0%                   | 41  |
| Sp    | Statens personalpolitikk     | 0.0%                   | 23  |
| Sp    | Avgifter                     | 0.0%                   | 28  |
| Sp    | Arbeidsvilkår                | 0.0%                   | 30  |
| Sp    | Arbeidsmiljø                 | 0.0%                   | 13  |
| A     | Universiteter                | 0.0%                   | 10  |
| A     | Studiefinansiering           | 0.0%                   | 15  |
| A     | Banker                       | 0.0%                   | 19  |
| A     | Trossamfunn                  | 0.0%                   | 20  |
| A     | Voksenopplæring              | 0.0%                   | 17  |
| Sp    | Universiteter                | 0.0%                   | 10  |
| Sp    | Studiefinansiering           | 0.0%                   | 15  |
| Sp    | Banker                       | 0.0%                   | 16  |
| Sp    | Trossamfunn                  | 0.0%                   | 19  |
| Sp    | Voksenopplæring              | 0.0%                   | 17  |
| A     | Toll                         | 0.0%                   | 9   |
| Sp    | Toll                         | 0.0%                   | 9   |
| Sp    | Skoler                       | 0.0%                   | 14  |
| A     | Valg                         | 0.0%                   | 9   |
| A     | Grunnloven                   | 0.0%                   | 7   |
| Sp    | Valg                         | 0.0%                   | 9   |
| Sp    | Grunnloven                   | 0.0%                   | 6   |
| Sp    | Privatskoler                 | 0.0%                   | 11  |
| Sp    | Bygningsvesen                | 0.0%                   | 10  |
| A     | Aksjer                       | 0.0%                   | 13  |
| Sp    | Aksjer                       | 0.0%                   | 12  |
| A     | Den norske kirke             | 0.0%                   | 15  |
| Sp    | Den norske kirke             | 0.0%                   | 13  |
| A     | Stortinget                   | 0.0%                   | 12  |
| Sp    | Stortinget                   | 0.0%                   | 10  |
| A     | Bibliotek og litteratur      | 0.0%                   | 10  |
| A     | Kringkasting                 | 0.0%                   | 6   |
| Sp    | Bibliotek og litteratur      | 0.0%                   | 10  |
| A     | Stortingsrepresentanter      | 0.0%                   | 6   |
| Sp    | Stortingsrepresentanter      | 0.0%                   | 5   |
| A     | Skattefradrag                | 0.0%                   | 12  |
| Sp    | Skattefradrag                | 0.0%                   | 12  |
| Sp    | Strafferett                  | 0.0%                   | 5   |

---

## Beregning 3: Fraksjon-til-plenum-konsistens

Datagrunnlag: 30 saker med fraksjonsinformasjon (ny_innstilling)
(av 309 forsoekte saker fra sesjonene 2023-2024, 2024-2025).

Maal: Naar XML inneholder `<ForslagFraMindretall>`, stemte partiene i plenum
konsistent med sin komitefraksjon-posisjon?
- Parti i mindretallsfraksjon: forventet aa stemme MOT tilraadingen.
- Parti i flertallsfraksjon: forventet aa stemme FOR tilraadingen.

### Samlet konsistensrate per parti

| Parti | Konsistente | Totalt | Konsistensrate |
| ----- | ----------- | ------ | -------------- |
| A | 3 | 30 | 10.0% |
| FrP | 11 | 29 | 37.9% |
| H | 14 | 30 | 46.7% |
| KrF | 10 | 29 | 34.5% |
| MDG | 12 | 28 | 42.9% |
| R | 8 | 23 | 34.8% |
| SV | 9 | 28 | 32.1% |
| Sp | 9 | 29 | 31.0% |
| V | 9 | 24 | 37.5% |

**Samlet konsistensrate (alle partier):** 34.0% (n=250)

- **Mindretallsfraksjon** (forventet MOT): 41.1% konsistente (n=124)
- **Flertallsfraksjon** (forventet FOR): 27.0% konsistente (n=126)

> **Konklusjon beregning 3:** Målt konsistensrate = **34.0%** (n=250 parti-sak-observasjoner).
>
> **Tolkning:** Den lave raten skyldes primært minoritetsregjerings-effekten (Støre 2021–2025):
> flertallspartier i komité stemmer hyppig MOT tilrådingen i plenum fordi tilrådingen er
> opposisjonens versjon. Mindretallssignalet (41.1%) er mer pålitelig enn flertallssignalet (27.0%).
>
> **Anbefaling:** `_FRAKSJON_KONFIDENS = 0.80` — konservativt gulv, ikke avledet direkte fra 34%.
> Re-evaluer ved overgang til majoritetsregjering (forventet vesentlig høyere konsistens).

---

## Beregning 4: Krysspress-saker

Voteringer der et regjeringsparti brøt med forventet retning. Totalt: 151

Forventet retning (ref. stemme-semantikk i beregning 0):
- mindretallsforslag_rp → MOT (regjeringen stemmer mot tilrådingen = for egne forslag)
- mindretallsforslag_opp → FOR (regjeringen stemmer for tilrådingen = mot opposisjonsforslag)
- proposisjon + tilråding → FOR

| Sesjon    | Dato       | Parti | Type                     | Forventet | Faktisk | For/Mot | Saksfelt                                                       |
| --------- | ---------- | ----- | ------------------------ | --------- | ------- | ------- | -------------------------------------------------------------- |
| 2021-2022 | 2022-02-10 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 19/27   | Regjeringen, Stortingsrepresentanter, Lønn og inntekt          |
| 2021-2022 | 2022-02-15 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 19/29   | Husdyr, Veterinærvesen                                         |
| 2021-2022 | 2022-02-15 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 11/17   | Husdyr, Veterinærvesen                                         |
| 2021-2022 | 2022-04-26 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 22/26   | Kultur, Reiselivsnæring, Næringsutvikling                      |
| 2021-2022 | 2022-04-26 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 12/16   | Kultur, Reiselivsnæring, Næringsutvikling                      |
| 2021-2022 | 2022-06-01 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/8     | Statsforfatning, Kongen, Grunnloven                            |
| 2021-2022 | 2022-06-01 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Sivilombudet, Stortinget                                       |
| 2021-2022 | 2022-06-01 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Menneskerettigheter, Stortinget                                |
| 2021-2022 | 2022-06-01 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Barnehager                                                     |
| 2021-2022 | 2023-01-12 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Den norske kirke, Trossamfunn, Kongen                          |
| 2021-2022 | 2023-01-12 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Landbruk, Grunnloven                                           |
| 2021-2022 | 2023-01-12 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 0/1     | Stortinget, Grunnloven                                         |
| 2021-2022 | 2023-01-12 | A     | Mindretallsforslag (RP)  | MOT       | FOR     | 1/0     | Norges bank, Grunnloven                                        |
| 2022-2023 | 2023-06-02 | A     | Komiteens tilråding      | FOR       | MOT     | 19/29   | Kommuner, Helsevesen, Sykdommer                                |
| 2022-2023 | 2023-06-02 | Sp    | Komiteens tilråding      | FOR       | MOT     | 11/17   | Kommuner, Helsevesen, Sykdommer                                |
| 2022-2023 | 2023-06-02 | A     | Komiteens tilråding      | FOR       | MOT     | 19/29   | Kommuner, Helsevesen, Sykdommer                                |
| 2022-2023 | 2023-06-02 | Sp    | Komiteens tilråding      | FOR       | MOT     | 11/17   | Kommuner, Helsevesen, Sykdommer                                |
| 2022-2023 | 2023-06-13 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 19/29   | Fylkeskommunenes økonomi, Kommunenes økonomi, Lokalforvaltning |
| 2022-2023 | 2023-06-13 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 12/16   | Fylkeskommunenes økonomi, Kommunenes økonomi, Lokalforvaltning |
| 2022-2023 | 2023-06-14 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 21/26   | Energi, Naturvern, Elektrisitet                                |
| 2022-2023 | 2023-06-14 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 10/18   | Energi, Naturvern, Elektrisitet                                |
| 2023-2024 | 2023-10-05 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 18/30   | Regjeringen                                                    |
| 2023-2024 | 2023-10-05 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 11/17   | Regjeringen                                                    |
| 2023-2024 | 2023-10-05 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 18/30   | Regjeringen                                                    |
| 2023-2024 | 2023-10-05 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 11/17   | Regjeringen                                                    |
| 2022-2023 | 2023-12-07 | A     | Mindretallsforslag (opp) | FOR       | MOT     | 19/28   | Kommuner, Helsevesen, Helsepersonell                           |
| 2022-2023 | 2023-12-07 | Sp    | Mindretallsforslag (opp) | FOR       | MOT     | 11/17   | Kommuner, Helsevesen, Helsepersonell                           |
| 2022-2023 | 2023-12-07 | A     | Komiteens tilråding      | FOR       | MOT     | 19/29   | Kommuner, Helsevesen, Helsepersonell                           |
| 2022-2023 | 2023-12-07 | Sp    | Komiteens tilråding      | FOR       | MOT     | 11/17   | Kommuner, Helsevesen, Helsepersonell                           |
| 2022-2023 | 2023-12-07 | A     | Komiteens tilråding      | FOR       | MOT     | 19/29   | Kommuner, Helsevesen, Helsepersonell                           |

*...og 121 til.*

---

## Beregning 5: Parti-par-korrelasjon

Andel voteringer der to partier stemte likt (samlet, n ≥ 5).
100% = alltid likt, 50% = tilfeldig.

|     | A     | FrP   | H     | KrF   | MDG   | PF    | R     | SV    | Sp    | Uav   | V     |
| --- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| A   | —     | 55.7% | 75.1% | 67.6% | 48.6% | 44.9% | 58.2% | 60.2% | 93.0% | 72.0% | 70.4% |
| FrP | 55.7% | —     | 65.4% | 58.9% | 38.7% | 46.7% | 36.0% | 31.1% | 55.0% | 62.9% | 55.1% |
| H   | 75.1% | 65.4% | —     | 71.9% | 46.3% | 44.6% | 42.9% | 43.1% | 70.4% | 65.8% | 73.7% |
| KrF | 67.6% | 58.9% | 71.9% | —     | 53.5% | 47.6% | 58.7% | 50.1% | 66.1% | 69.5% | 73.7% |
| MDG | 48.6% | 38.7% | 46.3% | 53.5% | —     | 59.7% | 68.3% | 64.7% | 48.8% | 46.4% | 62.2% |
| PF  | 44.9% | 46.7% | 44.6% | 47.6% | 59.7% | —     | 57.3% | 60.4% | 47.3% | 45.5% | 43.8% |
| R   | 58.2% | 36.0% | 42.9% | 58.7% | 68.3% | 57.3% | —     | 80.0% | 61.6% | 49.9% | 70.4% |
| SV  | 60.2% | 31.1% | 43.1% | 50.1% | 64.7% | 60.4% | 80.0% | —     | 60.7% | 51.3% | 55.4% |
| Sp  | 93.0% | 55.0% | 70.4% | 66.1% | 48.8% | 47.3% | 61.6% | 60.7% | —     | 62.5% | 66.1% |
| Uav | 72.0% | 62.9% | 65.8% | 69.5% | 46.4% | 45.5% | 49.9% | 51.3% | 62.5% | —     | 65.9% |
| V   | 70.4% | 55.1% | 73.7% | 73.7% | 62.2% | 43.8% | 70.4% | 55.4% | 66.1% | 65.9% | —     |

*Basert på 1435+ voteringer per par.*

---

## Beregning 6: Saksfelt-predikabilitet

Varians i andel FOR-stemmer per observasjon. Lav varians = forutsigbart saksfelt.
Terskel: varians < 0.05 = høy, < 0.15 = middels, ≥ 0.15 = lav predikabilitet.

| Saksfelt                     | Predikabilitet | Snitt FOR-andel | Varians | n obs. |
| ---------------------------- | -------------- | --------------- | ------- | ------ |
| Post                         | middels        | 80.3%           | 0.073   | 175    |
| Verftsindustri               | middels        | 83.6%           | 0.073   | 216    |
| Handel                       | middels        | 80.9%           | 0.079   | 405    |
| Kartverk                     | middels        | 80.9%           | 0.081   | 983    |
| Naturskader                  | middels        | 80.3%           | 0.083   | 1230   |
| Industri                     | middels        | 79.2%           | 0.087   | 1941   |
| Statlig eierskap             | middels        | 79.3%           | 0.088   | 2060   |
| Kunst                        | middels        | 78.2%           | 0.088   | 720    |
| Reiselivsnæring              | middels        | 79.0%           | 0.088   | 1740   |
| Kringkasting                 | middels        | 77.1%           | 0.089   | 453    |
| Sivilrett                    | middels        | 76.9%           | 0.089   | 784    |
| Reindrift                    | middels        | 79.2%           | 0.091   | 1548   |
| Merverdiavgift               | middels        | 78.7%           | 0.092   | 2249   |
| Skatteadministrasjon         | middels        | 77.0%           | 0.092   | 321    |
| Toll                         | middels        | 78.5%           | 0.093   | 413    |
| Statens pensjonsfond         | middels        | 79.7%           | 0.093   | 777    |
| Lotteri og spill             | middels        | 74.0%           | 0.094   | 784    |
| Traktater                    | middels        | 73.2%           | 0.094   | 344    |
| Departementer                | middels        | 78.4%           | 0.094   | 3991   |
| Varehandel                   | middels        | 75.9%           | 0.095   | 1150   |
| Banker                       | middels        | 76.0%           | 0.095   | 993    |
| Statsbudsjettet              | middels        | 77.8%           | 0.095   | 7791   |
| Den norske kirke             | middels        | 75.7%           | 0.096   | 695    |
| Skattefradrag                | middels        | 77.0%           | 0.096   | 803    |
| Frivillighet                 | middels        | 77.7%           | 0.096   | 4231   |
| Avgifter                     | middels        | 76.9%           | 0.096   | 2729   |
| Kommunenes økonomi           | middels        | 77.2%           | 0.097   | 5839   |
| Riksrevisjonen               | middels        | 76.7%           | 0.097   | 402    |
| Sosiale tjenester            | middels        | 76.9%           | 0.097   | 2665   |
| Vassdragsregulering          | middels        | 78.0%           | 0.097   | 1160   |
| Skatteavtaler                | middels        | 74.6%           | 0.097   | 65     |
| Forbrukersaker               | middels        | 76.1%           | 0.097   | 3662   |
| Barnevern                    | middels        | 75.9%           | 0.097   | 2691   |
| Massemedier                  | middels        | 74.1%           | 0.097   | 870    |
| Kulturvern                   | middels        | 77.4%           | 0.097   | 2209   |
| Fengsler                     | middels        | 71.5%           | 0.097   | 762    |
| Fylkeskommunenes økonomi     | middels        | 77.5%           | 0.097   | 4362   |
| Personvern                   | middels        | 75.4%           | 0.098   | 2373   |
| Bibliotek og litteratur      | middels        | 74.5%           | 0.098   | 663    |
| Svalbard                     | middels        | 78.6%           | 0.098   | 1724   |
| Statslån                     | middels        | 78.3%           | 0.098   | 3011   |
| Distriktspolitikk            | middels        | 76.6%           | 0.098   | 1973   |
| Priser og konkurranseforhold | middels        | 76.0%           | 0.098   | 6084   |
| Utenrikshandel               | middels        | 77.3%           | 0.098   | 2574   |
| Sjøfart                      | middels        | 77.0%           | 0.098   | 2929   |
| Internasjonalt samarbeid     | middels        | 77.0%           | 0.100   | 4379   |
| Kultur                       | middels        | 74.9%           | 0.100   | 1564   |
| Rusmidler                    | middels        | 75.5%           | 0.100   | 3625   |
| Stortingsrepresentanter      | middels        | 74.6%           | 0.100   | 687    |
| Husdyr                       | middels        | 75.7%           | 0.101   | 2220   |
| Næringsutvikling             | middels        | 75.3%           | 0.101   | 4542   |
| Utviklingssamarbeid          | middels        | 76.8%           | 0.101   | 2389   |
| Forskning                    | middels        | 76.1%           | 0.101   | 4290   |
| Næringsliv                   | middels        | 75.1%           | 0.101   | 3829   |
| Helseinstitusjoner           | middels        | 75.8%           | 0.101   | 1807   |
| Naturvern                    | middels        | 74.6%           | 0.102   | 4810   |
| Samferdsel                   | middels        | 74.7%           | 0.102   | 2519   |
| Vegvesen                     | middels        | 73.6%           | 0.102   | 2946   |
| Fangst                       | middels        | 76.3%           | 0.102   | 623    |
| Lokalforvaltning             | middels        | 75.0%           | 0.102   | 3298   |
| Eu/eøs                       | middels        | 74.5%           | 0.102   | 5128   |
| Likestilling                 | middels        | 73.2%           | 0.102   | 2124   |
| Bergverk                     | middels        | 75.4%           | 0.102   | 898    |
| Barn                         | middels        | 72.7%           | 0.102   | 3877   |
| Trossamfunn                  | middels        | 75.0%           | 0.102   | 1472   |
| Vegtrafikk                   | middels        | 73.8%           | 0.102   | 3495   |
| Samfunnssikkerhet            | middels        | 74.7%           | 0.102   | 4407   |
| Jernbaner                    | middels        | 74.3%           | 0.103   | 1994   |
| Luftfart                     | middels        | 75.2%           | 0.103   | 1922   |
| Voksenopplæring              | middels        | 74.5%           | 0.103   | 1662   |
| Fylker                       | middels        | 74.4%           | 0.103   | 2731   |
| Høyere utdanning             | middels        | 74.7%           | 0.103   | 3024   |
| Husbanken                    | middels        | 75.8%           | 0.103   | 2721   |
| Forsvar                      | middels        | 74.8%           | 0.103   | 1790   |
| Jordbruk                     | middels        | 74.4%           | 0.103   | 2266   |
| Strafferett                  | middels        | 71.2%           | 0.104   | 1771   |
| Statseiendommer              | middels        | 76.6%           | 0.104   | 1847   |
| Boligsaker                   | middels        | 75.0%           | 0.104   | 4040   |
| Kommunikasjonsteknologi      | middels        | 74.8%           | 0.104   | 5192   |
| Psykisk helse                | middels        | 73.5%           | 0.104   | 4855   |
| Innvandrere                  | middels        | 73.0%           | 0.104   | 4672   |
| Aksjer                       | middels        | 72.3%           | 0.104   | 758    |
| Grensespørsmål               | middels        | 75.4%           | 0.104   | 158    |
| Sykehus                      | middels        | 74.7%           | 0.104   | 2841   |
| Fn                           | middels        | 75.3%           | 0.104   | 1495   |
| Familie                      | middels        | 73.1%           | 0.105   | 3080   |
| Ferger                       | middels        | 74.4%           | 0.105   | 1475   |
| Høgskoler                    | middels        | 74.7%           | 0.105   | 1316   |
| Omsorgstjenester             | middels        | 74.3%           | 0.105   | 3400   |
| Redningstjeneste             | middels        | 76.5%           | 0.105   | 346    |
| Finanser                     | middels        | 70.3%           | 0.106   | 1577   |
| Utdanning                    | middels        | 73.3%           | 0.106   | 2542   |
| Politi og påtalemyndighet    | middels        | 70.3%           | 0.106   | 3130   |
| Økonomisk samarbeid          | middels        | 73.9%           | 0.106   | 910    |
| Universiteter                | middels        | 74.0%           | 0.106   | 1274   |
| Polarområder                 | middels        | 77.0%           | 0.106   | 1359   |
| Språk                        | middels        | 72.7%           | 0.106   | 2345   |
| Skoler                       | middels        | 73.6%           | 0.106   | 2159   |
| Folkehelse                   | middels        | 74.1%           | 0.106   | 4391   |
| Kommuner                     | middels        | 71.6%           | 0.107   | 5426   |
| Sikkerhet til sjøs           | middels        | 75.0%           | 0.107   | 1403   |
| Havner                       | middels        | 74.2%           | 0.107   | 1118   |
| Funksjonshemmede             | middels        | 74.0%           | 0.107   | 3154   |
| Skatter                      | middels        | 74.2%           | 0.108   | 1718   |
| Forsikring                   | middels        | 75.1%           | 0.108   | 620    |
| Utenrikssaker                | middels        | 73.2%           | 0.108   | 2282   |
| Stortingets forretningsorden | middels        | 72.1%           | 0.108   | 63     |
| Ungdommer                    | middels        | 72.0%           | 0.108   | 2341   |
| Arbeidsmiljø                 | middels        | 71.7%           | 0.109   | 1163   |
| Rettsvesen                   | middels        | 70.1%           | 0.109   | 1118   |
| Statens personalpolitikk     | middels        | 71.1%           | 0.109   | 910    |
| Sykdommer                    | middels        | 73.4%           | 0.110   | 3178   |
| Regjeringen                  | middels        | 73.8%           | 0.110   | 1949   |
| Studiefinansiering           | middels        | 75.0%           | 0.110   | 881    |
| Grunnskole                   | middels        | 72.8%           | 0.110   | 2387   |
| Energi                       | middels        | 74.0%           | 0.110   | 5054   |
| Kriminalomsorg               | middels        | 69.9%           | 0.110   | 1197   |
| Elektrisitet                 | middels        | 73.9%           | 0.111   | 7181   |
| Sivilombudet                 | middels        | 67.7%           | 0.111   | 152    |
| Internasjonal rett           | middels        | 72.2%           | 0.111   | 871    |
| Fagskoler                    | middels        | 73.5%           | 0.111   | 1086   |
| Idrett                       | middels        | 72.5%           | 0.112   | 1351   |
| Landbruksprodukter           | middels        | 73.0%           | 0.112   | 1643   |
| Fiskerier                    | middels        | 73.9%           | 0.112   | 1197   |
| Miljøvern                    | middels        | 73.1%           | 0.113   | 3582   |
| Forsvarsmateriell            | middels        | 73.6%           | 0.113   | 1461   |
| Trygder                      | middels        | 73.4%           | 0.113   | 6689   |
| Samer                        | middels        | 72.7%           | 0.114   | 1254   |
| Bygningsvesen                | middels        | 71.9%           | 0.114   | 3511   |
| Landbruk                     | middels        | 72.2%           | 0.115   | 1973   |
| Nato                         | middels        | 73.9%           | 0.115   | 510    |
| Videregående skoler          | middels        | 71.1%           | 0.116   | 1419   |
| Forurensning                 | middels        | 72.5%           | 0.118   | 7087   |
| Rettferdsvederlag            | middels        | 70.8%           | 0.118   | 239    |
| Olje og gass                 | middels        | 74.2%           | 0.118   | 3182   |
| Norges bank                  | middels        | 74.7%           | 0.119   | 686    |
| Privatskoler                 | middels        | 70.9%           | 0.119   | 1079   |
| Barnehager                   | middels        | 71.6%           | 0.119   | 1958   |
| Militært personell           | middels        | 68.4%           | 0.120   | 484    |
| Helsevesen                   | middels        | 70.3%           | 0.120   | 8921   |
| Atomvåpen                    | middels        | 70.1%           | 0.120   | 369    |
| Fiskeomsetning               | middels        | 71.9%           | 0.121   | 585    |
| Skogbruk                     | middels        | 73.0%           | 0.123   | 573    |
| Sysselsetting                | middels        | 71.5%           | 0.123   | 3396   |
| Domstoler                    | middels        | 69.8%           | 0.124   | 642    |
| Veterinærvesen               | middels        | 69.4%           | 0.125   | 977    |
| Arbeidsvilkår                | middels        | 68.2%           | 0.127   | 2734   |
| Helsepersonell               | middels        | 70.5%           | 0.127   | 4709   |
| Stortinget                   | middels        | 67.3%           | 0.127   | 1122   |
| Kongen                       | middels        | 72.0%           | 0.128   | 724    |
| Statsforvaltning             | middels        | 69.6%           | 0.128   | 1785   |
| Menneskerettigheter          | middels        | 67.3%           | 0.130   | 3932   |
| Lønn og inntekt              | middels        | 69.3%           | 0.131   | 2998   |
| Nordisk samarbeid            | middels        | 68.4%           | 0.131   | 381    |
| Arbeidsliv                   | middels        | 67.2%           | 0.132   | 2915   |
| Havbruk                      | middels        | 68.5%           | 0.134   | 1199   |
| Svangerskap                  | middels        | 69.3%           | 0.135   | 2969   |
| Europarådet                  | middels        | 65.5%           | 0.138   | 92     |
| Statsforfatning              | middels        | 24.4%           | 0.139   | 18     |
| Fredsarbeid                  | middels        | 67.9%           | 0.148   | 484    |
| Valg                         | middels        | 64.5%           | 0.149   | 570    |
| Fn-styrker                   | middels        | 67.5%           | 0.150   | 138    |
| Politiske partier            | lav            | 66.4%           | 0.159   | 444    |
| Spesialundervisning          | lav            | 60.1%           | 0.176   | 177    |
| Grunnloven                   | lav            | 34.7%           | 0.189   | 468    |

**Samlet:** varians=0.108, predikabilitet=middels

---

## Konklusjon: Hvilke regler er pålitelige nok til å bruke?

ℹ **Beregning 0 (semantikk bekreftet):** for=tilråding, mot=alternativt forslag. Repr.forslag_rp FOR-rate: 0.0% (n=38) — forventet ≈ 0 %. Repr.forslag_opp FOR-rate: 99.6% (n=3573) — forventet ≈ 100 %.

⚠ **151 krysspress-saker** (RP-forslag FOR: 1, Opp-forslag MOT: 55, Prop+tilråding MOT: 95). Se beregning 4.

❌ **Beregning 3 (fraksjon-til-plenum)** ikke gjennomført. Konfidens for signal 1 er empirisk ukjent. Sett placeholder 90%.

### Neste steg

1. **Evaluer tallene** — verifiser at mindretallsforslag_rp → ≈ 0 % FOR (regjeringen
   stemmer mot tilrådingen = for egne forslag), og mindretallsforslag_opp → ≈ 100 % FOR
   (stemmer for tilrådingen). Krysspress-saker skal nå være reelle unntak.
2. **Bygg lag 1–2** etter at baseline er verifisert.
3. **Gjennomfør beregning 3** (fraksjon-til-plenum) etter XML-kobling er klar.

---

*Rapport generert av `scripts/baseline_analyse.py` · 2026-04-21*