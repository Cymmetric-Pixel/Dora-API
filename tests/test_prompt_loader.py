from app.services.prompt_loader import load_dora_prompt


def test_load_dora_prompt_returns_non_empty_text() -> None:
    prompt = load_dora_prompt()
    assert prompt.strip()
    assert "Biblical Context Engine" in prompt
