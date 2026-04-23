#!/usr/bin/env python3
"""
Baseline-analyse: beregner empiriske voteringsmønstre fra databasen.

Kjøres fra backend/-mappen:
    python scripts/baseline_analyse.py

Produserer:
  - parti_moenster og parti_korrelasjon i PostgreSQL
  - docs/baseline-rapport.md (stopp-og-evaluer-rapport)

Beregning 0: Voteringsstruktur og korrekt klassifisering av mindretallsforslag
Beregning 1: Parti-saksfelt-profil (empirisk prior)
Beregning 2: FOR-rate på tilrådinger (regjeringspartier)
Beregning 3: Fraksjon-til-plenum-konsistens (TODO — krever XML-kobling)
Beregning 4: Krysspress-saker
Beregning 5: Parti-par-korrelasjon
Beregning 6: Saksfelt-predikabilitet
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import REGJERINGER, Settings, regjering_partier_for_dato
from app.db.models import DbFraksjonPlenumKonsistens, DbPartiKorrelasjon, DbPartiMoenster

import asyncio
import structlog, structlog.stdlib

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

MIN_N = 5

DOK_PROPOSISJON  = "2"
DOK_REPR_FORSLAG = "4"
DOK_GRUNNLOV     = "5"
DOK_INNSTILLING  = "6"


# ── Datastruktur ──────────────────────────────────────────────────────────────

@dataclass
class Votering:
    votering_id: str
    sak_id: int
    sesjon: str
    dato: date
    tema: str | None
    saksfelt: list[str]
    dokumentgruppe: str
    vedtatt: bool | None
    alternativ_votering_id: int | None
    parti_stemmer: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    # parti -> (for_stemmer, mot_stemmer, fravarende)


# ── Partiidentifisering fra voteringstema ─────────────────────────────────────
# Brukes til å avgjøre om et mindretallsforslag er fremmet av et regjeringsparti
# eller utelukkende av opposisjonen.

# Søkes i prioritert rekkefølge (lengst/mest spesifikt navn først)
_PARTI_MULTIORD: list[tuple[str, str]] = [
    ("sosialistisk venstreparti", "SV"),
    ("kristelig folkeparti", "KrF"),
    ("miljøpartiet de grønne", "MDG"),
    ("miljøpartiet dei grøne", "MDG"),
    ("fremskrittspartiet", "FrP"),
    ("arbeiderpartiet", "A"),
    ("arbeiderpartia", "A"),
    ("senterpartiet", "Sp"),
    ("senterpartia", "Sp"),
    ("pensjonistpartiet", "PF"),
    ("pensjonistforbundets", "PF"),
    ("høyre", "H"),
    ("venstre", "V"),
    ("rødt", "R"),
]

# Forkortelser søkes som hele ord etter at fulle navn er fjernet
_PARTI_FORK_RE = re.compile(r'\b(FrP|KrF|MDG|SV|Sp|AP|A|H|V|R)\b', re.IGNORECASE)
_PARTI_FORK_MAP: dict[str, str] = {
    "frp": "FrP", "krf": "KrF", "mdg": "MDG", "sv": "SV",
    "sp": "Sp", "ap": "A", "a": "A", "h": "H", "v": "V", "r": "R",
}

_RE_PAAVEGNEAV     = re.compile(r"på vegne av\s+(.+)", re.IGNORECASE)
_RE_REPRESENTANTER = re.compile(r",?\s*representantene?\s+.+", re.IGNORECASE)
_RE_MINDRETALLET   = re.compile(r"et mindretall i komiteen,?\s*", re.IGNORECASE)


def parse_partier_fra_tema(tema: str | None) -> list[str]:
    """Ekstraherer partikoder fra voteringstema («på vegne av PARTI»)."""
    if not tema:
        return []
    m = _RE_PAAVEGNEAV.search(tema)
    if not m:
        return []
    tekst = _RE_REPRESENTANTER.sub("", m.group(1))
    tekst = _RE_MINDRETALLET.sub("", tekst)

    funnet: list[str] = []
    t = tekst.lower()

    for navn, kode in _PARTI_MULTIORD:
        if navn in t:
            t = t.replace(navn, " ")
            if kode not in funnet:
                funnet.append(kode)

    for m2 in _PARTI_FORK_RE.finditer(t):
        kode = _PARTI_FORK_MAP.get(m2.group(0).lower())
        if kode and kode not in funnet:
            funnet.append(kode)

    return funnet


# ── Voteringsklassifisering ───────────────────────────────────────────────────

_RE_MINDRETALLSFORSLAG = re.compile(r"Forslag nr\.?\s*\d", re.IGNORECASE)
_RE_TILRAADING = re.compile(
    r"[Rr]omertall|[Ss]tor bokstav\s+[A-ZÆØÅa-zæøå]"
    r"|[Ll]ovens overskrift|loven i sin helhet"
    r"|^[Ss]tor bokstav [A-ZÆØÅa-zæøå],",
    re.IGNORECASE,
)
_RE_ALTERNATIV = re.compile(r"^Alternativ votering mellom", re.IGNORECASE)

VOTERINGSTYPE_TILRAADING                = "tilraading"
VOTERINGSTYPE_MINDRETALLSFORSLAG_RP     = "mindretallsforslag_rp"
VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP    = "mindretallsforslag_opp"
VOTERINGSTYPE_MINDRETALLSFORSLAG_UKJENT = "mindretallsforslag_ukjent"
VOTERINGSTYPE_ALTERNATIV                = "alternativ"
VOTERINGSTYPE_ANNET                     = "annet"

ALLE_MINDRETALLSFORSLAG = {
    VOTERINGSTYPE_MINDRETALLSFORSLAG_RP,
    VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP,
    VOTERINGSTYPE_MINDRETALLSFORSLAG_UKJENT,
}


def klassifiser_votering(
    tema: str | None,
    alternativ_votering_id: int | None,
    dato: date,
) -> str:
    """
    Klassifiserer voteringstype basert på tema, alternativ_votering_id og dato.

    dato brukes til å avgjøre om forslagsstilleren er et regjeringsparti:
    - mindretallsforslag_rp:     fremmet av minst ett regjeringsparti
    - mindretallsforslag_opp:    fremmet utelukkende av opposisjonspartier
    - mindretallsforslag_ukjent: parti ikke identifisert fra tema-teksten
    """
    if alternativ_votering_id is not None:
        return VOTERINGSTYPE_ALTERNATIV
    t = tema or ""
    if _RE_ALTERNATIV.match(t):
        return VOTERINGSTYPE_ALTERNATIV
    if _RE_MINDRETALLSFORSLAG.search(t):
        partier = parse_partier_fra_tema(t)
        if not partier:
            return VOTERINGSTYPE_MINDRETALLSFORSLAG_UKJENT
        rp = regjering_partier_for_dato(dato)
        return (
            VOTERINGSTYPE_MINDRETALLSFORSLAG_RP
            if any(p in rp for p in partier)
            else VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP
        )
    if _RE_TILRAADING.search(t):
        return VOTERINGSTYPE_TILRAADING
    return VOTERINGSTYPE_ANNET


def majority_vote(for_s: int, mot_s: int) -> str | None:
    if for_s > mot_s:
        return "for"
    if mot_s > for_s:
        return "mot"
    return None


def er_regjeringsparti(parti: str, dato: date) -> bool:
    return parti in regjering_partier_for_dato(dato)


# ── Data-lasting ──────────────────────────────────────────────────────────────

async def last_alle_voteringer(engine) -> list[Votering]:
    async with engine.connect() as c:
        rows = await c.execute(text("""
            SELECT
                v.votering_id, v.sak_id, v.sesjon, v.dato,
                v.tema, v.saksfelt, v.dokumentgruppe, v.vedtatt,
                v.alternativ_votering_id,
                vp.parti, vp.for_stemmer, vp.mot_stemmer, vp.fravarende
            FROM voteringer v
            JOIN voteringsresultat_parti vp ON v.votering_id = vp.votering_id
            ORDER BY v.votering_id, vp.parti
        """))

    voteringer: dict[str, Votering] = {}
    for row in rows:
        vid = row.votering_id
        if vid not in voteringer:
            voteringer[vid] = Votering(
                votering_id=vid,
                sak_id=row.sak_id,
                sesjon=row.sesjon,
                dato=row.dato,
                tema=row.tema,
                saksfelt=list(row.saksfelt or []),
                dokumentgruppe=str(row.dokumentgruppe or ""),
                vedtatt=row.vedtatt,
                alternativ_votering_id=row.alternativ_votering_id,
            )
        voteringer[vid].parti_stemmer[row.parti] = (
            row.for_stemmer, row.mot_stemmer, row.fravarende
        )

    result = list(voteringer.values())
    log.info("data_lastet", voteringer=len(result))
    return result


# ── Beregning 0: Voteringsstruktur ────────────────────────────────────────────

def beregning_0(voteringer: list[Votering]) -> dict[str, Any]:
    """
    Voteringstype-fordeling (med RP/OPP-skille for mindretallsforslag)
    og FOR-rate for regjeringspartier per (dok, type).
    """
    type_fordeling: dict[tuple[str, str], int] = defaultdict(int)
    for_rate: dict[tuple[str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    for v in voteringer:
        dok = v.dokumentgruppe
        vtype = klassifiser_votering(v.tema, v.alternativ_votering_id, v.dato)
        type_fordeling[(dok, vtype)] += 1

        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            if not er_regjeringsparti(parti, v.dato):
                continue
            if for_s == 0 and mot_s == 0:
                continue
            mv = majority_vote(for_s, mot_s)
            if mv is None:
                continue
            r, n = for_rate[(dok, vtype)]
            for_rate[(dok, vtype)] = (r + (1 if mv == "for" else 0), n + 1)

    return {
        "type_fordeling": dict(type_fordeling),
        "for_rate": {k: {"for_andel": r / n, "n": n} for k, (r, n) in for_rate.items() if n > 0},
    }


# ── Beregning 1: Empirisk prior ───────────────────────────────────────────────

def beregning_1(voteringer: list[Votering]) -> dict[tuple[str, str], dict[str, Any]]:
    """
    FOR%-profil per (parti, saksfelt) på tvers av ALLE omstridte voteringer.
    Ekskluderer alternativvoteringer (50/50 per konstruksjon).
    Brukes som empirisk prior for prediksjonsmodellen.
    """
    teller: dict[tuple[str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    for v in voteringer:
        if klassifiser_votering(v.tema, v.alternativ_votering_id, v.dato) == VOTERINGSTYPE_ALTERNATIV:
            continue
        saksfelter = v.saksfelt if v.saksfelt else ["_ukjent"]
        felter = saksfelter + ["_total"]

        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            if for_s == 0 and mot_s == 0:
                continue
            mv = majority_vote(for_s, mot_s)
            if mv is None:
                continue
            for sf in felter:
                r, n = teller[(parti, sf)]
                teller[(parti, sf)] = (r + (1 if mv == "for" else 0), n + 1)

    return {(parti, sf): {"andel_for": r / n, "n": n} for (parti, sf), (r, n) in teller.items()}


# ── Beregning 2: FOR-rate på tilrådinger ─────────────────────────────────────

def beregning_2(voteringer: list[Votering]) -> dict[tuple[str, str], dict[str, Any]]:
    """
    FOR%-profil for regjeringspartier på tilraading-voteringer per saksfelt.
    Lav FOR% er normalt: omstridte tilrådinger er typisk opposisjonsamendmenter.
    """
    teller: dict[tuple[str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    for v in voteringer:
        if klassifiser_votering(v.tema, v.alternativ_votering_id, v.dato) != VOTERINGSTYPE_TILRAADING:
            continue
        saksfelter = v.saksfelt if v.saksfelt else ["_ukjent"]
        felter = saksfelter + ["_total"]

        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            if not er_regjeringsparti(parti, v.dato):
                continue
            if for_s == 0 and mot_s == 0:
                continue
            mv = majority_vote(for_s, mot_s)
            if mv is None:
                continue
            for sf in felter:
                r, n = teller[(parti, sf)]
                teller[(parti, sf)] = (r + (1 if mv == "for" else 0), n + 1)

    return {(parti, sf): {"andel_for": r / n, "n": n} for (parti, sf), (r, n) in teller.items()}


# ── Beregning 3: Fraksjon-til-plenum (TODO) ───────────────────────────────────

def beregning_3_todo() -> dict[str, str]:
    return {
        "status": "TODO",
        "forklaring": (
            "Krever kobling mellom voteringer og fraksjonsinformasjon fra "
            "innstillingens XML (<Fraksjon Fra='...'>). "
            "Gjennomføres etter at saksanalyse-pipelinen er kjørt mot de "
            "aktuelle sakene og fraksjonsinformasjon er tilgjengelig i DB."
        ),
    }


# ── Beregning 4: Krysspress-saker ─────────────────────────────────────────────

def beregning_4(voteringer: list[Votering]) -> list[dict[str, Any]]:
    """
    Voteringer der et regjeringsparti brøt med forventet retning.

    Semantikk: for_stemmer = stemte for tilrådingen, mot_stemmer = stemte mot tilrådingen
    (dvs. for det alternative forslagets vedtagelse).

    - mindretallsforslag_rp  → MOT  (regjeringen stemmer MOT tilrådingen = FOR egne forslag)
    - mindretallsforslag_opp → FOR  (regjeringen stemmer FOR tilrådingen = MOT opposisjonens forslag)
    - Proposisjon + tilraading → FOR  (regjeringen stemmer FOR tilrådingen på egne proposisjoner)
    """
    avvik = []

    for v in voteringer:
        dok = v.dokumentgruppe
        vtype = klassifiser_votering(v.tema, v.alternativ_votering_id, v.dato)

        if vtype == VOTERINGSTYPE_MINDRETALLSFORSLAG_RP:
            forventet = "mot"
        elif vtype == VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP:
            forventet = "for"
        elif dok == DOK_PROPOSISJON and vtype == VOTERINGSTYPE_TILRAADING:
            forventet = "for"
        else:
            continue

        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            if not er_regjeringsparti(parti, v.dato):
                continue
            mv = majority_vote(for_s, mot_s)
            if mv is None:
                continue
            if mv != forventet:
                avvik.append({
                    "votering_id": v.votering_id,
                    "sak_id": v.sak_id,
                    "sesjon": v.sesjon,
                    "dato": str(v.dato),
                    "dokumentgruppe": dok,
                    "voteringstype": vtype,
                    "parti": parti,
                    "forventet": forventet,
                    "faktisk": mv,
                    "for_stemmer": for_s,
                    "mot_stemmer": mot_s,
                    "saksfelt": v.saksfelt[:3],
                    "tema": (v.tema or "")[:80],
                })

    return sorted(avvik, key=lambda x: x["dato"])


# ── Beregning 5: Parti-par-korrelasjon ───────────────────────────────────────

def beregning_5(voteringer: list[Votering]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Andel voteringer der to partier stemte likt, per saksfelt."""
    teller: dict[tuple[str, str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    for v in voteringer:
        saksfelter = v.saksfelt if v.saksfelt else ["_ukjent"]
        felter = saksfelter + ["_total"]

        parti_mv: dict[str, str] = {}
        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            mv = majority_vote(for_s, mot_s)
            if mv is not None:
                parti_mv[parti] = mv

        for pa, pb in combinations(sorted(parti_mv.keys()), 2):
            er_lik = 1 if parti_mv[pa] == parti_mv[pb] else 0
            for sf in felter:
                lik, n = teller[(pa, pb, sf)]
                teller[(pa, pb, sf)] = (lik + er_lik, n + 1)

    return {(pa, pb, sf): {"andel_lik": lik / n, "n": n} for (pa, pb, sf), (lik, n) in teller.items()}


# ── Beregning 6: Saksfelt-predikabilitet ─────────────────────────────────────

def beregning_6(voteringer: list[Votering]) -> dict[str, dict[str, Any]]:
    """Per saksfelt: varians i FOR-andel. Lav varians = forutsigbart saksfelt."""
    sf_obs: dict[str, list[float]] = defaultdict(list)

    for v in voteringer:
        saksfelter = v.saksfelt if v.saksfelt else ["_ukjent"]
        for parti, (for_s, mot_s, _) in v.parti_stemmer.items():
            total = for_s + mot_s
            if total == 0:
                continue
            for sf in saksfelter:
                sf_obs[sf].append(for_s / total)

    result: dict[str, dict[str, Any]] = {}
    for sf, obs in sf_obs.items():
        if len(obs) < MIN_N:
            continue
        mean = sum(obs) / len(obs)
        var = sum((x - mean) ** 2 for x in obs) / len(obs)
        result[sf] = {
            "mean_andel_for": mean,
            "varians": var,
            "n_observasjoner": len(obs),
            "predikabilitet": "hoy" if var < 0.05 else "middels" if var < 0.15 else "lav",
        }

    alle_obs = [o for obs_list in sf_obs.values() for o in obs_list]
    if alle_obs:
        mean = sum(alle_obs) / len(alle_obs)
        var = sum((x - mean) ** 2 for x in alle_obs) / len(alle_obs)
        result["_total"] = {
            "mean_andel_for": mean,
            "varians": var,
            "n_observasjoner": len(alle_obs),
            "predikabilitet": "hoy" if var < 0.05 else "middels" if var < 0.15 else "lav",
        }

    return result


# ── DB-skriving ───────────────────────────────────────────────────────────────

async def lagre_parti_moenster(engine, b1: dict, b2: dict) -> int:
    from datetime import datetime
    now = datetime.utcnow()
    rader = 0

    kombinert: dict[tuple[str, str, str], dict] = {}
    for (parti, sf), data in b1.items():
        kombinert[(parti, sf, "")] = {
            "parti": parti, "saksfelt": sf, "dokumentgruppe": "",
            "antall_voteringer": data["n"],
            "andel_for": data["andel_for"],
            "andel_mot": 1.0 - data["andel_for"],
        }
    for (parti, sf), data in b2.items():
        kombinert[(parti, sf, "tilraading")] = {
            "parti": parti, "saksfelt": sf, "dokumentgruppe": "tilraading",
            "antall_voteringer": data["n"],
            "andel_for": data["andel_for"],
            "andel_mot": 1.0 - data["andel_for"],
        }

    async with engine.begin() as c:
        for rad in kombinert.values():
            if rad["antall_voteringer"] < MIN_N:
                continue
            stmt = (
                pg_insert(DbPartiMoenster)
                .values(**rad, sist_oppdatert=now)
                .on_conflict_do_update(
                    index_elements=["parti", "saksfelt", "dokumentgruppe"],
                    set_={
                        "antall_voteringer": rad["antall_voteringer"],
                        "andel_for": rad["andel_for"],
                        "andel_mot": rad["andel_mot"],
                        "sist_oppdatert": now,
                    },
                )
            )
            await c.execute(stmt)
            rader += 1

    return rader


async def lagre_parti_korrelasjon(engine, b5: dict) -> int:
    from datetime import datetime
    now = datetime.utcnow()
    rader = 0

    async with engine.begin() as c:
        for (pa, pb, sf), data in b5.items():
            if data["n"] < MIN_N:
                continue
            stmt = (
                pg_insert(DbPartiKorrelasjon)
                .values(
                    parti_a=pa, parti_b=pb, saksfelt=sf,
                    andel_lik_stemme=data["andel_lik"],
                    antall_voteringer=data["n"],
                    sist_oppdatert=now,
                )
                .on_conflict_do_update(
                    index_elements=["parti_a", "parti_b", "saksfelt"],
                    set_={
                        "andel_lik_stemme": data["andel_lik"],
                        "antall_voteringer": data["n"],
                        "sist_oppdatert": now,
                    },
                )
            )
            await c.execute(stmt)
            rader += 1

    return rader


# ── Rapportgenerering ─────────────────────────────────────────────────────────

def _pst(v: float | None) -> str:
    return f"{v * 100:.1f}%" if v is not None else "—"


def _tabell(headers: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(h), max((len(str(r[i])) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]
    sep    = "| " + " | ".join("-" * w for w in widths) + " |"
    header = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    lines  = [header, sep]
    for row in rows:
        lines.append("| " + " | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))) + " |")
    return "\n".join(lines)


def generer_rapport(
    voteringer: list[Votering],
    b0: dict,
    b1: dict,
    b2: dict,
    b3: dict,
    b4: list,
    b5: dict,
    b6: dict,
) -> str:
    from datetime import date as date_cls

    sesjoner        = sorted({v.sesjon for v in voteringer})
    partier_i_data  = sorted({p for v in voteringer for p in v.parti_stemmer})

    DOK_NAVN = {
        "1": "Lovforslag", "2": "Proposisjon", "3": "dok=3",
        "4": "Repr.forslag", "5": "Grunnlov", "6": "Innstilling", "7": "dok=7",
    }
    VTYPE_KORT = {
        VOTERINGSTYPE_TILRAADING:                "Komiteens tilråding",
        VOTERINGSTYPE_MINDRETALLSFORSLAG_RP:     "Mindretallsforslag (RP)",
        VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP:    "Mindretallsforslag (opp)",
        VOTERINGSTYPE_MINDRETALLSFORSLAG_UKJENT: "Mindretallsforslag (ukjent)",
        VOTERINGSTYPE_ALTERNATIV:                "Alternativ votering",
        VOTERINGSTYPE_ANNET:                     "Annet / prosedyre",
    }

    lines: list[str] = []

    # ── Header ──
    lines += [
        "# Baseline-analyse — Stortinget voteringsmønstre",
        "",
        f"Generert: {date_cls.today().isoformat()}",
        "",
        "> **Stopp-og-evaluer-steg.** Les denne rapporten og vurder tallene før",
        "> prediksjonsmodulen (lag 1–2) bygges videre. Tallene her bestemmer hvilke",
        "> regler som er empirisk verifiserte og pålitelige nok til å bruke.",
        "",
        "---",
        "",
        "## Datagrunnlag",
        "",
        f"- Sesjoner i databasen: {', '.join(sesjoner)}",
        f"- Totalt voteringer: {len(voteringer)}",
        f"- Totalt parti-resultat-rader: {sum(len(v.parti_stemmer) for v in voteringer)}",
        f"- Partier representert: {', '.join(partier_i_data)}",
        "",
        "Tall basert på lite data (n < 10) er merket ⚠ og bør ikke brukes som grunnlag for regler.",
        "",
        "---",
        "",
    ]

    # ── Beregning 0 ──
    lines += [
        "## Beregning 0: Voteringsstruktur og seleksjonsbias",
        "",
        "### Korrekt forståelse av «mindretallsforslag»",
        "",
        "«Mindretallsforslag» er forslag fremmet av mindretallet **i komiteen** — partier som",
        "ikke fikk komitéflertall for sin posisjon. Det er **ikke** automatisk forslag fra",
        "opposisjonspartier generelt.",
        "",
        "Støre-regjeringen er en **mindretallsregjering** uten flertall i Stortinget.",
        "Konsekvens: opposisjonen har ofte flertall i komiteene, og regjeringens versjon",
        "havner i mindretall. Regjeringspartiene fremmer da **egne** mindretallsforslag i",
        "plenum — og stemmer FOR disse. Tilrådingen er ofte opposisjonens versjon, som",
        "regjeringen stemmer MOT.",
        "",
        "Voteringstemaet inneholder «på vegne av PARTI» som identifiserer forslagsstilleren.",
        "Mindretallsforslag klassifiseres nå i tre grupper:",
        "",
        "| Kategori | Forslagsstiller | Forventet data-retning (majority_vote) | Betydning |",
        "| --- | --- | --- | --- |",
        "| mindretallsforslag_rp | Minst ett regjeringsparti | **mot** (mot tilrådingen) | Støtter egne forslag |",
        "| mindretallsforslag_opp | Utelukkende opposisjonspartier | **for** (for tilrådingen) | Motarbeider opp-forslag |",
        "| mindretallsforslag_ukjent | Parti ikke identifisert fra tema | — | — |",
        "",
        "### Enstemmige voteringer er ikke i databasen",
        "",
        "Stortingets API returnerer tomme voteringsresultatlister for **enstemmige voteringer**",
        "(`votering_resultat_type=5`). Databasen inneholder kun *omstridte* voteringer.",
        "FOR-rater nedenfor gjelder utelukkende omstridte saker.",
        "",
        "### Regjeringssammensetning per periode",
        "",
    ]

    rj_rows = [
        [p["navn"], p["fra"], p["til"] if p["til"] else "(sittende)", ", ".join(p["partier"])]
        for p in REGJERINGER
    ]
    lines.append(_tabell(["Regjering", "Fra (inkl.)", "Til (ekskl.)", "Partier"], rj_rows))
    lines.append("")
    lines.append(
        "Sp er regjeringsparti for voteringer t.o.m. 2025-01-29. "
        "Fra 2025-01-30 behandles Sp som opposisjonsparti."
    )
    lines += ["", "### Voteringstype-distribusjon", ""]

    total_dist: dict[str, int] = defaultdict(int)
    for (dok, vtype), n in b0["type_fordeling"].items():
        total_dist[vtype] += n

    dist_order = [
        VOTERINGSTYPE_MINDRETALLSFORSLAG_RP,
        VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP,
        VOTERINGSTYPE_MINDRETALLSFORSLAG_UKJENT,
        VOTERINGSTYPE_TILRAADING,
        VOTERINGSTYPE_ALTERNATIV,
        VOTERINGSTYPE_ANNET,
    ]
    dist_rows = [
        [VTYPE_KORT.get(vt, vt), str(total_dist.get(vt, 0))]
        for vt in dist_order
        if total_dist.get(vt, 0) > 0
    ]
    lines.append(_tabell(["Voteringstype", "Antall voteringer"], dist_rows))
    lines += [
        "",
        "### Stemme-semantikk og FOR-rate",
        "",
        "**`for_stemmer`** = stemte **for tilrådingen** (komiteens flertallsposisjon).",
        "**`mot_stemmer`** = stemte **mot tilrådingen** = for det alternative forslagets vedtagelse.",
        "",
        "FOR-rate = andel (votering × parti) der partiet stemte FOR tilrådingen.",
        "",
        "Forventet FOR-rate for regjeringspartier:",
        "- **mindretallsforslag_rp ≈ 0 %**: regjeringen stemmer MOT tilrådingen (dvs. FOR egne forslag).",
        "- **mindretallsforslag_opp ≈ 100 %**: regjeringen stemmer FOR tilrådingen (dvs. MOT opposisjonens forslag).",
        "- **Proposisjon + tilråding ≈ 100 %**: regjeringen støtter tilrådingen på egne proposisjoner.",
        "",
        "### FOR-rate for regjeringspartier per (dok-type, voteringstype)",
        "",
    ]

    rate_rows = []
    for (dok, vtype), d in sorted(b0["for_rate"].items(), key=lambda x: (x[0][0], x[0][1])):
        if d["n"] < MIN_N:
            continue
        rate_rows.append([
            DOK_NAVN.get(dok, f"dok={dok}"),
            VTYPE_KORT.get(vtype, vtype),
            _pst(d["for_andel"]),
            str(d["n"]),
        ])
    if rate_rows:
        lines.append(_tabell(["Dok-type", "Voteringstype", "FOR-andel (rp)", "n (votering×parti)"], rate_rows))

    lines += [
        "",
        "**Tolkning:**",
        "- mindretallsforslag_rp + FOR ≈ 0 %: ✓ Forventet — regjeringen stemmer MOT tilrådingen (FOR egne forslag).",
        "- mindretallsforslag_opp + FOR ≈ 100 %: ✓ Forventet — regjeringen stemmer FOR tilrådingen (MOT opposisjonsforslag).",
        "- Avvik i opp-kategorien: forhandlede pakker (regjeringen støtter opposisjonsforslag som del av flertallsforlik).",
        "- Tilråding + lav FOR: ✓ Forventet for mindretallsregjering — opposisjonens versjon er tilrådingen.",
        "",
        "> **Konklusjon beregning 0:** Semantikken er bekreftet: `for_stemmer` = for tilrådingen,",
        "> `mot_stemmer` = for alternativet. For prediksjon: RP-parti på RP-forslag → predict «mot».",
        "> RP-parti på Opp-forslag → predict «for». Avvik er forhandlede flertallspakker.",
    ]
    lines += ["", "---", ""]

    # ── Beregning 1 ──
    lines += [
        "## Beregning 1: Parti-saksfelt-profil (FOR-andel, alle omstridte voteringer)",
        "",
        "For hvert parti: andel omstridte voteringer der partiet stemte FOR, per saksfelt.",
        "Ekskluderer alternativvoteringer (50/50 per konstruksjon).",
        "Brukes som empirisk prior for prediksjonsmodellen.",
        "",
    ]

    alle_partier_sorted = sorted({p for (p, sf) in b1 if not sf.startswith("_")})
    b1_samlet = [(p, b1.get((p, "_total"), {})) for p in alle_partier_sorted if (p, "_total") in b1]
    if b1_samlet:
        rows = [
            [p, _pst(d.get("andel_for")), str(d.get("n", 0))]
            for p, d in b1_samlet if d.get("n", 0) >= MIN_N
        ]
        lines.append(_tabell(["Parti", "FOR-andel (alle omstridte)", "n"], rows))
        lines += [
            "",
            "> Tall gjelder omstridte voteringer. Enstemmige mangler fra DB.",
            "> Reell FOR-andel er høyere — spesielt for konsensusnære partier.",
            "",
        ]

    alle_rp = sorted({p for periode in REGJERINGER for p in periode["partier"]})
    b1_sf = {
        (parti, sf): data
        for (parti, sf), data in b1.items()
        if not sf.startswith("_") and parti in alle_rp and data["n"] >= MIN_N
    }
    if b1_sf:
        lines.append(f"### {' og '.join(alle_rp)} — FOR-andel per saksfelt (n ≥ 5)")
        lines.append("")
        sf_rows = [
            [parti, sf, _pst(data["andel_for"]), str(data["n"])]
            for (parti, sf), data in sorted(b1_sf.items(), key=lambda x: -x[1]["andel_for"])
        ]
        lines.append(_tabell(["Parti", "Saksfelt", "FOR-andel", "n"], sf_rows))
    else:
        lines.append("*For lite data per saksfelt (n < 5).*")

    lines += ["", "---", ""]

    # ── Beregning 2 ──
    lines += [
        "## Beregning 2: FOR-rate på omstridte tilrådinger (regjeringspartier)",
        "",
        "Andel ganger regjeringspartiene stemte FOR på omstridte tilrådingsvoteringer.",
        "Lav FOR-rate betyr at komiteen satte opposisjonens versjon som tilråding.",
        "",
    ]

    rp_liste = sorted({p for periode in REGJERINGER for p in periode["partier"]})
    b2_total = [(p, b2.get((p, "_total"), {})) for p in rp_liste if (p, "_total") in b2]
    if b2_total:
        rows = [[p, _pst(d.get("andel_for")), str(d.get("n", 0))] for p, d in b2_total]
        lines.append(_tabell(["Parti", "FOR-andel (tilraading, omstridt)", "n"], rows))
        lines.append("")

    b2_sf = {
        (parti, sf): data
        for (parti, sf), data in b2.items()
        if not sf.startswith("_") and parti in rp_liste and data["n"] >= MIN_N
    }
    if b2_sf:
        lines.append("### Per saksfelt (n ≥ 5)")
        lines.append("")
        rows = [
            [parti, sf, _pst(data["andel_for"]), str(data["n"])]
            for (parti, sf), data in sorted(b2_sf.items(), key=lambda x: -x[1]["andel_for"])
        ]
        lines.append(_tabell(["Parti", "Saksfelt", "FOR-andel (tilraading)", "n"], rows))
    else:
        lines.append("*For lite data per saksfelt (n < 5).*")

    lines += ["", "---", ""]

    # ── Beregning 3 ──
    lines += [
        "## Beregning 3: Fraksjon-til-plenum-konsistens",
        "",
        f"> **{b3['status']}** — {b3['forklaring']}",
        "",
        "Konsekvens: Konfidensverdien for signal 1 (fraksjonsinformasjon fra XML) i",
        "lag 1-prediksjonen kan ikke settes empirisk ennå. Bruk konservativt estimat",
        "(f.eks. 90%) som placeholder inntil denne beregningen er gjennomført.",
        "",
        "---",
        "",
    ]

    # ── Beregning 4 ──
    lines += [
        "## Beregning 4: Krysspress-saker",
        "",
        f"Voteringer der et regjeringsparti brøt med forventet retning. Totalt: {len(b4)}",
        "",
        "Forventet retning (ref. stemme-semantikk i beregning 0):",
        "- mindretallsforslag_rp → MOT (regjeringen stemmer mot tilrådingen = for egne forslag)",
        "- mindretallsforslag_opp → FOR (regjeringen stemmer for tilrådingen = mot opposisjonsforslag)",
        "- proposisjon + tilråding → FOR",
        "",
    ]

    if b4:
        rows = [
            [
                a["sesjon"], a["dato"], a["parti"],
                VTYPE_KORT.get(a["voteringstype"], a["voteringstype"])[:24],
                a["forventet"].upper(), a["faktisk"].upper(),
                f"{a['for_stemmer']}/{a['mot_stemmer']}",
                ", ".join(a["saksfelt"]) or "—",
            ]
            for a in b4[:30]
        ]
        lines.append(_tabell(
            ["Sesjon", "Dato", "Parti", "Type", "Forventet", "Faktisk", "For/Mot", "Saksfelt"],
            rows,
        ))
        if len(b4) > 30:
            lines.append(f"\n*...og {len(b4) - 30} til.*")
    else:
        lines.append("*Ingen krysspress-saker funnet med korrigert klassifisering.*")

    lines += ["", "---", ""]

    # ── Beregning 5 ──
    lines += [
        "## Beregning 5: Parti-par-korrelasjon",
        "",
        "Andel voteringer der to partier stemte likt (samlet, n ≥ 5).",
        "100% = alltid likt, 50% = tilfeldig.",
        "",
    ]

    korr_total = {
        (pa, pb): data
        for (pa, pb, sf), data in b5.items()
        if sf == "_total" and data["n"] >= MIN_N
    }
    if korr_total:
        partier_k = sorted({p for pair in korr_total for p in pair})
        header = [""] + partier_k
        matrix_rows = []
        for pa in partier_k:
            row = [pa]
            for pb in partier_k:
                if pa == pb:
                    row.append("—")
                elif (pa, pb) in korr_total:
                    row.append(_pst(korr_total[(pa, pb)]["andel_lik"]))
                elif (pb, pa) in korr_total:
                    row.append(_pst(korr_total[(pb, pa)]["andel_lik"]))
                else:
                    row.append("n/a")
            matrix_rows.append(row)
        lines.append(_tabell(header, matrix_rows))
        lines.append("")
        min_n = min(d["n"] for d in korr_total.values())
        lines.append(f"*Basert på {min_n}+ voteringer per par.*")
    else:
        lines.append("*For lite data (n < 5).*")

    lines += ["", "---", ""]

    # ── Beregning 6 ──
    lines += [
        "## Beregning 6: Saksfelt-predikabilitet",
        "",
        "Varians i andel FOR-stemmer per observasjon. Lav varians = forutsigbart saksfelt.",
        "Terskel: varians < 0.05 = høy, < 0.15 = middels, ≥ 0.15 = lav predikabilitet.",
        "",
    ]

    if b6:
        sf_rows = [
            [sf, data["predikabilitet"], _pst(data["mean_andel_for"]),
             f"{data['varians']:.3f}", str(data["n_observasjoner"])]
            for sf, data in sorted(b6.items(), key=lambda x: x[1]["varians"])
            if not sf.startswith("_")
        ]
        if sf_rows:
            lines.append(_tabell(
                ["Saksfelt", "Predikabilitet", "Snitt FOR-andel", "Varians", "n obs."],
                sf_rows,
            ))
            if "_total" in b6:
                t = b6["_total"]
                lines.append(f"\n**Samlet:** varians={t['varians']:.3f}, predikabilitet={t['predikabilitet']}")
        else:
            lines.append("*For lite data per saksfelt.*")
    else:
        lines.append("*Ingen saksfelter med n ≥ 5 observasjoner.*")

    lines += ["", "---", ""]

    # ── Konklusjon ──
    lines += ["## Konklusjon: Hvilke regler er pålitelige nok til å bruke?", ""]

    mf_rp_total  = b0["for_rate"].get(("4", VOTERINGSTYPE_MINDRETALLSFORSLAG_RP),  {})
    mf_opp_total = b0["for_rate"].get(("4", VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP), {})
    prop_tilr    = b0["for_rate"].get((DOK_PROPOSISJON, VOTERINGSTYPE_TILRAADING),  {})

    konklusjoner = [
        "ℹ **Beregning 0 (semantikk bekreftet):** for=tilråding, mot=alternativt forslag. "
        + (f"Repr.forslag_rp FOR-rate: {_pst(mf_rp_total.get('for_andel'))} (n={mf_rp_total.get('n',0)}) — forventet ≈ 0 %. " if mf_rp_total else "")
        + (f"Repr.forslag_opp FOR-rate: {_pst(mf_opp_total.get('for_andel'))} (n={mf_opp_total.get('n',0)}) — forventet ≈ 100 %." if mf_opp_total else ""),
    ]

    if b4:
        avvik_rp   = sum(1 for a in b4 if a["voteringstype"] == VOTERINGSTYPE_MINDRETALLSFORSLAG_RP)
        avvik_opp  = sum(1 for a in b4 if a["voteringstype"] == VOTERINGSTYPE_MINDRETALLSFORSLAG_OPP)
        avvik_tilr = sum(1 for a in b4 if a["voteringstype"] == VOTERINGSTYPE_TILRAADING)
        konklusjoner.append(
            f"⚠ **{len(b4)} krysspress-saker** "
            f"(RP-forslag FOR: {avvik_rp}, Opp-forslag MOT: {avvik_opp}, "
            f"Prop+tilråding MOT: {avvik_tilr}). Se beregning 4."
        )
    else:
        konklusjoner.append("✅ Ingen krysspress-saker med korrigert klassifisering.")

    konklusjoner.append(
        "❌ **Beregning 3 (fraksjon-til-plenum)** ikke gjennomført. "
        "Konfidens for signal 1 er empirisk ukjent. Sett placeholder 90%."
    )

    for k in konklusjoner:
        lines.append(k)
        lines.append("")

    lines += [
        "### Neste steg",
        "",
        "1. **Evaluer tallene** — verifiser at mindretallsforslag_rp → ≈ 0 % FOR (regjeringen",
        "   stemmer mot tilrådingen = for egne forslag), og mindretallsforslag_opp → ≈ 100 % FOR",
        "   (stemmer for tilrådingen). Krysspress-saker skal nå være reelle unntak.",
        "2. **Bygg lag 1–2** etter at baseline er verifisert.",
        "3. **Gjennomfør beregning 3** (fraksjon-til-plenum) etter XML-kobling er klar.",
        "",
        "---",
        "",
        f"*Rapport generert av `scripts/baseline_analyse.py` · {date_cls.today().isoformat()}*",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    settings = Settings()
    if not settings.database_url:
        log.error("DATABASE_URL_mangler")
        sys.exit(1)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    try:
        voteringer = await last_alle_voteringer(engine)
        if not voteringer:
            log.error("ingen_data", melding="Databasen er tom — kjør hent_voteringer.py først")
            sys.exit(1)

        log.info("starter_beregninger", n=len(voteringer))

        b0 = beregning_0(voteringer)
        log.info("b0_ferdig", typer=len(b0["type_fordeling"]))

        b1 = beregning_1(voteringer)
        log.info("b1_ferdig", nøkler=len(b1))

        b2 = beregning_2(voteringer)
        log.info("b2_ferdig", nøkler=len(b2))

        b3 = beregning_3_todo()

        b4 = beregning_4(voteringer)
        log.info("b4_ferdig", krysspress_saker=len(b4))

        b5 = beregning_5(voteringer)
        log.info("b5_ferdig", par_total=sum(1 for k in b5 if k[2] == "_total"))

        b6 = beregning_6(voteringer)
        log.info("b6_ferdig", saksfelter=len(b6))

        n_moenster = await lagre_parti_moenster(engine, b1, b2)
        n_korr     = await lagre_parti_korrelasjon(engine, b5)
        log.info("db_lagret", parti_moenster=n_moenster, parti_korrelasjon=n_korr)

        rapport = generer_rapport(voteringer, b0, b1, b2, b3, b4, b5, b6)

        rapport_sti = Path(__file__).resolve().parent.parent.parent / "docs" / "baseline-rapport.md"
        rapport_sti.write_text(rapport, encoding="utf-8")
        log.info("rapport_skrevet", sti=str(rapport_sti))

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
