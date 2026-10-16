import asyncio
import errno
import json
import socket
from types import SimpleNamespace

import aiohttp
import pytest

from helpers import searxng as search


@pytest.fixture(autouse=True)
def no_live_tinyfish_key(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rows",
    [[], [{"title": "Title", "url": "https://example.org", "content": "Snippet"}]],
)
async def test_healthy_and_empty(monkeypatch, rows):
    async def healthy(query):
        return rows

    monkeypatch.setattr(search, "_searxng", healthy)
    result = await search._search("query")
    assert result["status"] == "ok" and result["results"] == rows
    assert not result["fallback_attempted"]


ERRORS = [
    (
        aiohttp.ClientConnectorError(
            SimpleNamespace(ssl=False, host="localhost", port=55510),
            ConnectionRefusedError(errno.ECONNREFUSED, "refused"),
        ),
        "connection_refused",
    ),
    (
        aiohttp.ClientConnectorError(
            SimpleNamespace(ssl=False, host="missing", port=80),
            socket.gaierror(-2, "missing"),
        ),
        "dns_failure",
    ),
    (TimeoutError(), "timeout"),
    (aiohttp.ClientConnectionError(), "provider_error"),
    (aiohttp.ClientResponseError(None, (), status=500), "http_500"),
    (aiohttp.ClientResponseError(None, (), status=429), "http_429"),
    (json.JSONDecodeError("invalid", "", 0), "invalid_response"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("error,reason", ERRORS)
@pytest.mark.parametrize("fallback", [True, False])
async def test_failure_semantics(monkeypatch, error, reason, fallback):
    monkeypatch.setenv("A0_SEARCH_BACKEND", "auto")

    async def fail(query):
        raise error

    async def second(query):
        if not fallback:
            raise RuntimeError("private provider response must not escape")
        return [
            {
                "title": "Actual result",
                "url": "https://example.org",
                "content": "Snippet",
            }
        ]

    monkeypatch.setattr(search, "_searxng", fail)
    monkeypatch.setattr(search, "_duckduckgo", second)
    result = await search._search("query")
    assert result["fallback_attempted"]
    assert result["status"] == ("ok" if fallback else "unavailable")
    if fallback:
        assert result["backend"] == "duckduckgo"
        assert result["results"][0]["content"] == "Snippet"
    else:
        assert result["reason"] == reason and result["results"] == []
        assert "private" not in json.dumps(result)


@pytest.mark.asyncio
async def test_cancellation_is_not_fallback(monkeypatch):
    async def cancel(query):
        raise asyncio.CancelledError

    async def never(query):
        pytest.fail("must not fall back on cancellation")

    monkeypatch.setattr(search, "_searxng", cancel)
    monkeypatch.setattr(search, "_duckduckgo", never)
    with pytest.raises(asyncio.CancelledError):
        await search._search("cancel")


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_mix_results(monkeypatch):
    async def healthy(query):
        await asyncio.sleep(0)
        return [{"title": query, "url": "https://example.org", "content": query}]

    monkeypatch.setattr(search, "_searxng", healthy)
    results = await asyncio.gather(*(search._search(str(i)) for i in range(20)))
    assert [r["results"][0]["title"] for r in results] == list(map(str, range(20)))


@pytest.mark.asyncio
async def test_actual_http_contract_and_timeout(monkeypatch):
    captured = {}

    class Response:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def raise_for_status(self):
            captured["checked_status"] = True

        async def json(self):
            return {
                "results": [
                    {"title": "x", "url": "https://example.org", "content": "y"}
                ]
            }

    class Session(Response):
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return Response()

    monkeypatch.setattr(search.aiohttp, "ClientSession", Session)
    monkeypatch.setenv("A0_SEARXNG_URL", "http://127.0.0.1:55510/search")
    result = await search._searxng("q")
    assert captured["checked_status"] and captured["timeout"].total == 15
    assert captured["timeout"].connect == 3 and captured["data"]["format"] == "json"
    assert result[0]["content"] == "y"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,body,reason",
    [
        (500, "{}", "http_500"),
        (429, "{}", "http_429"),
        (200, "invalid json", "invalid_response"),
        (200, "{}", "invalid_response"),
    ],
)
async def test_loopback_http_failures_are_structured(monkeypatch, status, body, reason):
    from aiohttp import web

    app = web.Application()

    async def handler(request):
        return web.Response(text=body, status=status, content_type="application/json")

    app.router.add_post("/search", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    monkeypatch.setenv("A0_SEARXNG_URL", f"http://127.0.0.1:{port}/search")
    monkeypatch.setenv("A0_SEARCH_BACKEND", "searxng")
    try:
        result = await search._search("query")
        assert result["status"] == "unavailable" and result["reason"] == reason
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_unavailable_search_uses_normal_tool_response(monkeypatch):
    from tools import search_engine

    received = []

    async def intervention(message):
        received.append(message)

    async def unavailable(query):
        return {
            "status": "unavailable",
            "backend": "searxng",
            "reason": "connection_refused",
            "fallback_attempted": True,
            "results": [],
        }

    monkeypatch.setattr(search_engine, "searxng", unavailable)
    tool = search_engine.SearchEngine(
        SimpleNamespace(handle_intervention=intervention),
        "search_engine",
        None,
        {},
        "",
        None,
    )
    response = await tool.execute(query="search")
    assert (
        not response.break_loop
        and json.loads(response.message)["status"] == "unavailable"
    )
    assert received == [response.message]


def test_duckduckgo_html_preserves_results_and_decodes_source_urls():
    html = """<div class="result"><h2><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fdocs">Real title</a></h2>
    <a class="result__snippet">Source <b>snippet</b></a></div>"""
    assert search._parse_duckduckgo(html) == [
        {
            "title": "Real title",
            "url": "https://example.org/docs",
            "content": "Source snippet",
        }
    ]
    assert search._parse_duckduckgo('<div class="no-results">No results</div>') == []
    with pytest.raises(ValueError):
        search._parse_duckduckgo("<html>challenge page</html>")


@pytest.mark.asyncio
async def test_duckduckgo_transport_keeps_tls_verification_and_proxy_support(
    monkeypatch,
):
    captured = {}

    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            captured["closed"] = True

        def raise_for_status(self):
            pass

        async def text(self):
            return '<div class="no-results">No results</div>'

    class Session(Response):
        def __init__(self, **kwargs):
            captured["session"] = kwargs

        def post(self, url, **kwargs):
            captured.update(url=url, request=kwargs)
            return Response()

    monkeypatch.setattr(search.aiohttp, "ClientSession", Session)
    assert await search._duckduckgo("query") == []
    assert captured["session"]["trust_env"] is True
    assert captured["session"]["timeout"].total == 15
    assert captured["request"]["allow_redirects"] is False
    assert "ssl" not in captured["request"] and "connector" not in captured["session"]
    assert captured["url"].startswith("https://") and captured["closed"]
