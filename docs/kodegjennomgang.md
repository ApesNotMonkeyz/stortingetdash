# Gjennomgang av Stortingetdash-koden

## Context

Brukeren har bedt om en forklaring av hva koden gjør og hvordan applikasjonen fungerer. Dette er et rent forklaringsoppdrag — ingen endringer skal gjøres. Planen her er en oppsummering som brukeren kan lese i output, ikke en endringsplan.

## Hva applikasjonen er

`stortingetdash` er en dashboard-applikasjon for norske stortingssaker, bygd i to deler:

1. **Frontend** (Next.js 16 + React 19, App Router): et dashboard som viser saker, representanter, partier, voteringer og AI-analyser.
2. **Backend** (Python / FastAPI): analyserer stortingsdokumenter ved hjelp av deterministisk XML-parsing + Claude for tolkning.

De snakker sammen via en Next.js API-proxy (`/api/analyse/[sak_id]/route.ts`) som videresender til backendens `/api/v1/analyse/{sak_id}`.

## Backend (Python / FastAPI)

### Entrypoint og ruter
- `backend/app/main.py`: FastAPI-app med structlog-logging, lifespan-initialisering av DB, `/health`.
- `backend/app/api/routes.py`: to endepunkter
  - `GET /api/v1/analyse/{sak_id}` → `Saksanalyse` (kjører steg 1–6)
  - `GET /api/v1/prediksjon/{sak_id}` → `Saksprediksjon` (lag 1–2; lag 3 ikke ferdig)
  - `?force=true` hopper over cache.

### Analyse-pipelinen (fase 1 — ferdig)
`backend/app/services/pipeline.py:23` orkestrerer:

| Steg | Hva skjer | LLM? |
|---|---|---|
| 1 | Hent saksmetadata fra Stortinget (`/eksport/sak?sakid=...&format=json`) | Nei |
| 2 | Last ned publikasjon som XML (HTML fallback) | Nei |
| 3 | Parse XML deterministisk → `DokumentStruktur` (seksjoner, mindretallsforslag, fraksjoner, tilråding) | Nei |
| 4 | Klassifiser forpliktelsesgrad på hvert forslagspunkt (utrede/vurdere/legge frem/komme tilbake/sikre/gjennomføre) | Ja |
| 5 | Innholdsanalyse (problemforståelse, løsningsforslag, argumentasjonslinjer) | Ja |
| 6 | Politisk kontekst (dimensjoner, kobling til eksisterende politikk) | Ja |

Ferdigbehandlede saker caches permanent; andre har 24 t TTL.

### Integrasjoner
- `services/stortinget.py`: httpx-klient mot `data.stortinget.no`, XML først, HTML-fallback. U+00A0 normaliseres før parsing.
- `services/xml_parser.py`: lxml + XPath mot `innstillinger.dtd`. Detekterer `ny_innstilling` / `ny_dok8` / `gammel_innstilling` fra rotelement. Ekstraherer `<ForslagFraMindretall>`, `<Fraksjon>`, `<KomTilrading>`, `<VedtakS>`, `<Vedlegg>`.
- `services/claude.py`: `AsyncAnthropic` innpakket med `tool_call()` som tvinger JSON-output (temperature=0) og logger token-bruk. Tool-input valideres direkte mot Pydantic (f.eks. `Innholdsanalyse.model_validate(result)`).
- `db/cache.py`: dual backend. Uten `DATABASE_URL` brukes in-memory dict; med URL brukes PostgreSQL-tabellen `saksanalyser` (sak_id PK, pub_id, analyse_json JSONB, opprettet, utloper).

### Prompts og schemaer
- `prompts/` har ett prompt-modul per tolkningssteg (innholdsanalyse, forpliktelsesklassifisering, politisk_kontekst, prediksjon) — norsk språk, XML-tagger, few-shot.
- `models/` har Pydantic v2-modeller: `Sak`, `DokumentStruktur`, `Forslagspunkt`, `Saksanalyse`, `Innholdsanalyse`, `PolitiskKontekst`, `Saksprediksjon`, `PartiPrediksjon`.

### Prediksjon (fase 2 — delvis)
`services/prediksjon_pipeline.py` + `steps/prediksjon_lag{1,2,3}.py`:
- **Lag 1 (ferdig):** fraksjonsinformasjon fra XML + regler (mindretallsforslag → typisk forkastet 0.80 konfidens; opposisjonsforslag → regjeringen imot ~99.6 %).
- **Lag 2 (delvis):** historisk mønstermatching fra voteringsdata i DB.
- **Lag 3 (skelett):** LLM-kall for kontroversielle saker.
- Cache-nøkkel inkluderer prompt-versjon (`lag1-3/v3`). Analyse-pipelinen har ikke prompt-hash i cache ennå.
- Scripts: `scripts/hent_voteringer.py`, `scripts/baseline_analyse.py`, `scripts/evaluer_prediksjon.py`.

## Frontend (Next.js)

### Arkitektur
- Next.js 16.2.4, React 19, App Router, Tailwind CSS 4, shadcn/ui, @base-ui/react, lucide-react.
- Server components som standard; `"use client"` brukes selektivt.
- `app/layout.tsx` er root layout (Geist-fonter).

### Visninger
Dashboardet har 5 hovedseksjoner (intern komponent-router, ikke filbasert routing):
- **Dashboard:** KPI-strip, dagsorden, voteringer, hemicycle-SVG.
- **Bills:** saksliste + detaljvisning med saksgang og AI-analysepanel.
- **Representatives / Parties / Votes/Committees.**

Nøkkelkomponenter: `components/dash/page-dashboard.tsx`, `components/dash/page-bills.tsx`, `components/dash/components.tsx` (Sparkline, Hemicycle, PartyVoteBar, MultiLine).

### Datalag
- `lib/stortinget/endpoints.ts` mapper Stortingets API.
- `lib/stortinget/config.ts` har fil-/memory-cache og rate limiter (90 req/min).
- `lib/stortinget/types.ts` har TypeScript-typer som speiler backendens Pydantic-modeller (`Saksanalyse`, `Forpliktelsesgrad`, `Sikkerhetsnivaa`).

### Analysepanel
`AnalysePanel` i `components/dash/page-bills.tsx` lar brukeren klikke "Hent analyse" → Next.js proxy (`app/api/analyse/[sak_id]/route.ts`) → backendens `/api/v1/analyse/{sak_id}` → viser innholdsanalyse, politisk kontekst og forslagspunkter med forpliktelsesgrad.

### `instrumentation.ts`
Kjører ved server-startup: fire-and-forget cache warmup (`runWarmup()`) som pre-fetcher Stortinget-data, og valgfri periodisk refresh (`startWarmupLoop()`). Styres via `STORTINGET_WARMUP` og `STORTINGET_WARMUP_INTERVAL_MS`.

## Dataflyt ende-til-ende (saksanalyse)

```
Bruker → Next.js-side → /api/analyse/[sak_id] (proxy)
  → FastAPI /api/v1/analyse/{sak_id}
    → cache? returner cached
    → Stortinget /eksport/sak (metadata)
    → Stortinget /eksport/publikasjon (XML)
    → lxml-parsing (deterministisk struktur)
    → Claude (3 tolkningssteg med Pydantic-validering)
    → cache-skriv
  → Saksanalyse JSON
→ AnalysePanel viser strukturert resultat
```

## Prinsipper kodebasen håndhever

1. XML-parsing for struktur, LLM kun for tolkning.
2. Skill fakta fra tolkning (XML-ekstraksjon vs. politisk analyse).
3. Strukturerte utdata — alle LLM-svar valideres mot Pydantic.
4. Politisk nøytralitet i prompts.
5. Pipeline-tenkning: små steg med klare inn-/utdata.
6. Prediksjon: billigste signal først (deterministisk → historikk → LLM).

## Filer verdt å kjenne

| Formål | Fil |
|---|---|
| FastAPI-app | `backend/app/main.py:42` |
| Ruter | `backend/app/api/routes.py` |
| Pipeline-orkestrering | `backend/app/services/pipeline.py:23` |
| XML-parser | `backend/app/services/xml_parser.py` |
| Stortinget-klient | `backend/app/services/stortinget.py` |
| Claude-wrapper | `backend/app/services/claude.py` |
| Cache (dual) | `backend/app/db/cache.py` |
| Prediksjonspipeline | `backend/app/services/prediksjon_pipeline.py` |
| Frontend-dashboard | `components/dash/page-dashboard.tsx` |
| Saksliste + analyse | `components/dash/page-bills.tsx` |
| Next.js analyse-proxy | `app/api/analyse/[sak_id]/route.ts` |
| Warmup | `instrumentation.ts` |

## Verifisering

Ingen endringer gjøres — dette er en forklaring. Brukeren kan verifisere ved å:
- Kjøre backend (`uvicorn app.main:app`) og ramme `GET /api/v1/analyse/47163` (test-sak fra CLAUDE.md).
- Kjøre frontend (`npm run dev`) og åpne Bills-visningen.
