"""Dora content endpoint."""
from typing import Annotated

from fastapi import Query

from app.models.dora import DoraResponse


async def get_doras(
    anchors: Annotated[list[str], Query(min_length=1)],
) -> DoraResponse:
    """Return doras for the given anchor terms."""
    # TODO: resolve anchors to dora content
    return DoraResponse(data=[])
