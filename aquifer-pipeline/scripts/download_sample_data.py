"""Download sample Aquifer content (the data behind well.bible / app.bible.well).

The well.bible file-manager is an offline-cache downloader over the Aquifer content API
(the `api-bn.aquifer.bible` backend, which the baked-in public web key authenticates against).
This script reproduces that flow headlessly: for a language, pick books and guides
(parent resources), search each (book x guide) pair for matching resources, then fetch
their text content and metadata and write one JSON file per resource plus a manifest.

Usage:
    uv run python scripts/download_sample_data.py --list-guides
    uv run python scripts/download_sample_data.py                        # English FIA guide, John
    uv run python scripts/download_sample_data.py --book JHN --book 1JN --guide 5 --guide 7
    uv run python scripts/download_sample_data.py --book JHN --guide FIA --max 50

Guides are parent resources (see --list-guides); pass them by id or by one of the built-in
aliases (FIA, FIAImages, ...). NB: not every guide covers every book, e.g. the FIA guide has
no resources for 1 John, whose content lives under Study Notes / Translation Notes / etc.

Auth: reads AQUIFER_API_KEY / AQUIFER_BASE_URL from the environment (or a .env file), falling
back to the public web key + api-bn base so this runs out of the box.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import os

DEFAULT_BASE_URL = "https://api-bn.aquifer.bible"
PUBLIC_WEB_API_KEY = "983741eb09ad4ad78b6eee25dfb8a83c"

# Guides == parent resources. These are global parentResourceId values (stable across
# languages); run --list-guides to see them all. Aliases are a convenience over the ids.
GUIDE_ALIASES = {
    "FIA": 1,
    "VideoBibleDictionary": 4,
    "UwTranslationWords": 7,
    "UwTranslationNotes": 11,
    "UwTranslationQuestions": 13,
    "FIAImages": 15,
    "FIAMaps": 16,
    "FIAKeyTerms": 17,
    "SilOpenTranslatorsNotes": 18,
}

# batch/content/text only serves text; passing a non-Text id 404s the WHOLE chunk.
TEXT_MEDIA_TYPE = "Text"
CONTENT_BATCH_SIZE = 10
METADATA_BATCH_SIZE = 100
SEARCH_PAGE_SIZE = 200
# Termination backstop: a filter the API silently ignores would otherwise page forever.
MAX_PAGES_PER_QUERY = 1000
REQUEST_DELAY = 0.1

log = logging.getLogger("aquifer")


class SearchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: int
    display_name: str | None = Field(None, alias="displayName")
    media_type: str | None = Field(None, alias="mediaType")
    parent_resource_id: int | None = Field(None, alias="parentResourceId")
    resource_type: str | None = Field(None, alias="resourceType")
    book_code: str | None = Field(None, alias="bookCode")


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def resolve_guide(value: str) -> int:
    if value in GUIDE_ALIASES:
        return GUIDE_ALIASES[value]
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"guide must be an id or one of {', '.join(GUIDE_ALIASES)}"
        ) from exc


async def resolve_bible(client: AquiferClient, value: str, language_code: str) -> int:
    if value.isdigit():
        return int(value)
    bibles = await client.bibles(language_code)
    for bib in bibles:
        if (bib.get("abbreviation") or "").lower() == value.lower():
            return bib["id"]
    raise SystemExit(
        f"unknown bible '{value}'; run --list-bibles (e.g. BSB) or pass a numeric id"
    )


class RateLimiter:
    """Bounded concurrency + a minimum spacing between request starts, so the client stays
    a polite (and correct) caller regardless of the configured concurrency."""

    def __init__(self, min_interval: float, concurrency: int) -> None:
        self._sem = asyncio.Semaphore(concurrency)
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._next_start = 0.0

    async def __aenter__(self) -> None:
        await self._sem.acquire()
        if self._min_interval:
            async with self._lock:
                now = time.monotonic()
                wait = self._next_start - now
                if wait > 0:
                    await asyncio.sleep(wait)
                self._next_start = max(now, self._next_start) + self._min_interval

    async def __aexit__(self, *_exc) -> None:
        self._sem.release()


class AquiferClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        delay: float = REQUEST_DELAY,
        concurrency: int = 1,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"api-key": api_key},
            timeout=60.0,
            transport=transport,
        )
        self._limiter = RateLimiter(delay, concurrency)

    async def __aenter__(self) -> AquiferClient:
        return self

    async def __aexit__(self, *_exc) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params=None) -> httpx.Response:
        async with self._limiter:
            return await self._client.get(path, params=params)

    async def _get_json(self, path: str, params=None) -> object:
        resp = await self._get(path, params)
        resp.raise_for_status()
        return resp.json()

    async def languages(self) -> list[dict]:
        return await self._get_json("/languages")

    async def parent_resources(self, language_id: int) -> list[dict]:
        return await self._get_json("/resources/parent-resources", {"languageId": language_id})

    async def bibles(self, language_code: str) -> list[dict]:
        return await self._get_json("/bibles", {"languageCode": language_code})

    async def bible_texts(self, bible_id: int, book_code: str) -> dict:
        return await self._get_json(
            f"/bibles/{bible_id}/texts", {"bookCode": book_code}
        )

    async def search(
        self,
        language_id: int,
        book_code: str,
        parent_resource_id: int,
        page_size: int,
        max_results: int | None,
    ) -> list[SearchResult]:
        # parentResourceId is the filter the API actually honors and is required (bookCode alone
        # 400s with "resourceTypes must not be empty"); resourceType/resourceTypes do not filter.
        found: list[SearchResult] = []
        offset = 0
        for _ in range(MAX_PAGES_PER_QUERY):
            page = await self._get_json(
                "/resources/search",
                [
                    ("languageId", language_id),
                    ("bookCode", book_code),
                    ("parentResourceId", parent_resource_id),
                    ("offset", offset),
                    ("limit", page_size),
                ],
            )
            if not isinstance(page, list):
                raise RuntimeError(f"search returned {type(page).__name__}, expected list: {page}")
            found.extend(SearchResult.model_validate(r) for r in page)
            offset += len(page)
            if len(page) < page_size:
                break
            if max_results is not None and len(found) >= max_results:
                break
        else:
            log.warning("hit MAX_PAGES_PER_QUERY for %s/guide %s", book_code, parent_resource_id)
        return found[:max_results] if max_results is not None else found

    async def batch_content(self, ids: list[int]) -> dict[int, object]:
        try:
            rows = await self._get_json(
                "/resources/batch/content/text", [("ids", i) for i in ids]
            )
            return {row["id"]: row.get("content") for row in rows}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            if len(ids) == 1:
                # A lone 404 means this id has no text content; record it as missing.
                return {ids[0]: None}
            # One contentless id 404s the whole chunk; split so its neighbours still land.
            log.debug("content batch 404 for %d ids; splitting", len(ids))
            mid = len(ids) // 2
            left = await self.batch_content(ids[:mid])
            right = await self.batch_content(ids[mid:])
            return {**left, **right}

    async def batch_metadata(self, ids: list[int]) -> dict[int, dict]:
        rows = await self._get_json("/resources/batch/metadata", [("ids", i) for i in ids])
        return {row["id"]: row for row in rows}


async def run_list_languages(client: AquiferClient) -> None:
    for lang in await client.languages():
        log.info("%4s  %s  %s", lang["id"], lang["iso6393Code"], lang["englishDisplay"])


async def run_list_guides(client: AquiferClient, language_id: int) -> None:
    for pr in await client.parent_resources(language_id):
        log.info(
            "%4s  %-12s  %s (%s)",
            pr["id"],
            pr["resourceType"],
            pr["displayName"],
            pr.get("resourceCountForLanguage", 0),
        )


async def run_list_bibles(client: AquiferClient, language_code: str) -> None:
    for bib in await client.bibles(language_code):
        log.info("%4s  %-8s  %s", bib["id"], bib.get("abbreviation"), bib.get("name"))


async def fetch_bible_texts(
    client: AquiferClient, bible_id: int, books: list[str], out_dir: Path
) -> None:
    # Actual scripture, distinct from the /resources/* study helps: /bibles/{id}/texts.
    for book in books:
        dest = out_dir / f"bible_{bible_id}_{book}.json"
        if dest.exists():
            continue
        data = await client.bible_texts(bible_id, book)
        verses = sum(len(ch.get("verses", [])) for ch in data.get("chapters", []))
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        abbrev = data.get("bibleAbbreviation", bible_id)
        log.info("  bible %s / %s: %d verses", abbrev, book, verses)


async def discover(
    client: AquiferClient,
    language_id: int,
    books: list[str],
    guides: list[int],
    page_size: int,
    max_results: int | None,
) -> dict[int, SearchResult]:
    resources: dict[int, SearchResult] = {}
    for book in books:
        for guide in guides:
            results = await client.search(language_id, book, guide, page_size, max_results)
            for r in results:
                r.book_code = book
                resources.setdefault(r.id, r)
            log.info("  %s / guide %s: %d resources", book, guide, len(results))
    return resources


async def fetch_and_write(
    client: AquiferClient, resources: dict[int, SearchResult], out_dir: Path
) -> list[dict]:
    pending = [rid for rid in resources if not (out_dir / f"{rid}.json").exists()]
    text_pending = [rid for rid in pending if resources[rid].media_type == TEXT_MEDIA_TYPE]
    log.info(
        "%d resources (%d on disk); fetching metadata for %d, text content for %d "
        "(non-text media URLs live in metadata)",
        len(resources),
        len(resources) - len(pending),
        len(pending),
        len(text_pending),
    )

    # Metadata covers every media type and is where image/audio CDN URLs live; text content
    # only exists for Text resources (batch/content/text 404s for the rest). Batches are
    # dispatched concurrently; the client's RateLimiter bounds in-flight requests and spaces
    # their starts, so throughput reaches the polite ceiling instead of stalling on latency.
    metadata: dict[int, dict] = {}
    for result in await asyncio.gather(
        *(client.batch_metadata(b) for b in chunked(pending, METADATA_BATCH_SIZE))
    ):
        metadata.update(result)

    content: dict[int, object] = {}
    for result in await asyncio.gather(
        *(client.batch_content(b) for b in chunked(text_pending, CONTENT_BATCH_SIZE))
    ):
        content.update(result)

    for rid in pending:
        record = {
            "id": rid,
            "search": resources[rid].model_dump(by_alias=True),
            "metadata": metadata.get(rid),
            "content": content.get(rid),
        }
        (out_dir / f"{rid}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    if pending:
        log.info("  wrote %d records", len(pending))

    return [
        {
            "id": r.id,
            "displayName": r.display_name,
            "bookCode": r.book_code,
            "resourceType": r.resource_type,
            "parentResourceId": r.parent_resource_id,
            "mediaType": r.media_type,
        }
        for r in resources.values()
    ]


async def download(args: argparse.Namespace) -> None:
    api_key = os.getenv("AQUIFER_API_KEY") or PUBLIC_WEB_API_KEY
    base_url = os.getenv("AQUIFER_BASE_URL") or DEFAULT_BASE_URL

    async with AquiferClient(
        base_url, api_key, delay=args.delay, concurrency=args.concurrency
    ) as client:
        if args.list_languages:
            return await run_list_languages(client)
        if args.list_guides:
            return await run_list_guides(client, args.language_id)
        if args.list_bibles:
            return await run_list_bibles(client, args.language_code)

        if args.all_guides:
            args.guide = [pr["id"] for pr in await client.parent_resources(args.language_id)]
            log.info("all-guides: searching %d parent resources", len(args.guide))

        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.bible:
            bible_id = await resolve_bible(client, args.bible, args.language_code)
            log.info("scripture: bible=%s books=%s", args.bible, args.book)
            await fetch_bible_texts(client, bible_id, args.book, out_dir)

        max_results = args.max if args.max > 0 else None
        log.info(
            "search %s | language=%s guides=%s books=%s max/query=%s",
            base_url,
            args.language_id,
            args.guide,
            args.book,
            max_results or "all",
        )

        resources = await discover(
            client, args.language_id, args.book, args.guide, args.page_size, max_results
        )
        if not resources:
            log.warning("No resources matched. Try --list-guides or different --book / --guide.")
            return

        manifest = await fetch_and_write(client, resources, out_dir)
        (out_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "baseUrl": base_url,
                    "languageId": args.language_id,
                    "guides": args.guide,
                    "books": args.book,
                    "count": len(manifest),
                    "resources": manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        log.info("Wrote %d resources + manifest.json to %s/", len(manifest), out_dir)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--language-id", type=int, default=1, help="Aquifer language id (1 = English)")
    p.add_argument(
        "--language-code", default="eng", help="ISO language code for /bibles (default eng)"
    )
    p.add_argument("--book", action="append", help="Book code, e.g. JHN (repeatable; default JHN)")
    p.add_argument(
        "--bible",
        help="Also download scripture text for --book from this Bible (id or abbreviation, "
        "e.g. BSB); see --list-bibles",
    )
    p.add_argument(
        "--guide",
        action="append",
        type=resolve_guide,
        help=f"Guide / parent resource, id or alias ({', '.join(GUIDE_ALIASES)}); "
        "repeatable; default FIA",
    )
    p.add_argument(
        "--page-size", type=int, default=SEARCH_PAGE_SIZE, help="Search results per page"
    )
    p.add_argument("--max", type=int, default=0, help="Cap resources per (book, guide); 0 = all")
    p.add_argument(
        "--delay", type=float, default=REQUEST_DELAY, help="Min seconds between requests"
    )
    p.add_argument("--concurrency", type=int, default=3, help="Max in-flight requests (default 3)")
    p.add_argument("--out", default="data/sample", help="Output directory")
    p.add_argument("--list-languages", action="store_true", help="Print languages and exit")
    p.add_argument("--list-guides", action="store_true", help="Print guides for --language-id")
    p.add_argument("--list-bibles", action="store_true", help="Print Bibles for --language-code")
    p.add_argument(
        "--all-guides",
        action="store_true",
        help="Search every parent resource for the language (all content types), ignoring --guide",
    )
    args = p.parse_args()
    if not args.book:
        args.book = ["JHN"]
    if not args.guide and not args.all_guides:
        args.guide = [GUIDE_ALIASES["FIA"]]
    return args


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(download(parse_args()))
