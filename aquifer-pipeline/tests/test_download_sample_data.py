"""Offline tests for the two branch-heavy bits of the Aquifer sample downloader:
search pagination/termination and the content-batch 404 split. All requests go through
an httpx.MockTransport, so no network is touched."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

_spec = importlib.util.spec_from_file_location(
    "download_sample_data",
    Path(__file__).resolve().parents[1] / "scripts" / "download_sample_data.py",
)
dsd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dsd)


def make_client(handler) -> dsd.AquiferClient:
    return dsd.AquiferClient(
        "https://test", "key", delay=0, transport=httpx.MockTransport(handler)
    )


async def test_search_stops_on_short_page():
    pages = [
        [{"id": i} for i in range(25)],
        [{"id": i} for i in range(25, 40)],  # short page ends it
    ]
    calls: list[int] = []

    def handler(request):
        offset = int(request.url.params["offset"])
        calls.append(offset)
        idx = offset // 25
        return httpx.Response(200, json=pages[idx] if idx < len(pages) else [])

    async with make_client(handler) as client:
        found = await client.search(1, "JHN", 1, page_size=25, max_results=None)

    assert [r.id for r in found] == list(range(40))
    assert calls == [0, 25]  # stopped after the short page, no extra request


async def test_search_stops_on_empty_page_after_exact_multiple():
    def handler(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json=[{"id": i} for i in range(offset, offset + 25)]
                              if offset == 0 else [])

    async with make_client(handler) as client:
        found = await client.search(1, "JHN", 1, page_size=25, max_results=None)

    assert [r.id for r in found] == list(range(25))


async def test_search_raises_on_error_object():
    def handler(request):
        return httpx.Response(200, json={"statusCode": 400, "message": "bad", "errors": {}})

    async with make_client(handler) as client:
        with pytest.raises(RuntimeError, match="expected list"):
            await client.search(1, "JHN", 1, page_size=25, max_results=None)


async def test_search_respects_max_results():
    def handler(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json=[{"id": i} for i in range(offset, offset + 25)])

    async with make_client(handler) as client:
        found = await client.search(1, "JHN", 1, page_size=25, max_results=10)

    assert len(found) == 10


async def test_max_pages_guard_terminates(monkeypatch):
    monkeypatch.setattr(dsd, "MAX_PAGES_PER_QUERY", 3)
    calls: list[int] = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=[{"id": 1} for _ in range(25)])  # never short

    async with make_client(handler) as client:
        await client.search(1, "JHN", 1, page_size=25, max_results=None)

    assert len(calls) == 3  # capped, did not loop forever


async def test_batch_content_isolates_the_404_id():
    # id 999 has no text content -> 404 alone, and 404s any chunk it's in.
    def handler(request):
        ids = [int(v) for v in request.url.params.get_list("ids")]
        if 999 in ids:
            return httpx.Response(404)
        return httpx.Response(200, json=[{"id": i, "content": [{"step": 1}]} for i in ids])

    async with make_client(handler) as client:
        result = await client.batch_content([1, 999, 2])

    assert result[1] == [{"step": 1}]
    assert result[2] == [{"step": 1}]
    assert result[999] is None  # isolated, recorded as missing, did not sink the batch


async def test_batch_content_reraises_non_404():
    def handler(request):
        return httpx.Response(500)

    async with make_client(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.batch_content([1, 2])
