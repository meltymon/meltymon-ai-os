import pytest

from meltymon_ai_os.config.settings import load_settings


def test_load_default_settings():
    settings = load_settings()

    assert settings.ollama.base_url == "http://127.0.0.1:11434"
    assert settings.ollama.timeout == 60.0
    assert settings.models.default == "gemma4:e4b"


def test_environment_override(monkeypatch):
    monkeypatch.setenv(
        "MELTYMON_OLLAMA_BASE_URL",
        "http://127.0.0.1:11435",
    )
    monkeypatch.setenv("MELTYMON_OLLAMA_TIMEOUT", "30")
    monkeypatch.setenv(
        "MELTYMON_DEFAULT_MODEL",
        "qwen3:8b",
    )

    settings = load_settings()

    assert settings.ollama.base_url == "http://127.0.0.1:11435"
    assert settings.ollama.timeout == 30.0
    assert settings.models.default == "qwen3:8b"


def test_invalid_timeout(monkeypatch):
    monkeypatch.setenv("MELTYMON_OLLAMA_TIMEOUT", "-1")

    with pytest.raises(ValueError):
        load_settings()
