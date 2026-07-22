import os
from collections.abc import Generator
from unittest.mock import patch

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
)
os.environ.setdefault("GEMINI_USE_VERTEX", "false")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


@pytest.fixture
def mock_db() -> Generator[None]:
    with patch("app.database.client.init_db"), patch("app.database.client.close_db"):
        yield
