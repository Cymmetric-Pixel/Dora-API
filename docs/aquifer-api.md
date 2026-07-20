# Aquifer Bible API — Endpoint Reference

Open-licensed, multilingual Bible resources for translation apps. For a task-focused summary of how Dora uses this API (the highlight → passage → content flow), see [`aquifer-integration.md`](./aquifer-integration.md).

- **Base URL:** `https://api.aquifer.bible`
- **OpenAPI spec:** `https://api.aquifer.bible/swagger/v1/swagger.json`
- **Auth:** API key required (request at https://www.aquifer.bible/apiaccess)
- **Format:** JSON over REST, all `GET`
- **Pagination:** list endpoints share `{ totalItemCount, returnedItemCount, offset, ... }`
- **Errors:** `400` (Bad Request) and `404` (Not Found) return `application/problem+json`: `{ statusCode: int, message: str, errors: object }`. Per-endpoint codes noted below.

> Verified field-by-field (paths, params, 200/400/404 bodies) against the raw OpenAPI spec (`aquifer-swagger.json`, OpenAPI 3.0.0, API v1.0.0) on 2026-07-20. Covers all 19 GET operations.

---

## Resources

### `GET /resources/search`  (`200`, `400`)
Full-text / scripture-scoped search across resources.

**Query:** `query` (min 3 chars; matches resource **names only**, not content body), `bookCode` (USFM), `startChapter`/`endChapter`, `startVerse`/`endVerse`, `languageId`|`languageCode` (ISO 639-3, e.g. `eng`), `resourceType`, `resourceCollectionCode`, `limit` (max 100, default 10), `offset` (default 0).
**Constraints:** one of `languageId`/`languageCode` is required; `query` optional if `bookCode`/`resourceType`/`resourceCollectionCode` given; `resourceType` and `resourceCollectionCode` are mutually exclusive; chapter/verse bounds must be paired (a start requires its matching end).

```jsonc
{ "totalItemCount": int, "returnedItemCount": int, "offset": int,
  "items": [ {
    "id": int, "name": str, "localizedName": str,
    "reviewLevel": "None|Community|Professional|Ai",
    "mediaType": "None|Text|Audio|Video|Image",
    "languageCode": str,
    "grouping": { "type": "None|Guide|Dictionary|StudyNotes|Images|Videos",
                  "name": str, "collectionTitle": str, "collectionCode": str } } ] }
```

### `GET /resources/{contentId}`  (`200`, `400`, `404`)
### `GET /resources/{contentId}/by-language/{languageCode}`  (`200`, `400`, `404`)
Single resource. `content` is polymorphic — pin `contentTextType` for a stable shape.

**Query:** `contentTextType` = `None|Json|Html|Markdown` (default `None`). `by-language` takes the same param plus the `languageCode` path segment.

```jsonc
{ "id": int, "referenceId": int, "name": str, "localizedName": str,
  "reviewLevel": "None|Community|Professional|Ai",
  "content": object|string,
  "grouping": { "type": "None|Guide|Dictionary|StudyNotes|Images|Videos",
                "name": str, "mediaType": str, "licenseInfo": {...} },
  "language": { "id": int, "code": str, "displayName": str,
                "scriptDirection": "None|LTR|RTL" } }
```

### `GET /resources/{contentId}/associations`  (`200`)
Passage references and related-resource links for a resource. Path param `contentId` only.

```jsonc
{ "passageAssociations": [ { "startBookCode": str, "startChapter": int, "startVerse": int,
                             "endBookCode": str, "endChapter": int, "endVerse": int } ],
  "resourceAssociations": [ { "contentId": int, "displayName": str, "referenceId": int } ] }
```

### `GET /resources/updates`  (`200`, `400`)
Change feed for incremental sync (poll instead of full re-pull).

**Query:** `startTimestamp` (UTC date-time, e.g. `07/20/2024`; required unless the deprecated `timestamp` is passed), `endTimestamp` (UTC date-time; defaults to now), `languageId`, `languageCode`, `resourceCollectionCode`, `limit` (default 1000), `offset` (default 0), `timestamp` (**deprecated** — use `startTimestamp`).

```jsonc
{ "returnedItemCount": int, "totalItemCount": int, "offset": int,
  "items": [ { "updateType": "New|Updated", "languageId": int, "languageCode": str,
               "resourceId": int, "timestamp": str } ] }
```

### `GET /resources/types`  (`200`)
Resource types and their collections. No params.

```jsonc
[ { "type": str,
    "collections": [ { "code": str, "title": str, "licenseInformation": {...} } ] } ]
```

### `GET /resources/{contentId}/available-languages`  (`200`, `404`)
Languages a given resource is available in. Path param `contentId` only.

```jsonc
[ { "contentId": int, "contentDisplayName": str, "languageId": int,
    "languageDisplayName": str, "languageEnglishDisplayName": str, "languageCode": str } ]
```

### `GET /resources/collections`  (`200`, `400`)
### `GET /resources/collections/{code}`  (`200`, `400`, `404`)
Collection catalog; the `{code}` detail adds license + per-language availability.

**Query (list):** `resourceType`, `limit`, `offset`.
**Query (detail):** `languageIds`, `languageCodes` (filter the `availableLanguages` output).

```jsonc
// list — resourceType enum: None|Guide|Dictionary|StudyNotes|Images|Videos
[ { "code": str, "displayName": str, "shortName": str, "resourceType": str,
    "sliCategory": str?, "sliLevel": int? } ]
// detail — adds licenseInfo + per-language availability
{ "code": str, "displayName": str, "shortName": str, "resourceType": str,
  "sliCategory": str?, "sliLevel": int?, "licenseInfo": {...},
  "availableLanguages": [ { "languageId": int, "languageCode": str,
                            "displayName": str, "resourceItemCount": int } ] }
```

---

## Languages

### `GET /languages`  (`200`)
All supported languages. No params.

```jsonc
[ { "id": int, "code": str, "englishDisplay": str,
    "localizedDisplay": str, "scriptDirection": str } ]
```

### `GET /languages/available-resources`  (`200`, `400`)
Resource counts by type, per language, **scoped to a passage**.

**Query:** `bookCode` (**required**, USFM), `startChapter`/`endChapter`, `startVerse`/`endVerse` (bounds must be paired), `languageCodes`.

```jsonc
[ { "languageId": int, "languageCode": str,
    "resourceCounts": [ { "type": str, "count": int } ] } ]
```

---

## Bibles

### `GET /bibles`  (`200`, `400`)
Available Bible translations.

**Query:** `languageId`, `languageCode`, `isLanguageDefault` (bool), `hasAudio` (bool), `hasGreekAlignment` (bool) — all optional filters.

```jsonc
[ { "id": int, "name": str, "abbreviation": str, "languageId": int,
    "isLanguageDefault": bool, "hasAudio": bool, "hasGreekAlignment": bool,
    "licenseInfo": {...} } ]
```

### `GET /bibles/books`  (`200`)
Canonical book list. No params.

```jsonc
[ { "name": str, "code": str } ]   // code = USFM
```

### `GET /bibles/{bibleId}/texts`  (`200`, `400`, `404`)
Verse text for a passage, optional audio.

**Query:** `bookCode` (required, USFM), `startChapter` (1), `startVerse` (0), `endChapter` (999), `endVerse` (999), `shouldReturnAudioData` (false).

```jsonc
{ "bibleId": int, "bibleName": str, "bibleAbbreviation": str,
  "bookName": str, "bookCode": str,
  "chapters": [ {
    "number": int,
    "audio": { "webm": { "url": str, "size": int }, "mp3": { "url": str, "size": int } },
    "verses": [ { "number": int, "text": str,
                  "audioTimestamp": { "start": number, "end": number } } ] } ] }
```

### `GET /bibles/{bibleId}/alignments/greek`  (`200`, `400`, `404`)
Word-by-word alignment of a translation to the Greek (lemma, Strong's, senses).

**Query:** `bookCode` (required), `startChapter`/`endChapter` (1/999), `startVerse`/`endVerse` (0/999), `startWord`/`endWord` (1/999), `shouldReturnSenseData` (false).

```jsonc
{ "bibleId": int, "bibleName": str, "bibleAbbreviation": str,
  "greekBibleAbbreviation": str, "bookName": str, "bookCode": str,
  "chapters": [ { "number": int, "verses": [ { "number": int,
    "words": [ { "number": int, "word": str, "nextWordIsInGroup": bool,
      "greekWords": [ { "word": str, "grammarType": str, "usageCode": str,
                        "lemma": str, "strongsNumber": str,
                        "senses": [ { "glosses": [str], "definition": str } ] } ] } ] } ] } ] }
```

---

## Client SDKs

### `GET /clients/{cs|java|py|ts}`  (`200`)
Download generated client libraries — C#, Java, Python, TypeScript. No params.
