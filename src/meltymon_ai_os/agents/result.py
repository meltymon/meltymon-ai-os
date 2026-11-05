"""Immutable execution results for MELTYMON AI OS agents."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from .exceptions import AgentExecutionError


class AgentResultStatus(str, Enum):
    """Possible outcomes of an agent execution."""

    SUCCESS = "success"
    FAILURE = "failure"


def _validate_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} must not be empty.")

    return value


def _freeze(value: Any, path: str = "value") -> Any:
    """Recursively freeze supported result data."""

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain a finite number.")
        return value

    if isinstance(value, Mapping):
        frozen = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string mapping key.")

            frozen[key] = _freeze(item, f"{path}.{key}")

        return MappingProxyType(frozen)

    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze(item, f"{path}[{index}]") for index, item in enumerate(value)
        )

    raise TypeError(
        f"{path} contains an unsupported value type: {type(value).__name__}."
    )


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Immutable result returned by an agent execution."""

    agent_id: str
    correlation_id: str
    status: AgentResultStatus
    output: Any = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
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

        if not isinstance(self.status, AgentResultStatus):
            raise TypeError("status must be an AgentResultStatus.")

        if self.status is AgentResultStatus.SUCCESS:
            if self.error is not None:
                raise ValueError("A successful result cannot contain an error.")

        else:
            if not isinstance(self.error, str) or not self.error.strip():
                raise ValueError("A failed result must contain a non-empty error.")

            object.__setattr__(self, "error", self.error.strip())

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")

        object.__setattr__(
            self,
            "output",
            _freeze(self.output, "output"),
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

    @property
    def is_success(self) -> bool:
        return self.status is AgentResultStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status is AgentResultStatus.FAILURE

    @classmethod
    def success(
        cls,
        *,
        agent_id: str,
        correlation_id: str,
        output: Any = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentResult:
        """Create a successful result."""

        return cls(
            agent_id=agent_id,
            correlation_id=correlation_id,
            status=AgentResultStatus.SUCCESS,
            output=output,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def failure(
        cls,
        *,
        agent_id: str,
        correlation_id: str,
        error: str,
        output: Any = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentResult:
        """Create a failed result."""

        return cls(
            agent_id=agent_id,
            correlation_id=correlation_id,
            status=AgentResultStatus.FAILURE,
            output=output,
            error=error,
            metadata={} if metadata is None else metadata,
        )

    def unwrap(self) -> Any:
        """Return the output or raise an execution error."""

        if self.is_failure:
            raise AgentExecutionError(self.error)

        return self.output


__all__ = [
    "AgentResult",
    "AgentResultStatus",
]
