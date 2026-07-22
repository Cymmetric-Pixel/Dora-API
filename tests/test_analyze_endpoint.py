from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_GEMINI_RESPONSE = {
    "schemaVersion": "1.0",
    "type": "full_verse",
    "subType": None,
    "references": ["JHN.3.16.NIV"],
    "selection": {"text": None, "startOffset": None, "endOffset": None},
    "summary": "God's love is shown through giving his Son.",
    "data": {},
    "sources": [],
    "certainty": {"confidence": 0.95, "ambiguity": False, "alternativeInterpretations": []},
}


@pytest.mark.asyncio
async def test_analyze_dora_returns_raw_gemini_response(mock_db) -> None:
    with patch(
        "app.handlers.dora.gemini.generate_dora",
        new=AsyncMock(return_value=SAMPLE_GEMINI_RESPONSE),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/dora/analyze",
                json={
                    "references": ["JHN.3.16.NIV"],
                    "targetText": None,
                    "startOffset": None,
                    "endOffset": None,
                },
            )

    assert response.status_code == 200
    assert response.json() == SAMPLE_GEMINI_RESPONSE


@pytest.mark.asyncio
async def test_analyze_dora_returns_503_when_gemini_not_configured(mock_db) -> None:
    with (
        patch("app.handlers.dora.settings.gemini_api_key", None),
        patch("app.handlers.dora.settings.gemini_use_vertex", False),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/dora/analyze",
                json={"references": ["JHN.3.16.NIV"]},
            )

    assert response.status_code == 503
