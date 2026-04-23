from __future__ import annotations

# Normalisering av partinavn til kanoniske koder brukt i Stortingets API.
# Søkes i prioritert rekkefølge: fulle navn før forkortelser.

_KODE_MAP: dict[str, str] = {
    # Fulle navn (lowercased)
    "sosialistisk venstreparti": "SV",
    "kristelig folkeparti": "KrF",
    "miljøpartiet de grønne": "MDG",
    "miljøpartiet dei grøne": "MDG",
    "fremskrittspartiet": "FrP",
    "arbeiderpartiet": "A",
    "arbeiderpartia": "A",
    "senterpartiet": "Sp",
    "senterpartia": "Sp",
    "pensjonistpartiet": "PF",
    "pensjonistforbundets": "PF",
    "høyre": "H",
    "venstre": "V",
    "rødt": "R",
    # Forkortelser (lowercased) — etter fulle navn for å unngå delvis treff
    "frp": "FrP",
    "krf": "KrF",
    "mdg": "MDG",
    "sv": "SV",
    "sp": "Sp",
    "ap": "A",
    "a": "A",
    "h": "H",
    "v": "V",
    "r": "R",
    "pf": "PF",
    "uav": "Uav",
}

# Partier representert i Stortinget 2021–2025. PF og Uav holdes utenfor
# kjerne-prediksjoner da de er transiente (pensjonistparti / uavhengige).
KJERNE_PARTIER: list[str] = ["A", "H", "Sp", "FrP", "SV", "V", "MDG", "R", "KrF"]
ALLE_PARTIER: list[str] = KJERNE_PARTIER + ["PF", "Uav"]


def normaliser_parti(navn: str) -> str | None:
    """
    Normaliserer et rått partinavn fra XML eller API til kanonisk kode.
    Returnerer None for ukjente navn.
    """
    if not navn:
        return None
    return _KODE_MAP.get(navn.strip().lower())


def normaliser_partiliste(raa_liste: list[str]) -> list[str]:
    """Normaliserer en liste med råe partinavn. Ukjente filtreres bort."""
    resultat: list[str] = []
    for navn in raa_liste:
        kode = normaliser_parti(navn)
        if kode and kode not in resultat:
            resultat.append(kode)
    return resultat
