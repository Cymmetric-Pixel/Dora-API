"""Dora request/response models.

A "dora" is a unit of extra-biblical content tied to highlighted Bible text.
"""

from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal[
    "Bible Dictionary",
    "Images",
    "Key Terms",
    "Maps",
    "Open Bible Stories",
    "Open Translator's Notes",
    "Study Notes",
    "Study Notes - Book Intros",
    "Study Notes - Book Intro Summaries",
    "Study Notes - Profiles",
    "Study Notes - Themes",
    "Translation Guide",
    "Translation Notes",
    "Translation Questions",
    "Translation Words",
    "Videos",
    "Plan",
    "Summary",
    "Key Verse",
    "Commentary",
]

MediaType = Literal["none", "text", "audio", "video", "image"]


class DoraRequest(BaseModel):
    """Incoming highlight selection used to resolve related doras."""

    # camelCase mirrors the frontend highlight-selection JSON payload.
    references: list[str] = Field(default_factory=list)
    targetText: str | None = None  # noqa: N815
    startOffset: int | None = None  # noqa: N815
    endOffset: int | None = None  # noqa: N815


class Publisher(BaseModel):
    publisher_title: str
    publisher_url: str | None = None


class DoraItem(BaseModel):
    """A single piece of related content for a Bible selection."""

    content_type: ContentType
    title: str
    text: str | None = None
    url: str | None = None
    media_type: MediaType | None = None
    publisher: Publisher | None = None


class DoraResponse(BaseModel):
    data: list[DoraItem]
