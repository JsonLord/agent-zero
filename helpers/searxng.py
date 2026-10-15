"""Bounded search with an optional existing, free DuckDuckGo fallback."""

import asyncio
import logging
import os
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp

URL = "http://localhost:55510/search"
log = logging.getLogger(__name__)


async def search(query: str):
    from helpers import runtime

    return await runtime.call_development_function(_search, query=query)


def _timeout():
    try:
        return min(60, max(1, float(os.getenv("A0_SEARCH_TIMEOUT_SECONDS", "15"))))
    except ValueError:
        return 15


async def _searxng(query):
    timeout = aiohttp.ClientTimeout(total=_timeout(), connect=min(3, _timeout()))
    async with (
        aiohttp.ClientSession(timeout=timeout) as session,
        session.post(
            os.getenv("A0_SEARXNG_URL", URL), data={"q": query, "format": "json"}
        ) as response,
    ):
        response.raise_for_status()
        data = await response.json()
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise TypeError("invalid search response")
        return _normalize(data["results"])


def _normalize(rows):
    results = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("invalid search result")
        url = row.get("url", row.get("href", ""))
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        results.append(
            {
                "title": str(row.get("title") or url),
                "url": url,
                "content": str(row.get("content", row.get("body", "")) or ""),
            }
        )
    return results[:10]


async def _duckduckgo(query):
    # Use the existing provider's HTML backend with verified TLS. The pinned
    # DDGS client hardcodes verify=False, so it must not perform our requests.
    timeout = aiohttp.ClientTimeout(total=_timeout(), connect=min(3, _timeout()))
    async with (
        aiohttp.ClientSession(timeout=timeout, trust_env=True) as session,
        session.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            allow_redirects=False,
        ) as response,
    ):
        response.raise_for_status()
        if response.status != 200:
            raise ValueError("unexpected search redirect")
        html = await response.text()
    return _parse_duckduckgo(html)


def _parse_duckduckgo(html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for item in soup.select(".result"):
        link = item.select_one(".result__a")
        if link is None:
            continue
        url = urljoin("https://duckduckgo.com/", str(link.get("href", "")))
        parsed = urlparse(url)
        if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
            url = parse_qs(parsed.query).get("uddg", [url])[0]
        snippet = item.select_one(".result__snippet")
        rows.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": url,
                "content": snippet.get_text(" ", strip=True) if snippet else "",
            }
        )
    if not rows and soup.select_one(".no-results") is None:
        raise ValueError("search response contains no recognized results")
    return _normalize(rows)


def _reason(error):
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    if isinstance(error, aiohttp.ClientResponseError):
        return f"http_{error.status}"
    if isinstance(error, aiohttp.ClientConnectorError):
        import socket

        if isinstance(error.os_error, socket.gaierror):
            return "dns_failure"
        return (
            "connection_refused"
            if isinstance(error.os_error, ConnectionRefusedError)
            else "connection_failed"
        )
    if isinstance(error, (ValueError, TypeError, aiohttp.ContentTypeError)):
        return "invalid_response"
    return "provider_error"


async def _search(query: str):
    backend = os.getenv("A0_SEARCH_BACKEND", "auto").lower()
    providers = {"searxng": _searxng, "duckduckgo": _duckduckgo}
    if backend not in {*providers, "auto"}:
        return {
            "status": "unavailable",
            "backend": backend,
            "reason": "invalid_configuration",
            "fallback_attempted": False,
            "results": [],
        }
    names = ["searxng", "duckduckgo"] if backend == "auto" else [backend]
    failures = []
    for name in names:
        try:
            results = await providers[name](query)
            return {
                "status": "ok",
                "backend": name,
                "fallback_attempted": bool(failures),
                "results": results,
            }
        except asyncio.CancelledError:
            raise
        except (
            aiohttp.ClientError,
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            TimeoutError,
        ) as error:
            reason = _reason(error)
            log.warning("Search backend %s unavailable: %s", name, reason)
            failures.append({"backend": name, "reason": reason})
    return {
        "status": "unavailable",
        **failures[0],
        "fallback_attempted": len(failures) > 1,
        "results": [],
        "failures": failures,
    }
