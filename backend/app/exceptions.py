from __future__ import annotations


class SakIkkeFunnet(Exception):
    """Sak-ID eksisterer ikke i Stortingets API."""


class DokumentUtilgjengelig(Exception):
    """Dokumentet (HTML/PDF) kan ikke hentes."""


class AnalyseFeilet(Exception):
    """Analysepipeline feilet uventet."""
