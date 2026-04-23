# Kodekonvensjoner

## Språk i kode

- **Kode (variabel-, funksjons-, klassenavn)**: engelsk
- **Domenenære klasse- og feltnavn**: kan være norske når det er naturlig (f.eks. `Forslagspunkt`, `forpliktelsesgrad`, `DokumentStruktur`) — norsk reduserer oversettelsesfeil i domenet
- **Docstrings for domenekode**: norsk
- **Docstrings for infrastrukturkode**: engelsk
- **Kommentarer**: samme språk som omkringliggende docstring
- **Loggmeldinger**: engelsk (enklere for verktøy)

Konsistens innen én fil er viktigere enn reglene over. Ikke bland halvveis.

## Type hints

Overalt. `from __future__ import annotations` øverst i alle filer.

Returtyper på alle funksjoner, inkludert `-> None` hvor relevant. `Any` er et lukt-tegn — unngå unntatt når det er uunngåelig (typisk mot JSON-respons før parsing).

## Datamodeller

All strukturert data er Pydantic v2-modeller. Ikke `dataclass`, ikke `TypedDict`, ikke dicts med konvensjoner.

```python
from pydantic import BaseModel, Field

class Forslagspunkt(BaseModel):
    nummer: int = Field(description="Løpenummer slik det står i dokumentet")
    tekst: str = Field(description="Ordrett forslagstekst fra XML")
    fra_partier: list[str] = Field(description="Partikoder som fremmer forslaget")
    forpliktelsesgrad: Forpliktelsesgrad | None = None  # Settes i LLM-steg
    begrunnelse_klassifisering: str | None = None
```

Bruk `Field(description=...)` for alle felt — beskrivelsen blir med i JSON-schemaet som Claude ser når modellen brukes som tool-input.

Enums for klassifiseringsfelt:
```python
from enum import Enum

class Forpliktelsesgrad(str, Enum):
    UTREDE = "utrede"
    VURDERE = "vurdere"
    LEGGE_FREM = "legge_frem"
    KOMME_TILBAKE = "komme_tilbake"
    SIKRE = "sikre"
    GJENNOMFORE = "gjennomfore"
```

## Modulstruktur

```
app/
  __init__.py
  config.py            # pydantic-settings, leser fra env
  main.py              # FastAPI-app
  models/              # Pydantic-modeller (domene)
    __init__.py
    sak.py             # saksmetadata
    dokument.py        # publikasjon, xml-struktur
    forslag.py         # forslagspunkter, fraksjoner
    analyse.py         # innholdsanalyse, politisk kontekst, full Saksanalyse
  services/            # forretningslogikk
    __init__.py
    stortinget.py      # API-klient (JSON metadata + XML publikasjoner)
    xml_parser.py      # lxml-basert strukturell parsing
    claude.py          # innpakning av Anthropic SDK
    pipeline.py        # orkestrering av analysesteg
  steps/               # hvert analysesteg som egen modul
    __init__.py
    metadata_henting.py
    publikasjon_henting.py
    strukturell_parsing.py
    forpliktelsesklassifisering.py   # LLM
    innholdsanalyse.py                # LLM
    politisk_kontekst.py              # LLM
  prompts/             # prompt-templates (Python-konstanter, ikke filer)
    __init__.py
    forpliktelsesklassifisering.py
    innholdsanalyse.py
    politisk_kontekst.py
  api/                 # HTTP-endepunkter
    __init__.py
    routes.py
tests/
  fixtures/            # ekte saker som testdata (XML + JSON cached)
  test_*.py
```

## Avhengigheter

Alle avhengigheter i `pyproject.toml` (med `uv` eller `poetry`). Ingen `requirements.txt` side om side.

Kjerneavhengigheter:
- `fastapi`
- `pydantic`, `pydantic-settings`
- `anthropic`
- `httpx`
- `lxml` — brukes for XML-parsing (raskere og mer robust enn stdlib `xml.etree`, håndterer DTD og entities bedre)
- `structlog`
- `pytest`, `pytest-asyncio` (dev)

Før ny avhengighet legges til: begrunn hvorfor eksisterende stack ikke dekker behovet.

## XML-parsing

Bruk `lxml` — ikke `xml.etree.ElementTree`. Grunner:
- Håndterer DTD-referanser robust (Stortingets XML refererer til eksterne DTD-er)
- Bedre håndtering av entities som `&shy;`
- XPath-støtte er renere
- Raskere

**Ikke hent eksterne DTD-er ved parsing.** Sett `lxml` til å ikke løse opp eksterne referanser (`no_network=True`, `resolve_entities=False` når praktisk). DTD-en er dokumentasjon for oss, ikke noe parseren skal følge.

```python
from lxml import etree

parser = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
)
tree = etree.fromstring(xml_bytes, parser=parser)
```

## Async

HTTP og API-kall er async. Pipeline-steg som kaller Claude er async. Bruk `httpx.AsyncClient`.

XML-parsing (CPU-bundet) er sync. Hvis pipelinen totalt sett er async, wrap tung parsing i `asyncio.to_thread` for å unngå å blokkere event-loop-en.

## Feilhåndtering

- Egne exception-klasser for domenefeil: `SakIkkeFunnet`, `PublikasjonUtilgjengelig`, `XmlParsingFeilet`, `AnalyseFeilet`
- Ikke fang generiske `Exception`. Fang spesifikt.
- Log før re-raise når du legger til kontekst.
- FastAPI `HTTPException` kun i rute-handlere, ikke dypere.
- XML-parsing-feil skal ikke kræsje pipelinen — fall tilbake til HTML-fallback med tydelig logging.

## Testing

- `pytest` med `pytest-asyncio`
- Tester bruker ekte data fra Stortinget (cachet i `tests/fixtures/` som XML/JSON-filer)
- Claude-kall mockes kun i enhetstester; integrasjonstester kjører mot ekte API (med eget flag)
- Hver analysestepmodul har minst én "ekte sak"-test med forventet output
- Strukturell parsing (steg 3) testes uten LLM-kall — deterministiske tester mot lagrede XML-eksempler
- LLM-steg testes med "golden output"-sammenligning på lav strenghet (tekstlikhet), streng sammenligning på strukturerte felt (enum-verdier)

## Config

`pydantic-settings` leser fra env og `.env`. Ingen hardkodede verdier.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    anthropic_api_key: str
    claude_model: str = "claude-opus-4-7"
    stortinget_base_url: str = "https://data.stortinget.no"
    user_agent: str = "saksanalyse/0.1 (kontakt: ...)"
```

## Logging

`structlog` i JSON-modus. Alle logglinjer har minst: `sak_id` (når relevant), `step`, `duration_ms`.

```python
log.info("analysis_step_completed", sak_id=sak_id, step="forpliktelsesklassifisering",
         duration_ms=elapsed, antall_forslag=len(result.forslag))
```

## Ikke gjør dette

- Ikke `print()` utenfor utviklings-skripts
- Ikke global state utenom config
- Ikke singletons for Claude-klient eller HTTP-klient — bruk dependency injection via FastAPI
- Ikke fang og svelg exceptions "just in case"
- Ikke commit `.env`, API-nøkler, eller nedlastede dokumenter
- Ikke bruk `xml.etree.ElementTree` — bruk `lxml`
- Ikke la parseren hente eksterne DTD-er fra nettet (sikkerhet + ytelse)
