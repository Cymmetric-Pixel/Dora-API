"""Dora response models.

A "dora" is a unit of extra-biblical content tied to highlighted Bible text.
Doras are polymorphic on `dora_type`, modeled as a discriminated union so each
variant declares its own required/optional fields (rendered as oneOf in OpenAPI).
"""
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class DoraBase(BaseModel):
    """Fields shared by every dora."""

    summary: str


class PersonDora(DoraBase):
    dora_type: Literal["person"] = "person"
    timeline: str | None = None
    maps: list[str] | None = None
    audio: str | None = None


class PlaceDora(DoraBase):
    dora_type: Literal["place"] = "place"
    maps: list[str]


class ThingDora(DoraBase):
    dora_type: Literal["thing"] = "thing"
    importance: str
    hebrew_summary: str | None = None
    greek_summary: str | None = None


class VerseDora(DoraBase):
    dora_type: Literal["verse"] = "verse"
    audio: str


Dora = Annotated[
    PersonDora | PlaceDora | ThingDora | VerseDora,
    Field(discriminator="dora_type"),
]


class DoraResponse(BaseModel):
    data: list[Dora]
