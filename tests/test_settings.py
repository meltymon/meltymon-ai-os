from pathlib import Path

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


@pytest.mark.parametrize(
    ("yaml_content", "section"),
    [
        ("ollama: false\n", "ollama"),
        ("ollama: test\n", "ollama"),
        ("ollama: null\n", "ollama"),
        ("ollama: []\n", "ollama"),
        ("models: false\n", "models"),
        ("models: test\n", "models"),
        ("models: null\n", "models"),
        ("models: []\n", "models"),
    ],
)
def test_invalid_configuration_section(
    tmp_path: Path,
    yaml_content: str,
    section: str,
):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(
        TypeError,
        match=f"Configuration section '{section}'",
    ):
        load_settings(config_path)


def test_invalid_configuration_root(tmp_path: Path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("- item\n", encoding="utf-8")

    with pytest.raises(
        TypeError,
        match="Configuration root must be a YAML mapping",
    ):
        load_settings(config_path)


def test_empty_configuration_file_uses_defaults(tmp_path: Path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("", encoding="utf-8")

    settings = load_settings(config_path)

    assert settings.ollama.base_url == "http://127.0.0.1:11434"
    assert settings.ollama.timeout == 60.0
    assert settings.models.default == "gemma4:e4b"
