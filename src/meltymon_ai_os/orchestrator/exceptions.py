"""Exception hierarchy for the MELTYMON AI OS orchestrator."""


class OrchestratorError(Exception):
    """Base exception for orchestrator-related errors."""


class AgentAlreadyRegisteredError(OrchestratorError):
    """Raised when an agent ID is already registered."""


class AgentNotRegisteredError(OrchestratorError):
    """Raised when an agent ID is not registered."""


class AgentFactoryError(OrchestratorError):
    """Raised when an agent factory fails or returns an invalid agent."""


__all__ = [
    "AgentAlreadyRegisteredError",
    "AgentFactoryError",
    "AgentNotRegisteredError",
    "OrchestratorError",
]
