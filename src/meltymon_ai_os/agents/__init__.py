"""Public interface for the MELTYMON AI OS agent framework."""

from .base import AgentBase
from .capabilities import (
    Capability,
    CapabilitySet,
)
from .context import AgentContext
from .exceptions import (
    AgentApprovalRequiredError,
    AgentCapabilityError,
    AgentConfigurationError,
    AgentError,
    AgentExecutionError,
    AgentLifecycleError,
    AgentPermissionError,
    AgentResultError,
    AgentTimeoutError,
)
from .lifecycle import (
    AgentLifecycle,
    AgentState,
    LifecycleEvent,
)
from .result import (
    AgentResult,
    AgentResultStatus,
)

__all__ = [
    "AgentApprovalRequiredError",
    "AgentBase",
    "AgentCapabilityError",
    "AgentConfigurationError",
    "AgentContext",
    "AgentError",
    "AgentExecutionError",
    "AgentLifecycle",
    "AgentLifecycleError",
    "AgentPermissionError",
    "AgentResult",
    "AgentResultError",
    "AgentResultStatus",
    "AgentState",
    "AgentTimeoutError",
    "Capability",
    "CapabilitySet",
    "LifecycleEvent",
]
