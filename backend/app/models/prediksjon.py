from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Konfidens(str, Enum):
    hoy = "hoy"
    middels = "middels"
    lav = "lav"


class Sakskategori(str, Enum):
    rutine = "rutine"
    koalisjonssak = "koalisjonssak"
    balansesak = "balansesak"
    personvotering = "personvotering"


class SamletUtfall(str, Enum):
    sannsynlig_bifalt = "sannsynlig_bifalt"
    sannsynlig_forkastet = "sannsynlig_forkastet"
    usikkert = "usikkert"


class PrimærSignal(str, Enum):
    fraksjon_xml = "fraksjon_xml"
    regjeringsposisjon = "regjeringsposisjon"
    historisk_moenster = "historisk_moenster"
    llm_analyse = "llm_analyse"
    ikke_tilgjengelig = "ikke_tilgjengelig"


class PartiPrediksjon(_Base):
    """Sannsynlighetsindikasjon for ett parti på én sak."""

    parti: str
    sannsynlighet_for: float = Field(
        description=(
            "Sannsynlighet for at partiet stemmer FOR tilrådingen [0.0–1.0]. "
            "Lav = partiet stemmer MOT tilrådingen (støtter alternativt forslag)."
        )
    )
    konfidens: Konfidens
    primaersignal: PrimærSignal
    begrunnelse: str = Field(description="Menneskelesbar forklaring med referanse til baseline-tall")
    historiske_saker: list[int] = Field(default_factory=list)
    avvik_fra_baseline: bool = Field(
        default=False,
        description="True hvis indikasjonen avviker fra naiv regel-baseline",
    )


class VoteringType(str, Enum):
    tilrading = "tilrading"
    mindretallsforslag = "mindretallsforslag"


class VoteringPrediksjon(_Base):
    """Prediksjoner for én spesifikk votering — tilrådingen eller ett mindretallsforslag."""

    votering_type: VoteringType
    tittel: str = Field(description="Menneskelesbar tittel, f.eks. 'Tilrådingen' eller 'Forslag 1–2 (SV, Sp)'")
    forslagstekst: str | None = Field(
        None,
        description="Forslagstekst fra XML (kun mindretallsforslag; sammenslåtte tekster for gruppen)",
    )
    forslagsstillere: list[str] = Field(
        default_factory=list,
        description="Partikoder for forslagsstillerne (kun mindretallsforslag)",
    )
    prediksjoner: list[PartiPrediksjon] = Field(default_factory=list)
    samlet_utfall: SamletUtfall


class Saksprediksjon(_Base):
    """Samlet sannsynlighetsindikasjon for en stortingssak."""

    sak_id: int
    sakskategori: Sakskategori
    voteringer: list[VoteringPrediksjon] = Field(
        default_factory=list,
        description=(
            "Prediksjoner per votering. Første element er alltid tilrådingen; "
            "påfølgende elementer er mindretallsforslag gruppert etter forslagsstillere."
        ),
    )
    samlet_utfall: SamletUtfall
    samlet_konfidens: Konfidens
    signalkilder_brukt: list[str] = Field(default_factory=list)
    baseline_ville_gitt: str = Field(
        default="",
        description="Hva naiv baseline ville predikert (for sammenligning)",
    )
    eksterne_signaler: list[str] = Field(default_factory=list)
    beregnet_tidspunkt: datetime = Field(default_factory=datetime.utcnow)
    prompt_versjon: str | None = None
