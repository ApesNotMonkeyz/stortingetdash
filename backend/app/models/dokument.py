from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Forpliktelsesgrad(str, Enum):
    utrede = "utrede"
    vurdere = "vurdere"
    legge_frem = "legge_frem"
    komme_tilbake = "komme_tilbake"
    sikre = "sikre"
    gjennomfore = "gjennomfore"


class Fraksjon(_Base):
    partier_raa: str = Field(description="Råverdi: @Fra/@fra-attributt eller <Fraksjon><Tittel>-tekst")
    partier: list[str] = Field(description="Partiliste splittet på komma og 'og' (rå, ikke normalisert)")


class Forslagspunkt(_Base):
    nr: str = Field(description="Forslagsnummer som streng, f.eks. '1'")
    fra: Fraksjon | None = Field(None, description="Fraksjon som fremmer forslaget")
    tekst: str = Field(description="Forslagsteksten, U+00A0 normalisert")
    forpliktelsesgrad: Forpliktelsesgrad | None = Field(
        None, description="Klassifisert forpliktelsesgrad (steg 4)"
    )
    begrunnelse_klassifisering: str | None = Field(
        None, description="LLM-begrunnelse for valgt forpliktelsesgrad"
    )


class Seksjon(_Base):
    tittel: str
    tekst: str = Field(description="All tekst i seksjonen, U+00A0 normalisert")


DokType = Literal["ny_innstilling", "ny_dok8", "gammel_innstilling"]


class DokumentStruktur(_Base):
    dok_type: DokType
    pub_id: str = Field(description="Publikasjon-ID som ble hentet")
    tittel: str | None = None
    sesjon: str | None = None
    kildedok: str | None = Field(None, description="Referanse til kildedokument")
    seksjoner: list[Seksjon] = Field(default_factory=list)
    mindretallsforslag: list[Forslagspunkt] = Field(
        default_factory=list,
        description="Forslag fra mindretallet (ForslagFraMindretall/forslagfram)",
    )
    vedtakstekst: str | None = Field(
        None,
        description=(
            "Komiteens tilråding (flertallet) eller "
            "originalforslagets vedtakspunkt (Dok 8)"
        ),
    )
    tilraading_partier: list[str] = Field(
        default_factory=list,
        description=(
            "Normaliserte partikoder for partier som eksplisitt støtter tilrådingen, "
            "fra KomTilrading/A-tekst ('Komiteens tilråding fremmes av ... fra X, Y og Z.'). "
            "Tom liste betyr at informasjonen ikke finnes i dokumentet."
        ),
    )
    vedlegg_tekst: str | None = Field(
        None,
        description="Vedlegg-innhold hvis tilgjengelig (gammel DTD); None for PDF-pekere",
    )
