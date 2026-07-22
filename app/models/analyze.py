"""Request model for the Gemini analyze endpoint."""

from pydantic import BaseModel, Field


class DoraAnalyzeRequest(BaseModel):
    references: list[str] = Field(min_length=1)
    targetText: str | None = None
    startOffset: int | None = None
    endOffset: int | None = None
