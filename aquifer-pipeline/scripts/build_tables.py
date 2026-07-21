"""Transform a downloaded sample directory into the two consumable tables.

    uv run python scripts/build_tables.py data/sample/1john

Reads the raw resource records written by download_sample_data.py plus the references in
reference/ (versification + guides) and emits, under <dir>/flat/:

    content.jsonl   one row per resource (PK content_id)
    keyword.jsonl   mention index: (keyword, content_id), many rows -> one content

Scripture (bible_*.json) is intentionally ignored. keyword rows come from three sources,
deduped on (keyword, content_id):
  - self-subject : a passage resource's own verses (ranges exploded per verse via the
                   versification, cross-chapter splits included); a term's own headword
  - in-body term : resourceReference marks in the body
  - in-body verse: bibleReference marks in the body (cross-book), exploded per verse
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REFERENCE = Path("reference")
TEXT, IMAGE, AUDIO, VIDEO = "Text", "Image", "Audio", "Video"
AUDIO_URL_PREFERENCE = ("mp3", "webm")
# Reference tails span several dialects seen in the raw displayNames: "1:1"; same-chapter
# "1:1-4" / "1:1–4"; cross-chapter as endchapter.endverse "1:1-2.25" or endchapter:endverse
# "1:1–2:25"; plus an optional " (#N)" step suffix ("John 1:4 (#2)"). Anchored to the tail
# (allowing that suffix) so the leading book name is ignored.
RANGE_RE = re.compile(r"(\d+):(\d+)(?:[-–—](?:(\d+)[:.])?(\d+))?(?:\s*\(#\d+\))?\s*$")

versification = json.loads((REFERENCE / "versification.json").read_text())
guides = json.loads((REFERENCE / "guides.json").read_text())
num_to_code = {b["book_number"]: code for code, b in versification.items()}

# Parent resources whose entries describe a whole book rather than a passage. Their displayName
# is a book/theme name that no verse parser can match, so map them to every verse of their book,
# making any verse lookup surface the book's intro / summary / themes. (8 Book Intros Tyndale,
# 9 Intro Summaries Tyndale, 19 Book Intros Biblica, 20 Themes Tyndale; 21 Profiles is
# character-scoped and intentionally excluded.)
WHOLE_BOOK_GUIDES = {8, 9, 19, 20}


def verses_in(book: str, sc: int, sv: int, ec: int, ev: int) -> list[str]:
    book_ref = versification.get(book)
    if book_ref is None:
        return []
    out: list[str] = []
    for chapter in range(sc, ec + 1):
        chapter_max = book_ref["chapters"].get(str(chapter))
        if chapter_max is None:
            continue
        lo = sv if chapter == sc else 1
        hi = min(ev, chapter_max) if chapter == ec else chapter_max
        out.extend(f"{book}.{chapter}.{v}" for v in range(lo, hi + 1))
    return out


def all_book_verses(book: str) -> list[str]:
    ref = versification.get(book)
    if not ref or not ref["chapters"]:
        return []
    last_ch = max(int(c) for c in ref["chapters"])
    return verses_in(book, 1, 1, last_ch, ref["chapters"][str(last_ch)])


def passage_verses(book: str, display_name: str) -> list[str]:
    m = RANGE_RE.search(display_name)
    if not m:
        return []
    sc, sv = int(m.group(1)), int(m.group(2))
    ec = int(m.group(3)) if m.group(3) else sc
    ev = int(m.group(4)) if m.group(4) else sv
    return verses_in(book, sc, sv, ec, ev)


def decode_verse_id(v: int) -> tuple[int, int, int]:
    s = str(v)
    return int(s[-9:-6]), int(s[-6:-3]), int(s[-3:])  # book_number, chapter, verse


def collect_marks(node: object, terms: list[str], refs: list[tuple[int, int]]) -> None:
    if isinstance(node, dict):
        for mark in node.get("marks", []) or []:
            if mark.get("type") == "resourceReference":
                text = (node.get("text") or "").strip().lower()
                if text:
                    terms.append(text)
            elif mark.get("type") == "bibleReference":
                for v in mark.get("attrs", {}).get("verses", []):
                    refs.append((v.get("startVerse"), v.get("endVerse")))
        for child in node.get("content", []) or []:
            collect_marks(child, terms, refs)
    elif isinstance(node, list):
        for n in node:
            collect_marks(n, terms, refs)


def node_text(node: object) -> str:
    parts: list[str] = []

    def walk(n: object) -> None:
        if isinstance(n, dict):
            if n.get("type") == "text" and "text" in n:
                parts.append(n["text"])
            for child in n.get("content", []) or []:
                walk(child)
        elif isinstance(n, list):
            for x in n:
                walk(x)

    walk(node)
    return "".join(parts)


def flatten_text(record: dict) -> str:
    return " ".join(node_text(step.get("tiptap")) for step in record.get("content") or [])


def first_heading(node: object) -> object | None:
    if isinstance(node, dict):
        if node.get("type") == "heading":
            return node
        for child in node.get("content", []) or []:
            found = first_heading(child)
            if found is not None:
                return found
    elif isinstance(node, list):
        for n in node:
            found = first_heading(n)
            if found is not None:
                return found
    return None


def term_forms(record: dict, fallback: str) -> list[str]:
    # A term entry's first heading is a comma-separated list of its synonyms/word-forms
    # (e.g. "testimony, testify, witness, eyewitness, evidence") — each is its own keyword.
    for step in record.get("content") or []:
        heading = first_heading(step.get("tiptap"))
        if heading is not None:
            forms = [f.strip().lower() for f in node_text(heading).split(",") if f.strip()]
            if forms:
                return forms
    return [fallback.strip().lower()] if fallback.strip() else []


def content_url(record: dict, media: str) -> str | None:
    inner = (record.get("metadata") or {}).get("metadata") or {}
    if media in (IMAGE, VIDEO):
        return inner.get("url")
    if media == AUDIO:
        for variant in AUDIO_URL_PREFERENCE:
            if isinstance(inner.get(variant), dict) and inner[variant].get("url"):
                return inner[variant]["url"]
    return None


def content_row(record: dict) -> dict:
    s = record.get("search", {})
    media = s.get("mediaType")
    guide = guides.get(str(s.get("parentResourceId")), {})
    return {
        "content_id": str(record["id"]),
        "type": (media or "").lower(),
        "category": guide.get("name"),
        "title": s.get("displayName"),
        "body": flatten_text(record) if media == TEXT else None,
        "url": content_url(record, media),
    }


def keyword_rows(record: dict) -> set[str]:
    s = record.get("search", {})
    book = s.get("bookCode")
    display_name = s.get("displayName") or ""
    keywords: set[str] = set()

    self_verses = passage_verses(book, display_name)
    if self_verses:
        keywords.update(self_verses)
    else:
        keywords.update(term_forms(record, display_name))

    terms: list[str] = []
    refs: list[tuple[int, int]] = []
    for step in record.get("content") or []:
        collect_marks(step.get("tiptap"), terms, refs)
    keywords.update(terms)
    for start, end in refs:
        bn, sc, sv = decode_verse_id(start)
        _, ec, ev = decode_verse_id(end)
        code = num_to_code.get(bn)
        if code:
            keywords.update(verses_in(code, sc, sv, ec, ev))

    if s.get("parentResourceId") in WHOLE_BOOK_GUIDES:
        keywords.update(all_book_verses(book))
    return {k for k in keywords if k}


def build(out_dir: Path) -> tuple[int, int]:
    flat_dir = out_dir / "flat"
    flat_dir.mkdir(exist_ok=True)
    content: list[dict] = []
    keyword_pairs: set[tuple[str, str]] = set()

    for path in sorted(out_dir.glob("*.json")):
        if path.name == "manifest.json" or path.name.startswith("bible_"):
            continue
        record = json.loads(path.read_text())
        content.append(content_row(record))
        cid = str(record["id"])
        for kw in keyword_rows(record):
            keyword_pairs.add((kw, cid))

    with (flat_dir / "content.jsonl").open("w") as fh:
        for row in content:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (flat_dir / "keyword.jsonl").open("w") as fh:
        for kw, cid in sorted(keyword_pairs):
            fh.write(json.dumps({"keyword": kw, "content_id": cid}, ensure_ascii=False) + "\n")
    return len(content), len(keyword_pairs)


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sample")
    if not out_dir.is_dir():
        print(f"not a directory: {out_dir}")
        return 1
    n_content, n_keyword = build(out_dir)
    print(f"content.jsonl: {n_content} rows")
    print(f"keyword.jsonl: {n_keyword} rows")
    print(f"wrote to {out_dir}/flat/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
