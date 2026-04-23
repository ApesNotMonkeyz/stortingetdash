from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    claude_model: str = "claude-opus-4-7"
    stortinget_base_url: str = "https://data.stortinget.no"
    stortinget_doc_base_url: str = "https://www.stortinget.no"
    user_agent: str = "saksanalyse/0.1 (kontakt: odinronning@icloud.com)"
    log_level: str = "INFO"
    database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ── Regjeringskonfigurasjon ───────────────────────────────────────────────────
# «til» er eksklusiv øvre grense (fra <= dato < til).
# til=None betyr sittende regjering (ingen sluttdato).
# Oppdateres manuelt ved regjeringsskifte — aldri hardkodet i scripts.

REGJERINGER: list[dict] = [
    {"navn": "Støre I",  "partier": ["A", "Sp"], "fra": "2021-10-14", "til": "2025-01-30"},
    {"navn": "Støre II", "partier": ["A"],        "fra": "2025-01-30", "til": None},
]


def regjering_partier_for_dato(votering_dato: date) -> set[str]:
    """Returnerer settet av regjeringspartier på en gitt dato (fra REGJERINGER-config)."""
    for periode in REGJERINGER:
        fra = date.fromisoformat(periode["fra"])
        til = date.fromisoformat(periode["til"]) if periode["til"] else None
        if votering_dato >= fra and (til is None or votering_dato < til):
            return set(periode["partier"])
    return set()
