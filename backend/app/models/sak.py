from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    """Felles konfig: ignorer ukjente felt fra API-et (respons_dato_tid, versjon, osv.)."""

    model_config = ConfigDict(extra="ignore")


class Parti(_Base):
    id: str = Field(description="Partiets ID, f.eks. 'KrF', 'A', 'H'")
    navn: str = Field(description="Fullt partinavn")
    representert_parti: bool = Field(description="Er partiet representert i Stortinget?")


class Fylke(_Base):
    id: str
    navn: str


class Emne(_Base):
    id: int
    navn: str = Field(description="Emnets navn, f.eks. 'Samferdsel'")
    er_hovedemne: bool


class Komite(_Base):
    id: str = Field(description="Komité-ID, f.eks. 'TRANSKOM'")
    navn: str = Field(description="Fullt komiténavn")


class Person(_Base):
    """Representant — brukes for både forslagstillere og saksordførere."""

    id: str = Field(description="Representantens ID")
    fornavn: str
    etternavn: str
    parti: Parti
    fylke: Fylke
    vara_representant: bool
    kjoenn: int | None = None

    @property
    def fullt_navn(self) -> str:
        return f"{self.fornavn} {self.etternavn}".strip()


class Publikasjon(_Base):
    """Referanse til et tilknyttet dokument (Dok 8, innstilling, referat, o.l.)."""

    eksport_id: str
    lenke_tekst: str = Field(description="Menneskelig lesbar tittel, f.eks. 'Dokument 8:175 S (2009-2010)'")
    # API returnerer relative URL-er som starter med //
    lenke_url: str
    type: int = Field(description="Dokumenttype-kode: 2=dok8, 6=innstilling, 10=referat")
    undertype: str | None = None

    @property
    def full_url(self) -> str:
        """Gjør relativ URL absolutt."""
        if self.lenke_url.startswith("//"):
            return f"https:{self.lenke_url}"
        return self.lenke_url


class SakOpphav(_Base):
    """Opphavsinformasjon — brukes primært for representantforslag (Dok 8)."""

    forslagstiller_liste: list[Person] = Field(default_factory=list)


class Sak(_Base):
    """
    Saksmetadata fra /eksport/sak.

    Dekker alle dokumentgrupper: representantforslag (4), proposisjoner (2),
    meldinger (3), innstillinger (6), osv.
    """

    id: int = Field(description="Unik sak-ID")
    tittel: str = Field(description="Fullstendig tittel")
    korttittel: str | None = Field(None, description="Kortversjon av tittelen")
    innstillingstekst: str | None = Field(
        None, description="Komiteens innstillingstittel (finnes etter komitébehandling)"
    )
    dokumentgruppe: int = Field(
        description="Dokumentgruppekode: 4=representantforslag, 2=proposisjon, 3=melding"
    )
    type: int
    status: int = Field(description="Statuskode: 1=ferdigbehandlet")
    ferdigbehandlet: bool
    henvisning: str | None = Field(
        None, description="Menneskelig referanse, f.eks. 'Dokument 8:175 S (2009-2010)'"
    )
    sak_sesjon: str | None = Field(None, description="Sesjonen saken ble fremmet, f.eks. '2009-2010'")
    sak_nummer: int | None = None
    kortvedtak: str | None = None
    vedtakstekst: str | None = None
    parentestekst: str | None = Field(
        None, description="F.eks. 'Forslag fra (KrF)' — brukes i listeoversikter"
    )
    komite: Komite | None = None
    emne_liste: list[Emne] = Field(default_factory=list)
    stikkord_liste: list[str] = Field(default_factory=list)
    publikasjon_referanse_liste: list[Publikasjon] = Field(default_factory=list)
    saksordfoerer_liste: list[Person] = Field(default_factory=list)
    sak_opphav: SakOpphav | None = None

    @property
    def er_representantforslag(self) -> bool:
        return self.dokumentgruppe == 4

    @property
    def er_proposisjon(self) -> bool:
        return self.dokumentgruppe == 2

    @property
    def primær_publikasjon(self) -> Publikasjon | None:
        """
        Originalforslaget eller proposisjonen — ikke innstillingen.
        For Dok 8: type 2. For proposisjoner: type 1.
        """
        for p in self.publikasjon_referanse_liste:
            if p.type in (1, 2):
                return p
        return self.publikasjon_referanse_liste[0] if self.publikasjon_referanse_liste else None

    @property
    def analyse_publikasjon(self) -> Publikasjon | None:
        """
        Innstilling (type 6) foretrekkes — inneholder komiteens behandling og
        originalforslaget som vedlegg i én XML. Falls tilbake til originalforslaget.
        """
        for p in self.publikasjon_referanse_liste:
            if p.type == 6:
                return p
        return self.primær_publikasjon
