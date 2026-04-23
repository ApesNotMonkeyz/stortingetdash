#!/usr/bin/env python3
"""
Holdout-evaluering av prediksjonsmodulen (lag 1-2).

Bruker siste 20% av voteringer sortert etter dato som holdout-sett.

Evalueringer:
  A. Signal 2 noyaktighet pa tilradingsvoteringer med identifisert forslagsstiller
     (kun hoy-konfidens prediksjoner for rp og forslagsstillere selv)
  B. Krysspress-saker fra beregning 4 -> verifiser at de har lav konfidens
  C. Fordeling av sakskategorier i holdout-settet

Kjores fra backend/-mappen:
    python scripts/evaluer_prediksjon.py

Krever DATABASE_URL i .env eller miljo.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import structlog, structlog.stdlib

logging.basicConfig(level=logging.WARNING)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
log = structlog.get_logger()
log.setLevel("INFO")

from app.config import Settings, regjering_partier_for_dato
from app.models.dokument import DokumentStruktur, Forslagspunkt, Fraksjon
from app.models.prediksjon import Konfidens
from app.models.sak import Parti, Person, Fylke, Sak, SakOpphav
from app.steps.prediksjon_lag1 import (
    beregn_samlet_utfall,
    klassifiser_sakskategori,
    lag1_prediker,
)
from app.utils.partier import KJERNE_PARTIER


# ── Datastrukturer ────────────────────────────────────────────────────────────

@dataclass
class VoteringRad:
    votering_id: str
    sak_id: int
    dato: date
    dokumentgruppe: str
    tema: str | None
    vedtatt: bool | None
    saksfelt: list[str]
    parti_stemmer: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    # parti -> (for_stemmer, mot_stemmer, fravarende)

    def faktisk_retning(self, parti: str) -> str | None:
        """'for' | 'mot' | None (ikke nok stemmer)"""
        stemmer = self.parti_stemmer.get(parti)
        if not stemmer:
            return None
        for_s, mot_s, _ = stemmer
        if for_s + mot_s == 0:
            return None
        return "for" if for_s >= mot_s else "mot"


# ── DB-oppslag ────────────────────────────────────────────────────────────────

async def hent_voteringer(session: AsyncSession) -> list[VoteringRad]:
    rows = await session.execute(text("""
        SELECT v.votering_id, v.sak_id, v.dato, v.dokumentgruppe,
               v.tema, v.vedtatt, v.saksfelt
        FROM voteringer v
        ORDER BY v.dato
    """))
    voteringer = {
        row.votering_id: VoteringRad(
            votering_id=row.votering_id,
            sak_id=row.sak_id,
            dato=row.dato,
            dokumentgruppe=str(row.dokumentgruppe),
            tema=row.tema,
            vedtatt=row.vedtatt,
            saksfelt=list(row.saksfelt) if row.saksfelt else [],
        )
        for row in rows
    }

    parti_rows = await session.execute(text("""
        SELECT votering_id, parti, for_stemmer, mot_stemmer, fravarende
        FROM voteringsresultat_parti
        WHERE parti = ANY(:kjerne)
    """), {"kjerne": KJERNE_PARTIER})

    for row in parti_rows:
        if row.votering_id in voteringer:
            voteringer[row.votering_id].parti_stemmer[row.parti] = (
                row.for_stemmer, row.mot_stemmer, row.fravarende
            )

    return list(voteringer.values())


async def hent_tilraading_rater(session: AsyncSession) -> dict[str, float]:
    rows = await session.execute(text("""
        SELECT parti, andel_for FROM parti_moenster
        WHERE saksfelt = '_total' AND dokumentgruppe = 'tilraading'
    """))
    return {row.parti: float(row.andel_for) for row in rows}


async def hent_krysspress_saker(session: AsyncSession) -> set[int]:
    """Henter sak_id-er identifisert som krysspress i beregning 4."""
    try:
        rows = await session.execute(text("SELECT DISTINCT sak_id FROM krysspress_saker"))
        return {row.sak_id for row in rows}
    except Exception:
        return set()


# ── Evalueringshjelpere ───────────────────────────────────────────────────────

def extract_forslagsstillere_fra_tema(tema: str | None) -> list[str]:
    """Prover a hente partikoder fra voteringstema ('pa vegne av H, FrP')."""
    if not tema:
        return []
    from app.utils.partier import normaliser_partiliste
    import re
    m = re.search(r"(?:pa vegne av|fremmet av|fra)\s+(.+)", tema, re.IGNORECASE)
    if not m:
        return []
    raw = re.sub(r"representantene?\s+.+", "", m.group(1), flags=re.IGNORECASE)
    kandidater = [s.strip().rstrip(",") for s in re.split(r"[,\s]+og\s+|[,]\s*", raw) if s.strip()]
    return normaliser_partiliste(kandidater)


def er_tilrading_votering(tema: str | None) -> bool:
    """
    Returnerer True for voteringer som sannsynligvis er tilradingsvoteringen
    (ikke en alternativ votering mellom to forslag).

    Signal 2 gjelder tilradingsvoteringen: rp stemmer FOR komiteens innstilling
    som forkaster Dok8-forslaget. For 'alternativ votering mellom innstillingen
    og forslag X' er FOR/MOT-semantikken annerledes og uklar.
    """
    if not tema:
        return True  # Ingen tema = sannsynligvis tilrading
    t = tema.lower()
    return "alternativ votering" not in t and "forslag nr" not in t


def bygg_mock_sak_og_dok(
    votering: VoteringRad,
    forslagsstillere: list[str],
    mindretall_partier: list[str],
) -> tuple[Sak, DokumentStruktur]:
    """Bygger Sak og DokumentStruktur nok for lag 1 uten ekte XML/API."""
    personer = [
        Person(
            id=f"eval_{p}",
            fornavn="Test",
            etternavn=p,
            parti=Parti(id=p, navn=p, representert_parti=True),
            fylke=Fylke(id="oslo", navn="Oslo"),
            vara_representant=False,
        )
        for p in forslagsstillere
    ]
    sak = Sak(
        id=votering.sak_id,
        tittel=votering.tema or "Ukjent",
        dokumentgruppe=int(votering.dokumentgruppe),
        type=1,
        status=0,
        ferdigbehandlet=False,
        sak_opphav=SakOpphav(forslagstiller_liste=personer) if forslagsstillere else None,
    )

    mindretallsforslag = []
    if mindretall_partier:
        mindretallsforslag = [
            Forslagspunkt(
                nr="1",
                fra=Fraksjon(
                    partier_raa=", ".join(mindretall_partier),
                    partier=mindretall_partier,
                ),
                tekst="(generert av evalueringsskript)",
            )
        ]

    dok = DokumentStruktur(
        dok_type="ny_innstilling",
        pub_id=f"eval-{votering.votering_id}",
        mindretallsforslag=mindretallsforslag,
    )
    return sak, dok


def er_korrekt_hoy(pred_sannsynlighet: float, faktisk: str | None) -> bool | None:
    """Evaluerer bare hoy-konfidens prediksjoner (>0.9 eller <0.1)."""
    if faktisk is None:
        return None
    if pred_sannsynlighet > 0.9:
        return faktisk == "for"
    if pred_sannsynlighet < 0.1:
        return faktisk == "mot"
    return None  # Lav konfidens (0.5) = ikke testet her


# ── Rapport ───────────────────────────────────────────────────────────────────

def skriv_rapport(resultater: dict) -> None:
    sep = "=" * 70
    seksjon = "-" * 40
    print(f"\n{sep}")
    print("EVALUERING -- Prediksjonsmodul lag 1")
    print(sep)

    print(f"\nHoldout-sett: {resultater['holdout_n']} voteringer "
          f"(siste 20% av {resultater['total_n']} totalt)")
    print(f"Dato-range: {resultater['holdout_fra']} til {resultater['holdout_til']}")

    # A: Signal 2
    a = resultater["signal2"]
    print(f"\n{seksjon}")
    print("A. Signal 2 -- hoy-konfidens tilradingsvoteringer")
    if a["n_testet"] > 0:
        acc = a["n_korrekt"] / a["n_testet"]
        print(f"   Testet (rp + forslagsstillere): {a['n_testet']}")
        print(f"   Korrekt:  {a['n_korrekt']} ({acc:.1%})")
        print(f"   Feil:     {a['n_feil']}")
        ok = "OK" if acc >= 0.95 else "IKKE NADD"
        print(f"   Mal >95%: {ok}")
        if a["feil_eksempler"]:
            print("   Eksempler pa feil:")
            for ex in a["feil_eksempler"][:5]:
                print(f"     sak={ex['sak_id']} {ex['parti']} "
                      f"pred={ex['pred']:.0%} faktisk={ex['faktisk']}  -- {ex['tema'][:60]}")
    else:
        print("   Ingen egnede testtilfeller (tilradingsvotering + identifisert opp-forslagsstiller)")
        print("   Merknad: Signal 2 gjelder Dok8-saker der hele saken er fremmet av opposisjon.")
        print("   DB har ikke sak-nivaforslag stillerdata -- evaluert via voteringstema.")

    # B: Krysspress-saker
    b = resultater["krysspress"]
    print(f"\n{seksjon}")
    print("B. Krysspress-saker (beregning 4)")
    if b["n_saker"] > 0:
        lav_andel = b["n_lav_konfidens"] / b["n_parti_voteringer"] if b["n_parti_voteringer"] > 0 else 0
        print(f"   Saker i holdout:      {b['n_saker']}")
        print(f"   Parti-voteringer:     {b['n_parti_voteringer']}")
        print(f"   Lav konfidens-andel:  {lav_andel:.1%}")
        ok = "OK" if lav_andel >= 0.80 else "IKKE NADD"
        print(f"   Mal >=80% lav: {ok}")
    else:
        print("   Ingen krysspress-saker funnet i holdout")
        print("   (krysspress_saker-tabellen mangler kanskje -- kjor baseline_analyse.py)")

    # C: Sakskategorier
    c = resultater["kategorier"]
    print(f"\n{seksjon}")
    print("C. Sakskategori-fordeling i holdout")
    total_k = sum(c.values())
    for kat, n in sorted(c.items(), key=lambda x: -x[1]):
        print(f"   {kat:<20}: {n:4d}  ({n/total_k:.1%})")

    print(f"\n{sep}\n")


# ── Hovedflyt ─────────────────────────────────────────────────────────────────

async def main() -> None:
    settings = Settings()
    if not settings.database_url:
        log.error("DATABASE_URL ikke satt -- avbryter")
        sys.exit(1)

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        log.info("Henter voteringer fra DB...")
        alle = await hent_voteringer(session)
        tilraading_rater = await hent_tilraading_rater(session)
        krysspress_sak_ids = await hent_krysspress_saker(session)

    log.info(f"Totalt {len(alle)} voteringer lastet")

    # Holdout = siste 20% sortert etter dato
    alle.sort(key=lambda v: v.dato)
    split = int(len(alle) * 0.80)
    holdout = alle[split:]

    log.info(
        "holdout_klart",
        n=len(holdout),
        fra=str(holdout[0].dato),
        til=str(holdout[-1].dato),
    )

    # ── A: Signal 2 ───────────────────────────────────────────────────────────
    # Kun tilradingsvoteringer (ikke alternativ votering mellom forslag),
    # kun hoy-konfidens prediksjoner (rp og forslagsstillere selv).
    n_testet = 0
    n_korrekt = 0
    n_feil = 0
    feil_eksempler: list[dict] = []

    for v in holdout:
        if v.dokumentgruppe != "4":
            continue
        if not er_tilrading_votering(v.tema):
            continue

        forslagsstillere = extract_forslagsstillere_fra_tema(v.tema)
        if not forslagsstillere:
            continue

        rp = regjering_partier_for_dato(v.dato)
        if not all(p not in rp for p in forslagsstillere):
            continue  # Ikke ren opposisjon

        sak, dok = bygg_mock_sak_og_dok(v, forslagsstillere, [])
        prediksjoner = lag1_prediker(
            dok, sak,
            alle_partier=KJERNE_PARTIER,
            dato=v.dato,
            tilraading_for_rate=tilraading_rater,
        )

        for parti, pred in prediksjoner.items():
            # Kun hoy-konfidens prediksjoner (rp eller forslagsstillere)
            res = er_korrekt_hoy(pred.sannsynlighet_for, v.faktisk_retning(parti))
            if res is None:
                continue
            n_testet += 1
            if res:
                n_korrekt += 1
            else:
                n_feil += 1
                feil_eksempler.append({
                    "sak_id": v.sak_id, "parti": parti,
                    "pred": pred.sannsynlighet_for,
                    "faktisk": v.faktisk_retning(parti),
                    "tema": v.tema or "",
                })

    # ── B: Krysspress ─────────────────────────────────────────────────────────
    holdout_sak_ids = {v.sak_id for v in holdout}
    krysspress_i_holdout = krysspress_sak_ids & holdout_sak_ids
    krysspress_n_parti = 0
    krysspress_n_lav = 0

    for v in holdout:
        if v.sak_id not in krysspress_i_holdout:
            continue
        rp = regjering_partier_for_dato(v.dato)
        sak, dok = bygg_mock_sak_og_dok(v, [], [])
        prediksjoner = lag1_prediker(
            dok, sak,
            alle_partier=KJERNE_PARTIER,
            dato=v.dato,
            tilraading_for_rate=tilraading_rater,
        )
        for pred in prediksjoner.values():
            krysspress_n_parti += 1
            if pred.konfidens == Konfidens.lav:
                krysspress_n_lav += 1

    # ── C: Sakskategorier ─────────────────────────────────────────────────────
    kategori_teller: Counter = Counter()

    for v in holdout:
        rp = regjering_partier_for_dato(v.dato)
        forslagsstillere = extract_forslagsstillere_fra_tema(v.tema)
        mindretall: list[str] = []
        if v.tema and "mindretall" in v.tema.lower():
            mindretall = forslagsstillere

        sak, dok = bygg_mock_sak_og_dok(v, forslagsstillere, mindretall)
        prediksjoner = lag1_prediker(
            dok, sak,
            alle_partier=KJERNE_PARTIER,
            dato=v.dato,
            tilraading_for_rate=tilraading_rater,
        )
        kat = klassifiser_sakskategori(prediksjoner, rp, set(), v.saksfelt)
        kategori_teller[kat] += 1

    skriv_rapport({
        "total_n": len(alle),
        "holdout_n": len(holdout),
        "holdout_fra": holdout[0].dato if holdout else None,
        "holdout_til": holdout[-1].dato if holdout else None,
        "signal2": {
            "n_testet": n_testet,
            "n_korrekt": n_korrekt,
            "n_feil": n_feil,
            "feil_eksempler": feil_eksempler,
        },
        "krysspress": {
            "n_saker": len(krysspress_i_holdout),
            "n_parti_voteringer": krysspress_n_parti,
            "n_lav_konfidens": krysspress_n_lav,
        },
        "kategorier": dict(kategori_teller),
    })


if __name__ == "__main__":
    asyncio.run(main())
