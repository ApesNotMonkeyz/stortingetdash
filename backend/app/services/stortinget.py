from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

import httpx
import structlog
from lxml import etree

from app.config import Settings
from app.exceptions import DokumentUtilgjengelig, SakIkkeFunnet
from app.models.sak import Sak

log = structlog.get_logger()

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BASE_DELAY = 1.0


class StortingetClient:
    """
    Async HTTP-klient mot data.stortinget.no.

    Brukes via FastAPI dependency injection — ikke som singleton.
    Én instans per request er tiltenkt mønster.
    """

    def __init__(self, settings: Settings) -> None:
        self._base = settings.stortinget_base_url.rstrip("/")
        self._headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        }

    async def hent_sak(self, sak_id: str | int) -> Sak:
        """
        Henter saksmetadata fra /eksport/sak.

        Reiser SakIkkeFunnet hvis sak-ID ikke eksisterer.
        """
        url = f"{self._base}/eksport/sak"
        raw = await self._get(url, {"sakid": str(sak_id), "format": "json"})
        return Sak.model_validate(raw)

    async def hent_publikasjon(
        self, sak: Sak
    ) -> tuple[bytes, Literal["xml", "html"]]:
        """
        Velger analyse-publikasjon for saken (innstilling type 6 foretrekkes,
        ellers originalforslaget) og henter innhold.

        Prøver XML (standardformat). Hvis lxml ikke klarer å parse resultatet,
        faller vi tilbake til HTML-versjonen.

        Returnerer (innhold_bytes, format) der format er 'xml' eller 'html'.
        Reiser DokumentUtilgjengelig hvis ingen publikasjoner finnes.
        """
        pub = sak.analyse_publikasjon
        if pub is None:
            raise DokumentUtilgjengelig(
                f"Ingen publikasjoner å hente for sak {sak.id}"
            )

        url = f"{self._base}/eksport/publikasjon"

        xml_bytes = await self._get_bytes(
            url, {"publikasjonid": pub.eksport_id}
        )
        try:
            etree.fromstring(xml_bytes)
            log.info(
                "publikasjon_xml_ok",
                sak_id=sak.id,
                pub_id=pub.eksport_id,
                bytes=len(xml_bytes),
            )
            return xml_bytes, "xml"
        except etree.XMLSyntaxError:
            log.warning(
                "publikasjon_xml_ugyldig_html_fallback",
                sak_id=sak.id,
                pub_id=pub.eksport_id,
            )

        html_bytes = await self._get_bytes(
            url, {"publikasjonid": pub.eksport_id, "format": "html"}
        )
        log.info(
            "publikasjon_html_ok",
            sak_id=sak.id,
            pub_id=pub.eksport_id,
            bytes=len(html_bytes),
        )
        return html_bytes, "html"

    # ── Intern HTTP-logikk ────────────────────────────────────────────────────

    async def _get(self, url: str, params: dict[str, str]) -> Any:
        """GET med exponential backoff på rate-limit og forbigående serverfeil."""
        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    r = await client.get(url, params=params)
                except httpx.TransportError as exc:
                    if attempt == _MAX_ATTEMPTS - 1:
                        raise
                    delay = _BASE_DELAY * 2**attempt
                    log.warning(
                        "stortinget_transport_error",
                        url=url,
                        attempt=attempt,
                        delay=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                    continue

                if r.status_code == 404:
                    raise SakIkkeFunnet(f"Sak ikke funnet: {url} params={params}")

                if r.status_code in _RETRY_STATUSES:
                    # Stortinget returnerer 500 med {"feilkode":...} for ugyldige IDer
                    # — dette er en applikasjonsfeil, ikke en forbigående serverfeil.
                    if r.status_code == 500:
                        try:
                            body = json.loads(r.content.decode("utf-8"))
                            if "feilkode" in body:
                                raise SakIkkeFunnet(
                                    f"Sak ikke funnet (feilkode={body.get('feilkode')}): "
                                    f"{url} params={params}"
                                )
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass

                    if attempt == _MAX_ATTEMPTS - 1:
                        r.raise_for_status()
                    delay = float(
                        r.headers.get("Retry-After", _BASE_DELAY * 2**attempt)
                    )
                    log.warning(
                        "stortinget_retry",
                        url=url,
                        status=r.status_code,
                        delay=delay,
                        attempt=attempt,
                    )
                    await asyncio.sleep(delay)
                    continue

                r.raise_for_status()
                log.info(
                    "stortinget_ok",
                    url=url,
                    status=r.status_code,
                    attempt=attempt,
                )
                return json.loads(r.content.decode("utf-8"))

        raise RuntimeError("unreachable")  # tilfredsstiller mypy

    async def _get_bytes(self, url: str, params: dict[str, str]) -> bytes:
        """
        GET med exponential backoff; returnerer råbytes.
        Brukes for publikasjoner (XML/HTML) i stedet for JSON.
        Reiser DokumentUtilgjengelig på 404.
        """
        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    r = await client.get(url, params=params)
                except httpx.TransportError as exc:
                    if attempt == _MAX_ATTEMPTS - 1:
                        raise
                    delay = _BASE_DELAY * 2**attempt
                    log.warning(
                        "stortinget_transport_error",
                        url=url,
                        attempt=attempt,
                        delay=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                    continue

                if r.status_code == 404:
                    raise DokumentUtilgjengelig(
                        f"Publikasjon ikke funnet: {url} params={params}"
                    )

                if r.status_code in _RETRY_STATUSES:
                    if attempt == _MAX_ATTEMPTS - 1:
                        r.raise_for_status()
                    delay = float(
                        r.headers.get("Retry-After", _BASE_DELAY * 2**attempt)
                    )
                    log.warning(
                        "stortinget_retry",
                        url=url,
                        status=r.status_code,
                        delay=delay,
                        attempt=attempt,
                    )
                    await asyncio.sleep(delay)
                    continue

                r.raise_for_status()
                log.info(
                    "stortinget_ok",
                    url=url,
                    status=r.status_code,
                    attempt=attempt,
                )
                return r.content

        raise RuntimeError("unreachable")  # tilfredsstiller mypy
