"""Gemini integration for Dora analyze requests."""

import json
import re
from typing import Any

import google.auth
from google import genai
from google.genai import types

from app.config import settings
from app.models.analyze import DoraAnalyzeRequest
from app.services.prompt_loader import load_dora_prompt


class GeminiServiceError(Exception):
    """Raised when Gemini generation or parsing fails."""


class GeminiNotConfiguredError(GeminiServiceError):
    """Raised when Gemini credentials are missing."""


_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    return _FENCE_PATTERN.sub("", text.strip())


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_markdown_fences(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise GeminiServiceError("Gemini response must be a JSON object")
    return parsed


def _create_client() -> genai.Client:
    if settings.gemini_api_key:
        return genai.Client(api_key=settings.gemini_api_key)

    if not settings.gemini_use_vertex:
        raise GeminiNotConfiguredError(
            "Gemini is not configured. Set GEMINI_API_KEY or enable GEMINI_USE_VERTEX."
        )

    project = settings.gemini_project
    if not project:
        _, project = google.auth.default()

    if not project:
        raise GeminiNotConfiguredError(
            "No GCP project found. Set GEMINI_PROJECT or run "
            "gcloud auth application-default login."
        )

    return genai.Client(
        vertexai=True,
        project=project,
        location=settings.gemini_location,
    )


async def generate_dora(request: DoraAnalyzeRequest) -> dict[str, Any]:
    """Call Gemini with the Dora prompt and return parsed JSON."""
    client = _create_client()
    config = types.GenerateContentConfig(
        system_instruction=load_dora_prompt(),
        temperature=0.2,
        response_mime_type="application/json",
    )
    user_content = json.dumps(request.model_dump())

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=config,
        )
    except GeminiNotConfiguredError:
        raise
    except Exception as exc:
        raise GeminiServiceError("Gemini request failed") from exc

    text = response.text
    if not text:
        raise GeminiServiceError("Gemini returned an empty response")

    return _parse_json_response(text)
