
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelMetadata(BaseModel):
    """Normalized metadata describing an AI model."""

    model_config = ConfigDict(extra="allow")

    name: str
    backend: str = "unknown"

    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None

    size_bytes: int | None = Field(default=None, ge=0)
    modified_at: datetime | None = None
    digest: str | None = None

    context_length: int | None = Field(default=None, gt=0)
    capabilities: list[str] = Field(default_factory=list)

    details: dict[str, Any] = Field(default_factory=dict)
    model_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def supports_vision(self) -> bool:
        return "vision" in self.capabilities

    @property
    def supports_tools(self) -> bool:
        return "tools" in self.capabilities

    @property
    def supports_thinking(self) -> bool:
        return "thinking" in self.capabilities
