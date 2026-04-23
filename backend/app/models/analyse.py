from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.dokument import DokType, Forslagspunkt


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Sikkerhetsnivaa(str, Enum):
    """høy / middels / lav — ASCII-navn for kompatibilitet med Anthropic tool-schema."""

    hoy = "hoy"
    middels = "middels"
    lav = "lav"


class Innholdsanalyse(_Base):
    problemforstaelse: str = Field(
        description="Hva forslagstillerne beskriver som problemet"
    )
    losningsforslag: str = Field(
        description="Kort sammendrag av hva som faktisk foreslås gjort"
    )
    argumentasjonslinjer: list[str] = Field(
        description="Verdier, hensyn og fakta forslagstillerne bygger argumentet på"
    )


class PolitiskDimensjon(_Base):
    akse: str = Field(description="Navn på den politiske aksen, f.eks. 'marked/stat'")
    plassering: str = Field(description="Forslagets plassering på aksen")
    sikkerhet: Sikkerhetsnivaa
    begrunnelse: str


class KoblingType(str, Enum):
    reversering = "reversering"
    opptrapping = "opptrapping"
    nytt = "nytt"
    videroforing = "videroforing"


class KoblingEksisterendePolitikk(_Base):
    type: KoblingType
    sikkerhet: Sikkerhetsnivaa
    begrunnelse: str


class PolitiskKontekst(_Base):
    politiske_dimensjoner: list[PolitiskDimensjon] = Field(default_factory=list)
    kobling_eksisterende_politikk: KoblingEksisterendePolitikk | None = None


class Saksanalyse(_Base):
    sak_id: int
    pub_id: str
    dok_type: DokType
    tittel: str | None = None
    sesjon: str | None = None
    forslag: list[Forslagspunkt] = Field(default_factory=list)
    innholdsanalyse: Innholdsanalyse | None = None
    politisk_kontekst: PolitiskKontekst | None = None
