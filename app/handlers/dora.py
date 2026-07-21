"""Dora content endpoint."""
from typing import Annotated

from fastapi import Query

from app.models.dora import DoraItem, DoraResponse, Publisher

MOCK_DORAS: list[DoraItem] = [
    DoraItem(
        content_type="Maps",
        title="Haran to Canaan",
        text="",
        url="https://cdn.aquifer.bible/aquifer-content/resources/FIAMaps/c39-haran-to-canaan.png",
        media_type="image",
        publisher=Publisher(
            publisher_title="Open Bible Maps",
            publisher_url="https://example.com/publishers/open-bible-maps",
        ),
    ),
    DoraItem(
        content_type="Study Notes",
        title="Understanding the Passage",
        text="This passage emphasizes God's love demonstrated through Christ. The surrounding context clarifies who is speaking and to whom the promise applies.",
        url="https://example.com/study-notes/john-3-16",
        media_type="text",
        publisher=Publisher(
            publisher_title="Aquifer Study Notes",
            publisher_url="https://example.com/publishers/aquifer",
        ),
    ),
    DoraItem(
        content_type="Summary",
        title="Passage Summary",
        text="Richard is the dopest guy in the world",
        url=None,
        media_type="text",
        publisher=Publisher(
            publisher_title="Dora",
            publisher_url=None,
        ),
    ),
    DoraItem(
        content_type="Key Verse",
        title="John 3:16",
        text="For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
        url="https://example.com/verses/JHN.3.16",
        media_type="text",
        publisher=Publisher(
            publisher_title="Holy Bible, NIV",
            publisher_url="https://example.com/publishers/biblica",
        ),
    ),
    DoraItem(
        content_type="Commentary",
        title="Commentary on John 3:16",
        text="This verse summarizes the gospel: God's initiative in love, the gift of the Son, the call to believe, and the promise of eternal life. It stands at the heart of Jesus' conversation with Nicodemus about new birth and salvation.",
        url="https://example.com/commentary/john-3-16",
        media_type="text",
        publisher=Publisher(
            publisher_title="Trusted Biblical Commentary",
            publisher_url="https://example.com/publishers/commentary",
        ),
    ),
]


async def get_doras(
    references: Annotated[list[str] | None, Query()] = None,
    targetText: str | None = None,
    startOffset: int | None = None,
    endOffset: int | None = None,
) -> DoraResponse:
    """Return doras for the given Bible selection."""
    # TODO: resolve selection to real Aquifer / generated content
    return DoraResponse(data=MOCK_DORAS)
