"""Load the Dora system prompt from disk."""

from functools import lru_cache
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "dora_prompt.md"


@lru_cache(maxsize=1)
def load_dora_prompt() -> str:
    """Return the Dora system prompt text."""
    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(f"Dora prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")
