"""Immutable execution context for MELTYMON AI OS agents."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import uuid4


def _validate_identifier(value: str, field_name: str) -> str:
    """Validate and normalize an identifier."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} must not be empty.")

    return value


def _freeze(value: Any, path: str = "data") -> Any:
    """Recursively convert supported values into immutable structures."""

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain a finite number.")
        return value

    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string mapping key.")

            frozen[key] = _freeze(item, f"{path}.{key}")

        return MappingProxyType(frozen)

    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze(item, f"{path}[{index}]") for index, item in enumerate(value)
        )

    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item, f"{path}[]") for item in value)

    raise TypeError(
        f"{path} contains an unsupported value type: {type(value).__name__}."
    )


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Immutable context passed to an agent during execution.

    The context carries identity, input data, metadata and correlation
    information. It does not grant permissions or approve operations.
    """

    agent_id: str
    input_data: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate and freeze all context fields."""

        object.__setattr__(
            self,
            "agent_id",
            _validate_identifier(self.agent_id, "agent_id"),
        )

        object.__setattr__(
            self,
            "correlation_id",
            _validate_identifier(
                self.correlation_id,
                "correlation_id",
            ),
        )

        if not isinstance(self.input_data, Mapping):
            raise TypeError("input_data must be a mapping.")

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")

        object.__setattr__(
            self,
            "input_data",
            _freeze(self.input_data, "input_data"),
        )

        object.__setattr__(
            self,
            "metadata",
            _freeze(self.metadata, "metadata"),
        )

        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime.")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")

        object.__setattr__(
            self,
            "created_at",
            self.created_at.astimezone(UTC),
        )

    def get_input(self, key: str, default: Any = None) -> Any:
        """Return an input value or a default."""
        return self.input_data.get(key, default)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Return a metadata value or a default."""
        return self.metadata.get(key, default)

    def has_input(self, key: str) -> bool:
        """Check whether an input key exists."""
        return key in self.input_data

    def has_metadata(self, key: str) -> bool:
        """Check whether a metadata key exists."""
        return key in self.metadata


__all__ = ["AgentContext"]
