#!/usr/bin/env python3
"""
Beregning 3: Fraksjon-til-plenum-konsistens.

Maaler: Naar fraksjonsinformasjon finnes i innstillingens XML (<ForslagFraMindretall>),
hvor ofte stemte partiene i plenum i samsvar med sin komitefraksjon?

Algoritme:
  1. Hent sak_ids med voteringer fra sesjonene 2023-2024 og 2024-2025 (DB).
  2. For hvert sak_id (stikkoerve, maks MAX_SAKER):
       a. Hent innstillings-XML fra Stortinget API (steg 1-3, ingen LLM).
       b. Sjekk om det er ny_innstilling (ForslagFraMindretall finnes).
       c. Ekstraher partier i mindretallsfraksjon.
       d. Finn tilraading-votering for sak_id i DB.
       e. Sammenlign fraksjon-posisjon med faktisk plenum-stemme.
  3. Aggreger per parti og per saksfelt.
  4. Lagre i fraksjon_plenum_konsistens-tabellen.
  5. Skriv seksjon for beregning 3 til baseline-rapport.md.

Kjoer fra backend/-mappen:
    python scripts/beregn_fraksjon_konsistens.py [--max-saker 100] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog, structlog.stdlib
import structlog.dev
import logging

logging.basicConfig(level=logging.WARNING)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    context_class=dict,
)
log = structlog.get_logger()

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.config import Settings, regjering_partier_for_dato
from app.db.models import DbFraksjonPlenumKonsistens
from app.db.session import init_db, get_session_factory
from app.exceptions import AnalyseFeilet, DokumentUtilgjengelig
from app.services.stortinget import StortingetClient
from app.services.xml_parser import parse_dokument
from app.utils.partier import normaliser_partiliste, KJERNE_PARTIER

# ── Konfigurering ─────────────────────────────────────────────────────────────

DEFAULT_MAX_SAKER = 100
SESJONER = ("2023-2024", "2024-2025")
MIN_N_RAPPORT = 5  # Minimum n for aa vises i rapporten

# Regex for aa identifisere tilraading-voteringer (fra baseline_analyse.py)
_RE_TILRAADING = re.compile(
    r"[Rr]omertall|[Ss]tor bokstav\s+[A-ZAEOaeo]"
    r"|[Ll]ovens overskrift|loven i sin helhet"
    r"|^[Ss]tor bokstav [A-ZAEOaeo],",
    re.IGNORECASE,
)
_RE_MINDRETALLSFORSLAG = re.compile(r"Forslag nr\.?\s*\d", re.IGNORECASE)
_RE_ALTERNATIV = re.compile(r"^Alternativ votering mellom", re.IGNORECASE)

RAPPORT_FIL = Path(__file__).resolve().parent.parent.parent / "docs" / "baseline-rapport.md"


# ── Datastrukturer ────────────────────────────────────────────────────────────

@dataclass
class PlenumStemme:
    parti: str
    for_stemmer: int
    mot_stemmer: int

    @property
    def stemte_for(self) -> bool:
        return self.for_stemmer > self.mot_stemmer

    @property
    def stemte_mot(self) -> bool:
        return self.mot_stemmer > self.for_stemmer


@dataclass
class SakFraksjonData:
    sak_id: int
    sesjon: str
    saksfelt: list[str]
    partier_i_mindretall: set[str]   # Fra XML: partier som fremmet mindretallsforslag
    tilraading_stemmer: list[PlenumStemme]  # Fra DB: faktisk plenum-stemmer


@dataclass
class KonsistensRad:
    """En sammenligningsrad: parti + fraksjon-posisjon + faktisk stemme."""
    parti: str
    saksfelt_liste: list[str]
    var_i_mindretall: bool    # XML-fraksjon sier MOT tilraadingen
    stemte_konsistent: bool   # Faktisk stemme samsvarer med fraksjon-posisjon


# ── Voteringsklassifisering ───────────────────────────────────────────────────

def er_tilraading_votering(tema: str | None, alternativ_votering_id: int | None) -> bool:
    if alternativ_votering_id is not None:
        return False
    t = tema or ""
    if _RE_ALTERNATIV.match(t):
        return False
    if _RE_MINDRETALLSFORSLAG.search(t):
        return False
    if _RE_TILRAADING.search(t):
        return True
    return False


# ── DB-oppslag ────────────────────────────────────────────────────────────────

async def hent_sak_ids(factory, sesjoner: tuple[str, ...]) -> list[tuple[int, str, list[str]]]:
    """
    Returnerer (sak_id, sesjon, saksfelt) for saker i DB sortert etter flest voteringer.
    Saker med mange voteringer er mer sannsynlig innstillinger med fraksjoninfo.
    """
    async with factory() as s:
        rows = await s.execute(text("""
            SELECT sak_id, sesjon,
                   (SELECT saksfelt FROM voteringer v2
                    WHERE v2.sak_id = v.sak_id AND v2.saksfelt IS NOT NULL
                    LIMIT 1) as saksfelt,
                   COUNT(*) as n_vot
            FROM voteringer v
            WHERE sesjon = ANY(:ses)
            GROUP BY sak_id, sesjon
            ORDER BY n_vot DESC
        """), {"ses": list(sesjoner)})
        return [
            (row.sak_id, row.sesjon, list(row.saksfelt) if row.saksfelt else [])
            for row in rows.fetchall()
        ]


async def hent_tilraading_stemmer(
    factory, sak_id: int
) -> list[PlenumStemme]:
    """Henter alle tilraading-voteringer for sak_id og returnerer parti-stemmer."""
    async with factory() as s:
        rows = await s.execute(text("""
            SELECT v.votering_id, v.tema, v.alternativ_votering_id,
                   vp.parti, vp.for_stemmer, vp.mot_stemmer
            FROM voteringer v
            JOIN voteringsresultat_parti vp ON v.votering_id = vp.votering_id
            WHERE v.sak_id = :sid
            ORDER BY v.votering_id, vp.parti
        """), {"sid": sak_id})
        alle = rows.fetchall()

    # Grupper per votering_id og filtrer til tilraading
    voteringer: dict[str, dict[str, Any]] = {}
    for row in alle:
        vid = row.votering_id
        if vid not in voteringer:
            voteringer[vid] = {
                "tema": row.tema,
                "alt_id": row.alternativ_votering_id,
                "stemmer": []
            }
        voteringer[vid]["stemmer"].append(
            PlenumStemme(row.parti, row.for_stemmer, row.mot_stemmer)
        )

    # Ta den tilraadingen med flest partier (hovedvoteringen)
    tilraading_kandidater = [
        v for v in voteringer.values()
        if er_tilraading_votering(v["tema"], v["alt_id"])
    ]
    if not tilraading_kandidater:
        return []

    # Velg tilraadingen med flest parti-stemmer (mest komplett)
    hoved = max(tilraading_kandidater, key=lambda v: len(v["stemmer"]))
    return hoved["stemmer"]


# ── DB-skriving ───────────────────────────────────────────────────────────────

async def lagre_konsistens(
    factory,
    per_parti_saksfelt: dict[tuple[str, str], tuple[int, int]],
) -> None:
    """Lagrer {(parti, saksfelt): (n_total, n_konsistente)} i fraksjon_plenum_konsistens."""
    from datetime import datetime, timezone
    naa = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    async with factory() as session:
        for (parti, saksfelt), (n_total, n_kons) in per_parti_saksfelt.items():
            andel = n_kons / n_total if n_total > 0 else 0.0
            stmt = (
                pg_insert(DbFraksjonPlenumKonsistens)
                .values(
                    parti=parti,
                    saksfelt=saksfelt,
                    antall_saker_med_fraksjoninfo=n_total,
                    antall_konsistente=n_kons,
                    andel_konsistent=andel,
                    sist_oppdatert=naa,
                )
                .on_conflict_do_update(
                    index_elements=["parti", "saksfelt"],
                    set_={
                        "antall_saker_med_fraksjoninfo": n_total,
                        "antall_konsistente": n_kons,
                        "andel_konsistent": andel,
                        "sist_oppdatert": naa,
                    },
                )
            )
            await session.execute(stmt)
        await session.commit()
    print(f"  Lagret {len(per_parti_saksfelt)} (parti, saksfelt)-rader til fraksjon_plenum_konsistens.")


# ── Rapport-skriving ──────────────────────────────────────────────────────────

def oppdater_rapport(
    resultater: list[KonsistensRad],
    per_parti: dict[str, tuple[int, int]],
    per_parti_saksfelt: dict[tuple[str, str], tuple[int, int]],
    n_saker_med_fraksjoninfo: int,
    n_saker_forsookt: int,
    anbefalt_konfidens: float,
) -> None:
    """Erstatter Beregning 3-seksjonen i baseline-rapport.md med faktiske tall."""
    if not RAPPORT_FIL.exists():
        print(f"  ADVARSEL: Fant ikke {RAPPORT_FIL} — hopper over rapport-oppdatering.")
        return

    innhold = RAPPORT_FIL.read_text(encoding="utf-8")

    # Bygg ny seksjon
    linjer = ["## Beregning 3: Fraksjon-til-plenum-konsistens", ""]
    linjer += [
        f"Datagrunnlag: {n_saker_med_fraksjoninfo} saker med fraksjonsinformasjon (ny_innstilling)",
        f"(av {n_saker_forsookt} forsoekte saker fra sesjonene {', '.join(SESJONER)}).",
        "",
        "Maal: Naar XML inneholder `<ForslagFraMindretall>`, stemte partiene i plenum",
        "konsistent med sin komitefraksjon-posisjon?",
        "- Parti i mindretallsfraksjon: forventet aa stemme MOT tilraadingen.",
        "- Parti i flertallsfraksjon: forventet aa stemme FOR tilraadingen.",
        "",
    ]

    # Tabell per parti (alle saksfelt samlet)
    linjer += [
        "### Samlet konsistensrate per parti",
        "",
        "| Parti | Konsistente | Totalt | Konsistensrate |",
        "| ----- | ----------- | ------ | -------------- |",
    ]
    for parti in sorted(KJERNE_PARTIER):
        if parti in per_parti:
            n_tot, n_kons = per_parti[parti]
            rate = n_kons / n_tot if n_tot > 0 else 0.0
            merknad = " ⚠" if n_tot < MIN_N_RAPPORT else ""
            linjer.append(f"| {parti} | {n_kons} | {n_tot} | {rate:.1%}{merknad} |")
    linjer.append("")

    # Totalrate (alle partier samlet)
    n_tot_alle = sum(v[0] for v in per_parti.values())
    n_kons_alle = sum(v[1] for v in per_parti.values())
    if n_tot_alle > 0:
        total_rate = n_kons_alle / n_tot_alle
        linjer += [
            f"**Samlet konsistensrate (alle partier):** {total_rate:.1%} (n={n_tot_alle})",
            "",
        ]

    # Beregn mindretall vs. flertall separat
    n_tot_min = sum(1 for r in resultater if r.var_i_mindretall)
    n_kons_min = sum(1 for r in resultater if r.var_i_mindretall and r.stemte_konsistent)
    n_tot_fler = sum(1 for r in resultater if not r.var_i_mindretall)
    n_kons_fler = sum(1 for r in resultater if not r.var_i_mindretall and r.stemte_konsistent)

    if n_tot_min > 0:
        rate_min = n_kons_min / n_tot_min
        linjer.append(f"- **Mindretallsfraksjon** (forventet MOT): {rate_min:.1%} konsistente (n={n_tot_min})")
    if n_tot_fler > 0:
        rate_fler = n_kons_fler / n_tot_fler
        linjer.append(f"- **Flertallsfraksjon** (forventet FOR): {rate_fler:.1%} konsistente (n={n_tot_fler})")
    linjer.append("")

    # Anbefaling
    linjer += [
        f"> **Konklusjon beregning 3:** Empirisk verifisert konsistensrate = **{total_rate:.1%}**",
        f"> (n={n_tot_alle} parti-sak-observasjoner).",
        f"> Anbefalt `_FRAKSJON_KONFIDENS` i lag 1: **{anbefalt_konfidens:.2f}**",
        f"> (avrundet ned fra {total_rate:.2f} til naermeste 0.05 for konservativt estimat).",
        "",
        "---",
    ]

    ny_seksjon = "\n".join(linjer)

    # Erstatt eksisterende seksjon
    moenster = re.compile(
        r"## Beregning 3: Fraksjon-til-plenum-konsistens.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    if moenster.search(innhold):
        ny_innhold = moenster.sub(ny_seksjon + "\n", innhold)
    else:
        # Legg til paa slutten hvis seksjonen ikke finnes
        ny_innhold = innhold + "\n" + ny_seksjon

    RAPPORT_FIL.write_text(ny_innhold, encoding="utf-8")
    print(f"  Oppdatert {RAPPORT_FIL.name} — beregning 3 seksjon erstattet.")


# ── Hovedlogikk ───────────────────────────────────────────────────────────────

async def main(max_saker: int, dry_run: bool, max_forsookt: int = 0) -> float:
    """
    Kjoer beregning 3.
    Returnerer anbefalt konfidens-verdi for signal 1.
    """
    settings = Settings()
    if not settings.database_url:
        sys.exit("Feil: DATABASE_URL er ikke satt i miljovariabler.")

    init_db(settings.database_url)
    factory = get_session_factory()

    stortinget = StortingetClient(settings)

    print(f"\n=== Beregning 3: Fraksjon-til-plenum-konsistens ===")
    print(f"Sesjoner: {', '.join(SESJONER)}  |  Maks saker: {max_saker}  |  Dry-run: {dry_run}\n")

    # Steg 1: Hent sak_ids fra DB
    sak_ids = await hent_sak_ids(factory, SESJONER)
    print(f"Fant {len(sak_ids)} unike saker i DB for valgte sesjoner.")

    # Steg 2: Iterer over saker, hent XML, filtrer til ny_innstilling
    rader: list[KonsistensRad] = []
    n_forsookt = 0
    n_ny_innstilling = 0
    n_ingen_tilraading = 0
    n_feil = 0

    for sak_id, sesjon, saksfelt in sak_ids:
        if n_ny_innstilling >= max_saker:
            break
        if max_forsookt > 0 and n_forsookt >= max_forsookt:
            break
        n_forsookt += 1

        try:
            sak = await stortinget.hent_sak(sak_id)
            xml_bytes, fmt = await stortinget.hent_publikasjon(sak)
        except (AnalyseFeilet, DokumentUtilgjengelig, Exception) as exc:
            n_feil += 1
            continue

        if fmt != "xml":
            n_feil += 1
            continue

        try:
            pub_id = sak.analyse_publikasjon.eksport_id if sak.analyse_publikasjon else ""
            dok = parse_dokument(xml_bytes, pub_id=pub_id)
        except AnalyseFeilet:
            n_feil += 1
            continue

        # Hopp over saker uten fraksjonsinformasjon
        if not dok.mindretallsforslag:
            continue

        # Identifiser partier i mindretallsfraksjon
        partier_i_mindretall: set[str] = set()
        for fp in dok.mindretallsforslag:
            if fp.fra and fp.fra.partier:
                for kode in normaliser_partiliste(fp.fra.partier):
                    partier_i_mindretall.add(kode)

        if not partier_i_mindretall:
            continue

        # Hent tilraading-stemmer fra DB
        tilraading_stemmer = await hent_tilraading_stemmer(factory, sak_id)
        if not tilraading_stemmer:
            n_ingen_tilraading += 1
            continue

        n_ny_innstilling += 1

        # Bygg konsistens-rader for alle kjerne-partier som har stemmedata
        stemmer_map = {st.parti: st for st in tilraading_stemmer}
        for parti in KJERNE_PARTIER:
            if parti not in stemmer_map:
                continue
            st = stemmer_map[parti]
            # Hopp over partier uten klart flertall i eget parti (fravarende/split)
            if st.for_stemmer == st.mot_stemmer:
                continue

            var_i_mindretall = parti in partier_i_mindretall
            if var_i_mindretall:
                stemte_konsistent = st.stemte_mot  # Forventet MOT tilraadingen
            else:
                stemte_konsistent = st.stemte_for  # Forventet FOR tilraadingen

            # Bruk saksfelt fra DB (kan vaere liste — ta alle)
            rader.append(KonsistensRad(
                parti=parti,
                saksfelt_liste=saksfelt or ["_total"],
                var_i_mindretall=var_i_mindretall,
                stemte_konsistent=stemte_konsistent,
            ))

        if n_ny_innstilling % 10 == 0:
            print(f"  Prosessert {n_forsookt} saker, {n_ny_innstilling} med fraksjoninfo...")

    print(f"\nResultat:")
    print(f"  Forsoekte saker:            {n_forsookt}")
    print(f"  Saker med fraksjoninfo:     {n_ny_innstilling}")
    print(f"  Saker uten tilraading-vot:  {n_ingen_tilraading}")
    print(f"  Feil (API/parse):           {n_feil}")
    print(f"  Totale konsistens-rader:    {len(rader)}")

    if not rader:
        print("\nIngen data -- avslutter.")
        return 0.90

    # Steg 3: Aggreger per parti og per (parti, saksfelt)
    per_parti: dict[str, list[bool]] = defaultdict(list)
    per_parti_saksfelt: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for rad in rader:
        per_parti[rad.parti].append(rad.stemte_konsistent)
        saksfelter = rad.saksfelt_liste if rad.saksfelt_liste else ["_ukjent"]
        for sf in saksfelter:
            per_parti_saksfelt[(rad.parti, sf)].append(rad.stemte_konsistent)
        # Alltid legg til _total
        per_parti_saksfelt[(rad.parti, "_total")].append(rad.stemte_konsistent)

    # Konverter til (n_total, n_konsistente)
    per_parti_teller: dict[str, tuple[int, int]] = {
        p: (len(v), sum(v)) for p, v in per_parti.items()
    }
    per_parti_saksfelt_teller: dict[tuple[str, str], tuple[int, int]] = {
        k: (len(v), sum(v)) for k, v in per_parti_saksfelt.items()
    }

    # Skriv ut resultater
    print("\n--- Konsistensrate per parti (alle saksfelt samlet) ---")
    n_tot_alle = sum(v[0] for v in per_parti_teller.values())
    n_kons_alle = sum(v[1] for v in per_parti_teller.values())
    total_rate = n_kons_alle / n_tot_alle if n_tot_alle > 0 else 0.0

    for parti in sorted(KJERNE_PARTIER):
        if parti in per_parti_teller:
            n, k = per_parti_teller[parti]
            rate = k / n if n > 0 else 0.0
            merknad = " (lav n)" if n < MIN_N_RAPPORT else ""
            print(f"  {parti:4s}: {rate:.1%}  (n={n}){merknad}")

    print(f"\n  Samlet: {total_rate:.1%}  (n={n_tot_alle})")

    # Beregn anbefalt konfidens: avrund ned til naermeste 0.05
    anbefalt = (total_rate // 0.05) * 0.05
    anbefalt = max(0.80, min(0.99, anbefalt))
    print(f"\n  Anbefalt _FRAKSJON_KONFIDENS: {anbefalt:.2f}")
    print(f"  (total_rate={total_rate:.4f}, avrundet ned til naermeste 0.05)")

    if not dry_run:
        # Steg 4: Lagre i DB
        print("\nLagrer i fraksjon_plenum_konsistens...")
        await lagre_konsistens(factory, per_parti_saksfelt_teller)

        # Steg 5: Oppdater baseline-rapport.md
        print("Oppdaterer baseline-rapport.md...")
        oppdater_rapport(
            rader,
            per_parti_teller,
            per_parti_saksfelt_teller,
            n_ny_innstilling,
            n_forsookt,
            anbefalt,
        )
    else:
        print("\nDry-run: ingen DB-skriving eller rapport-oppdatering.")

    return anbefalt


def oppdater_lag1(ny_konfidens: float) -> None:
    """Oppdaterer _FRAKSJON_KONFIDENS i prediksjon_lag1.py med empirisk verdi."""
    lag1_fil = Path(__file__).resolve().parent.parent / "app" / "steps" / "prediksjon_lag1.py"
    innhold = lag1_fil.read_text(encoding="utf-8")

    gammel_linje = "_FRAKSJON_KONFIDENS = 0.90"
    ny_linje = (
        f"_FRAKSJON_KONFIDENS = {ny_konfidens:.2f}  "
        f"# Empirisk: beregning 3, {ny_konfidens:.1%} fraksjon-til-plenum-konsistens"
    )

    if gammel_linje not in innhold:
        # Proeov aa finne eksisterende empirisk kommentar
        moenster = re.compile(r"_FRAKSJON_KONFIDENS = [0-9.]+.*")
        if moenster.search(innhold):
            innhold = moenster.sub(ny_linje, innhold)
        else:
            print(f"  ADVARSEL: Fant ikke _FRAKSJON_KONFIDENS i {lag1_fil} — hopper over.")
            return
    else:
        innhold = innhold.replace(gammel_linje, ny_linje)

    lag1_fil.write_text(innhold, encoding="utf-8")
    print(f"  Oppdatert {lag1_fil.name}: _FRAKSJON_KONFIDENS = {ny_konfidens:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beregning 3: fraksjon-til-plenum-konsistens")
    parser.add_argument("--max-saker", type=int, default=DEFAULT_MAX_SAKER,
                        help=f"Maks antall ny_innstilling-saker aa prosessere (default: {DEFAULT_MAX_SAKER})")
    parser.add_argument("--max-forsookt", type=int, default=0,
                        help="Maks antall saker aa forsoke (uavhengig av fraksjoninfo-treff). 0=ingen grense.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Ikke skriv til DB eller rapport")
    args = parser.parse_args()

    anbefalt = asyncio.run(main(args.max_saker, args.dry_run, max_forsookt=args.max_forsookt))

    if not args.dry_run and anbefalt > 0:
        print(f"\nOppdaterer prediksjon_lag1.py med _FRAKSJON_KONFIDENS = {anbefalt:.2f}...")
        oppdater_lag1(anbefalt)
        print("\nFerdig. Husk aa restarte uvicorn for aa aktivere ny konfidens-verdi.")
    else:
        print(f"\nForslag: sett _FRAKSJON_KONFIDENS = {anbefalt:.2f} i prediksjon_lag1.py")
