import os
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, Field, field_validator


class OllamaSettings(BaseModel):
    """Configuration for the Ollama backend."""

    base_url: str = "http://127.0.0.1:11434"
    timeout: float = Field(default=60.0, gt=0, le=600)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Invalid Ollama base URL")

        return value.rstrip("/")


class ModelSettings(BaseModel):
    """Default model configuration."""

    default: str = "gemma4:e4b"

    @field_validator("default")
    @classmethod
    def validate_default(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Default model must not be empty")

        return value.strip()


class AppSettings(BaseModel):
    """Application-wide configuration."""

    ollama: OllamaSettings = OllamaSettings()
    models: ModelSettings = ModelSettings()


def load_settings(
    config_path: Path | None = None,
) -> AppSettings:
    """Load configuration from YAML with environment overrides."""

    if config_path is None:
        config_path = Path(__file__).with_name("settings.yaml")

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    else:
        data = {}

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise TypeError("Configuration root must be a YAML mapping")

    data = dict(data)

    for section_name in ("ollama", "models"):
        if section_name not in data:
            data[section_name] = {}
            continue

        section = data[section_name]

        if not isinstance(section, dict):
            raise TypeError(
                f"Configuration section '{section_name}' must be a YAML mapping"
            )

        data[section_name] = dict(section)

    # Environment variables override YAML settings.
    if value := os.getenv("MELTYMON_OLLAMA_BASE_URL"):
        data["ollama"]["base_url"] = value

    if value := os.getenv("MELTYMON_OLLAMA_TIMEOUT"):
        data["ollama"]["timeout"] = value

    if value := os.getenv("MELTYMON_DEFAULT_MODEL"):
        data["models"]["default"] = value

    return AppSettings.model_validate(data)
