# Aquifer API

Reference for integrating the [Aquifer Bible API](https://api.aquifer.bible) into Dora. Aquifer provides openly-licensed, multilingual, multimodal biblical resources (study notes, dictionaries, images, key terms, Bible text, Greek alignment) keyed by scripture passage.

The client-facing API (AquiferDB API) is the same upstream database used by the [Bible Well app](https://well.bible). It does **not** read the [BibleAquifer GitHub repos](https://github.com/BibleAquifer) directly.

- **Base URL:** `https://api.aquifer.bible`
- **Swagger / OpenAPI:** https://api.aquifer.bible/docs/index.html?url=/swagger/v1/swagger.json (requires a key)
- **Python client:** https://github.com/BibleAquifer/aquifer-api-client · [demo](https://github.com/BibleAquifer/aquifer-api-client-demo)

## Authentication

Every request sends the key in an `api-key` header:

```
api-key: <your-key>
```

Request a key at https://www.aquifer.bible/apiaccess (emailed to you). In Dora it's configured via `AQUIFER_API_KEY` / `AQUIFER_BASE_URL` (see `.env.example`).

## Core flow for Dora

Highlighted text in the Bible app → scripture passage → related Aquifer resources → resource content.

1. Resolve the highlight to a passage: USFM `bookCode` + chapter/verse range.
2. `GET /resources/search` filtered by that passage (and `languageCode`) → list of matching resources with their `id`.
3. `GET /resources/{contentId}` → full content (HTML) for a chosen resource.

### 1. Search resources by passage — `GET /resources/search`

Returns `{ totalItemCount, items[] }`. Max **100** items per call; paginate with `offset`.

| Param | Type | Notes |
|---|---|---|
| `query` | string | Keyword search (min 3 chars). Optional. |
| `bookCode` | string | USFM book code, e.g. `GEN`, `RUT`, `MAT`. |
| `startChapter` / `endChapter` | int | Chapter range. |
| `startVerse` / `endVerse` | int | Verse range. |
| `languageCode` | string | ISO 639-3, e.g. `eng`. |
| `languageId` | int | Alternative to `languageCode`. |
| `resourceType` | string | Filter by type (see `GET /resources/types`). |
| `resourceCollectionCode` | string | Filter by collection. |
| `limit` | int | Default 10, max 100. |
| `offset` | int | Pagination offset. |

Example — resources for Ruth 2:1 in English:

```
GET /resources/search?bookCode=RUT&startChapter=2&endChapter=2&startVerse=1&endVerse=1&languageCode=eng&limit=100
api-key: <your-key>
```

### 2. Fetch a resource — `GET /resources/{contentId}`

Returns a single resource including `name` and `content`.

| Param | Type | Notes |
|---|---|---|
| `contentTextType` | string | Content format, default `Html`. |

Language variant: `GET /resources/{contentId}/by-language/{languageCode}` (404 if no version exists for that language).

## Full endpoint reference

| Endpoint | Purpose |
|---|---|
| `GET /languages` | Supported languages. |
| `GET /languages/available-resources` | Languages with resources for a passage. |
| `GET /bibles` | Available Bibles. |
| `GET /bibles/books` | All Bible books. |
| `GET /bibles/{bibleId}/books` | Books in a Bible. |
| `GET /bibles/{bibleId}/texts` | Bible text (book or passage range). |
| `GET /bibles/{bibleId}/alignments/greek` | Greek word alignment. |
| `GET /resources/types` | Resource type groups. |
| `GET /resources/collections` | Resource collections. |
| `GET /resources/collections/{code}` | A single collection. |
| `GET /resources/search` | **Search resources by passage / keyword / type / collection.** |
| `GET /resources/{contentId}` | **Full content for one resource.** |
| `GET /resources/{contentId}/by-language/{languageCode}` | Resource in a specific language. |
| `GET /resources/{contentId}/available-languages` | Languages a resource is available in. |
| `GET /resources/{contentId}/associations` | Related/associated resources. |
| `GET /resources/updates` | Changed resources since a timestamp (sync; max 1000/call). |

## Notes

- Book codes are [USFM](https://ubsicap.github.io/usfm/) three-letter codes (`GEN`, `PSA`, `MAT`, `REV`).
- Language codes are ISO 639-3 (`eng`, `fra`, `arb`, `spa`).
- The AquiferDB API is planned to be superseded by an API + MCP server over the GitHub repositories; treat endpoint shapes as current-not-permanent and verify against the Swagger.
