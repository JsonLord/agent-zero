"""Optional, bounded Tinyfish REST fallback; credentials never enter errors."""

from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlparse

import aiohttp

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"


class TinyfishError(RuntimeError):
    """Safe provider failure code; no response body or credential is retained."""


def configured() -> bool:
    return bool(os.getenv("TINYFISH_API_KEY", "").strip())


async def _request(method, endpoint, *, timeout, max_bytes, **kwargs):
    key = os.getenv("TINYFISH_API_KEY", "").strip()
    if not key:
        raise TinyfishError("not_configured")
    budget = aiohttp.ClientTimeout(total=min(60, max(1, timeout)), connect=3)
    try:
        async with (
            aiohttp.ClientSession(timeout=budget, trust_env=True) as session,
            session.request(
                method,
                endpoint,
                headers={"X-API-Key": key, "Accept": "application/json"},
                allow_redirects=False,
                **kwargs,
            ) as response,
        ):
            if response.status != 200:
                raise TinyfishError(f"http_{response.status}")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise TinyfishError("response_too_large")
            data = json.loads(body)
            if not isinstance(data, dict):
                raise TinyfishError("invalid_response")
            return data
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        raise TinyfishError("timeout") from None
    except (aiohttp.ClientError, OSError):
        raise TinyfishError("connection_failed") from None
    except (ValueError, TypeError):
        raise TinyfishError("invalid_response") from None


async def search(query: str, *, timeout=15) -> list[dict]:
    data = await _request(
        "GET",
        SEARCH_URL,
        params={"query": query},
        timeout=timeout,
        max_bytes=2 * 1024 * 1024,
    )
    if data.get("error") or data.get("errors"):
        raise TinyfishError("provider_error")
    rows = data.get("results")
    if not isinstance(rows, list):
        raise TinyfishError("invalid_response")
    results = []
    for row in rows[:10]:
        if not isinstance(row, dict):
            raise TinyfishError("invalid_response")
        url = row.get("url")
        if not isinstance(url, str):
            raise TinyfishError("invalid_response")
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise TinyfishError("invalid_response")
        results.append(
            {
                "title": str(row.get("title") or url),
                "url": url,
                "content": str(row.get("snippet") or ""),
            }
        )
    return results


async def fetch(
    url: str, *, timeout=30, max_bytes=50 * 1024 * 1024
) -> tuple[str, bytes]:
    from helpers.network import UnsafeUrlError, validate_public_http_url

    if urlparse(url).scheme != "https":
        raise UnsafeUrlError(
            "Tinyfish fetch fallback only supports public HTTPS content"
        )
    await asyncio.to_thread(validate_public_http_url, url)
    data = await _request(
        "POST",
        FETCH_URL,
        json={"urls": [url], "format": "markdown"},
        timeout=timeout,
        max_bytes=min(50 * 1024 * 1024, max_bytes * 6 + 65536),
    )
    if data.get("error") or data.get("errors"):
        raise TinyfishError("provider_error")
    rows = data.get("results")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise TinyfishError("fetch_failed")
    page = rows[0]
    if (
        page.get("url") != url
        or not isinstance(page.get("text"), str)
        or not page["text"].strip()
    ):
        raise TinyfishError("invalid_response")
    final_url = page.get("final_url") or url
    if not isinstance(final_url, str) or urlparse(final_url).scheme != "https":
        raise TinyfishError("invalid_response")
    await asyncio.to_thread(validate_public_http_url, final_url)
    content = page["text"].encode("utf-8")
    if len(content) > max_bytes:
        raise TinyfishError("response_too_large")
    return final_url, content
