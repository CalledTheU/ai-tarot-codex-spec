# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import pytest

from app.config import Settings


def test_model_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("LLM_MODEL", "Qwen3-0.6B")
    monkeypatch.setenv("LLM_API_KEY", "test-only-secret")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "512")

    settings = Settings()
    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_base_url == "http://127.0.0.1:8001/v1"
    assert settings.llm_model == "Qwen3-0.6B"
    assert settings.llm_api_key == "test-only-secret"
    assert "test-only-secret" not in repr(settings)
    assert settings.llm_timeout_seconds == 15
    assert settings.llm_max_output_tokens == 512


@pytest.mark.parametrize("name", ["LLM_TIMEOUT_SECONDS", "LLM_MAX_OUTPUT_TOKENS"])
@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_invalid_model_limits_are_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings()


def test_model_configuration_is_optional(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    assert settings.llm_model == ""
    assert settings.llm_timeout_seconds == 60
    assert settings.llm_max_output_tokens == 3000
