import asyncio
import ipaddress
import json
from types import SimpleNamespace

import pytest

from helpers import network, searxng, tinyfish
from plugins._document_query.helpers import fetch as documents


@pytest.fixture(autouse=True)
def isolate_key_and_dns(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    monkeypatch.setattr(
        network,
        "resolve_host_ips",
        lambda host: (ipaddress.ip_address("93.184.216.34"),),
    )


def transport(monkeypatch, payload, *, status=200, raw=None):
    captured = {}

    class Response:
        def __init__(self):
            self.status = status
            self.content = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            captured["closed"] = True

        async def iter_chunked(self, size):
            if isinstance(payload, BaseException):
                raise payload
            yield raw if raw is not None else json.dumps(payload).encode()

    class Session:
        def __init__(self, **kwargs):
            captured["session"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def request(self, method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return Response()

    monkeypatch.setenv("TINYFISH_API_KEY", "unit-only-private-key")
    monkeypatch.setattr(tinyfish.aiohttp, "ClientSession", Session)
    return captured


@pytest.mark.asyncio
async def test_get_search_contract_and_result_normalization(monkeypatch):
    captured = transport(
        monkeypatch,
        {
            "results": [
                {
                    "title": "Title",
                    "url": "https://example.org/docs",
                    "snippet": "Snippet",
                }
            ]
        },
    )
    assert await tinyfish.search("query & symbols") == [
        {"title": "Title", "url": "https://example.org/docs", "content": "Snippet"}
    ]
    assert captured["method"] == "GET" and captured["url"] == tinyfish.SEARCH_URL
    assert captured["params"] == {"query": "query & symbols"}
    assert captured["headers"]["X-API-Key"] == "unit-only-private-key"
    assert captured["allow_redirects"] is False and captured["session"]["trust_env"]
    assert "ssl" not in captured and captured["session"]["timeout"].total == 15


@pytest.mark.asyncio
async def test_post_fetch_contract_and_markdown_metadata(monkeypatch):
    uri = "https://example.org/docs"
    captured = transport(
        monkeypatch,
        {
            "results": [
                {"url": uri, "final_url": uri + "/page", "text": "# Actual page"}
            ],
            "errors": [],
        },
    )
    final_url, content = await tinyfish.fetch(uri)
    assert (final_url, content) == (uri + "/page", b"# Actual page")
    assert captured["method"] == "POST" and captured["url"] == tinyfish.FETCH_URL
    assert captured["json"] == {"urls": [uri], "format": "markdown"}
    assert captured["allow_redirects"] is False
    assert captured["headers"]["X-API-Key"] == "unit-only-private-key"
    assert captured["session"]["timeout"].total == 30


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [302, 401, 402, 429, 500])
async def test_provider_errors_are_safe_and_never_follow_redirects(monkeypatch, status):
    captured = transport(monkeypatch, {"error": "unit-only-private-key"}, status=status)
    with pytest.raises(tinyfish.TinyfishError, match=f"http_{status}") as error:
        await tinyfish.search("query")
    assert (
        "unit-only-private-key" not in str(error.value)
        and error.value.__cause__ is None
    )
    assert captured["closed"] and captured["allow_redirects"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"results": None},
        {"results": [1]},
        {"results": [{"url": "file:///secret"}]},
        {"errors": ["upstream error"], "results": []},
    ],
)
async def test_invalid_search_payload_is_not_success(monkeypatch, payload):
    transport(monkeypatch, payload)
    with pytest.raises(tinyfish.TinyfishError):
        await tinyfish.search("query")


@pytest.mark.asyncio
async def test_empty_search_is_success_and_missing_key_never_sends(monkeypatch):
    transport(monkeypatch, {"results": []})
    assert await tinyfish.search("query") == []
    monkeypatch.delenv("TINYFISH_API_KEY")
    with pytest.raises(tinyfish.TinyfishError, match="not_configured"):
        await tinyfish.search("query")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [TimeoutError(), asyncio.CancelledError()])
async def test_timeout_is_bounded_and_cancellation_propagates(monkeypatch, payload):
    captured = transport(monkeypatch, payload)
    expected = (
        asyncio.CancelledError
        if isinstance(payload, asyncio.CancelledError)
        else tinyfish.TinyfishError
    )
    with pytest.raises(expected):
        await tinyfish.search("query")
    assert captured["closed"]


@pytest.mark.asyncio
async def test_wire_size_and_invalid_json_are_bounded(monkeypatch):
    transport(monkeypatch, {}, raw=b"x" * 100)
    with pytest.raises(tinyfish.TinyfishError, match="response_too_large"):
        await tinyfish._request("GET", tinyfish.SEARCH_URL, timeout=1, max_bytes=10)
    transport(monkeypatch, {}, raw=b"not json")
    with pytest.raises(tinyfish.TinyfishError, match="invalid_response"):
        await tinyfish.search("query")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page",
    [
        {"url": "https://example.org", "text": ""},
        {"url": "https://different.org", "text": "Wrong page"},
        {"url": "https://example.org", "text": 42},
    ],
)
async def test_fetch_errors_do_not_invent_page_content(monkeypatch, page):
    transport(monkeypatch, {"results": [page]})
    with pytest.raises(tinyfish.TinyfishError):
        await tinyfish.fetch("https://example.org")


@pytest.mark.asyncio
async def test_fetch_preserves_ssrf_and_content_limits(monkeypatch):
    uri = "https://example.org"
    transport(
        monkeypatch, {"results": [{"url": uri, "final_url": uri, "text": "123456"}]}
    )
    with pytest.raises(tinyfish.TinyfishError, match="response_too_large"):
        await tinyfish.fetch(uri, max_bytes=5)
    monkeypatch.setattr(
        network, "resolve_host_ips", lambda host: (ipaddress.ip_address("127.0.0.1"),)
    )
    with pytest.raises(network.UnsafeUrlError):
        await tinyfish.fetch("https://private.example")
    with pytest.raises(network.UnsafeUrlError):
        await tinyfish.fetch("http://example.org")


@pytest.mark.asyncio
async def test_tinyfish_is_immediate_search_fallback_not_healthy_primary(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "unit-only-private-key")
    monkeypatch.setenv("A0_SEARCH_BACKEND", "auto")
    calls = []

    async def local(query):
        calls.append("local")
        raise ConnectionRefusedError()

    async def remote(query, **kwargs):
        calls.append("tinyfish")
        return [{"title": "Actual", "url": "https://example.org", "content": "Snippet"}]

    async def never(query):
        pytest.fail("must try Tinyfish before DuckDuckGo")

    monkeypatch.setattr(searxng, "_searxng", local)
    monkeypatch.setattr(tinyfish, "search", remote)
    monkeypatch.setattr(searxng, "_duckduckgo", never)
    result = await searxng._search("query")
    assert (
        calls == ["local", "tinyfish"]
        and result["backend"] == "tinyfish"
        and result["fallback_attempted"]
    )

    async def healthy(query):
        return []

    monkeypatch.setattr(searxng, "_searxng", healthy)
    assert (await searxng._search("query"))["backend"] == "searxng"
    assert calls == ["local", "tinyfish"]


@pytest.mark.asyncio
async def test_document_fallback_precedes_retry_sleep_and_preserves_source(monkeypatch):
    uri = "https://example.org/docs"
    transport(monkeypatch, {"results": [{"url": uri, "text": "# Actual document"}]})
    calls = []

    def fail(*args, **kwargs):
        calls.append("native")
        raise ConnectionError("native unavailable")

    async def never_sleep(*args):
        pytest.fail("Tinyfish must run before retry backoff")

    monkeypatch.setattr(documents, "fetch_public_http_resource", fail)
    monkeypatch.setattr(documents.asyncio, "sleep", never_sleep)
    result = await documents.fetch_public_resource(uri, {"fetch_retries": 3})
    assert calls == ["native"] and result.text() == "# Actual document"
    assert result.mimetype == "text/markdown" and result.source_uri == uri


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        network.UnsafeUrlError("Blocked private URL"),
        ValueError("Remote document exceeds max size"),
        asyncio.CancelledError(),
    ],
)
async def test_fetch_refusals_and_cancellation_never_invoke_fallback(
    monkeypatch, failure
):
    monkeypatch.setenv("TINYFISH_API_KEY", "unit-only-private-key")

    def fail(*args, **kwargs):
        raise failure

    async def never(*args, **kwargs):
        pytest.fail("must not fall back")

    monkeypatch.setattr(documents, "fetch_public_http_resource", fail)
    monkeypatch.setattr(tinyfish, "fetch", never)
    with pytest.raises(type(failure)):
        await documents.fetch_public_resource("https://example.org/docs", {})


@pytest.mark.asyncio
async def test_native_success_and_intervention_never_invoke_fallback(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "unit-only-private-key")

    def healthy(*args, **kwargs):
        return SimpleNamespace(
            url="https://example.org",
            content=b"native",
            content_type="text/plain",
            encoding="utf-8",
        )

    async def never(*args, **kwargs):
        pytest.fail("must not fall back")

    monkeypatch.setattr(documents, "fetch_public_http_resource", healthy)
    monkeypatch.setattr(tinyfish, "fetch", never)
    assert (
        await documents.fetch_public_resource("https://example.org", {})
    ).content == b"native"
    calls = []

    async def interrupted():
        calls.append(True)
        if len(calls) == 2:
            raise RuntimeError("user intervention")

    with pytest.raises(RuntimeError, match="user intervention"):
        await documents.fetch_public_resource("https://example.org", {}, interrupted)


@pytest.mark.asyncio
async def test_failed_document_fallback_is_once_and_safe(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "unit-only-private-key")
    calls = []

    def fail(*args, **kwargs):
        calls.append("native")
        raise ConnectionError("native details")

    async def remote(*args, **kwargs):
        calls.append("tinyfish")
        raise tinyfish.TinyfishError("http_401")

    monkeypatch.setattr(documents, "fetch_public_http_resource", fail)
    monkeypatch.setattr(tinyfish, "fetch", remote)
    with pytest.raises(ValueError, match="Tinyfish http_401") as error:
        await documents.fetch_public_resource(
            "https://example.org", {"fetch_retries": 3}
        )
    assert calls == ["native", "tinyfish"] and "unit-only-private-key" not in str(
        error.value
    )
