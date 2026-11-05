"""Exception hierarchy for the MELTYMON AI OS agent framework."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent framework errors."""


class AgentConfigurationError(AgentError):
    """Raised when an agent configuration is invalid."""


class AgentLifecycleError(AgentError):
    """Raised when an invalid agent lifecycle transition is attempted."""


class AgentExecutionError(AgentError):
    """Raised when an agent fails during execution."""


class AgentTimeoutError(AgentExecutionError):
    """Raised when an agent execution exceeds its permitted time."""


class AgentCapabilityError(AgentError):
    """Raised when an agent attempts to use an unsupported capability."""


class AgentPermissionError(AgentError):
    """Raised when an agent attempts an unauthorized operation."""


class AgentApprovalRequiredError(AgentPermissionError):
    """Raised when an operation requires explicit approval."""


class AgentResultError(AgentError):
    """Raised when an agent produces an invalid or unusable result."""


__all__ = [
    "AgentApprovalRequiredError",
    "AgentCapabilityError",
    "AgentConfigurationError",
    "AgentError",
    "AgentExecutionError",
    "AgentLifecycleError",
    "AgentPermissionError",
    "AgentResultError",
    "AgentTimeoutError",
]
