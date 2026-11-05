"""Tests for the public orchestrator package interface."""

from meltymon_ai_os import orchestrator
from meltymon_ai_os.orchestrator import (
    AgentAlreadyRegisteredError,
    AgentFactory,
    AgentFactoryError,
    AgentNotRegisteredError,
    AgentRegistry,
    Orchestrator,
    OrchestratorError,
)
from meltymon_ai_os.orchestrator.engine import Orchestrator as OriginalOrchestrator
from meltymon_ai_os.orchestrator.registry import (
    AgentFactory as OriginalAgentFactory,
)
from meltymon_ai_os.orchestrator.registry import (
    AgentRegistry as OriginalAgentRegistry,
)


def test_public_exports_are_available():
    """All documented public symbols must be importable."""

    expected_exports = {
        "Orchestrator",
        "AgentRegistry",
        "AgentFactory",
        "OrchestratorError",
        "AgentAlreadyRegisteredError",
        "AgentNotRegisteredError",
        "AgentFactoryError",
    }

    assert set(orchestrator.__all__) == expected_exports


def test_all_exports_exist():
    """Every name in __all__ must exist in the package."""

    for name in orchestrator.__all__:
        assert hasattr(orchestrator, name)


def test_public_imports_reference_original_implementations():
    """Package exports must reference the original implementations."""

    assert orchestrator.Orchestrator is OriginalOrchestrator
    assert orchestrator.AgentRegistry is OriginalAgentRegistry
    assert orchestrator.AgentFactory is OriginalAgentFactory

    assert orchestrator.Orchestrator is Orchestrator
    assert orchestrator.AgentRegistry is AgentRegistry
    assert orchestrator.AgentFactory is AgentFactory


def test_exception_hierarchy_is_preserved():
    """Exported exceptions must preserve their inheritance."""

    assert issubclass(AgentAlreadyRegisteredError, OrchestratorError)
    assert issubclass(AgentNotRegisteredError, OrchestratorError)
    assert issubclass(AgentFactoryError, OrchestratorError)


def test_public_exports_contain_no_duplicates():
    """The public export list must not contain duplicate names."""

    assert len(orchestrator.__all__) == len(set(orchestrator.__all__))
