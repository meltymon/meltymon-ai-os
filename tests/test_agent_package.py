"""Tests for the public agents package interface."""

from meltymon_ai_os import agents
from meltymon_ai_os.agents import (
    AgentApprovalRequiredError,
    AgentBase,
    AgentCapabilityError,
    AgentConfigurationError,
    AgentContext,
    AgentError,
    AgentExecutionError,
    AgentLifecycle,
    AgentLifecycleError,
    AgentPermissionError,
    AgentResult,
    AgentResultError,
    AgentResultStatus,
    AgentState,
    AgentTimeoutError,
    Capability,
    CapabilitySet,
    LifecycleEvent,
)


def test_public_exports_are_available():
    """All documented public symbols must be importable."""

    expected_exports = {
        "AgentBase",
        "AgentContext",
        "AgentResult",
        "AgentResultStatus",
        "AgentLifecycle",
        "AgentState",
        "LifecycleEvent",
        "Capability",
        "CapabilitySet",
        "AgentError",
        "AgentConfigurationError",
        "AgentLifecycleError",
        "AgentExecutionError",
        "AgentTimeoutError",
        "AgentCapabilityError",
        "AgentPermissionError",
        "AgentApprovalRequiredError",
        "AgentResultError",
    }

    assert set(agents.__all__) == expected_exports


def test_all_exports_exist():
    """Every name in __all__ must exist in the package."""

    for name in agents.__all__:
        assert hasattr(agents, name)


def test_public_imports_reference_original_classes():
    """Package exports must reference the original implementations."""

    assert agents.AgentBase is AgentBase
    assert agents.AgentContext is AgentContext
    assert agents.AgentResult is AgentResult
    assert agents.AgentResultStatus is AgentResultStatus
    assert agents.AgentLifecycle is AgentLifecycle
    assert agents.AgentState is AgentState
    assert agents.LifecycleEvent is LifecycleEvent
    assert agents.Capability is Capability
    assert agents.CapabilitySet is CapabilitySet


def test_exception_hierarchy_is_preserved():
    """Exported exceptions must preserve their inheritance."""

    assert issubclass(AgentConfigurationError, AgentError)
    assert issubclass(AgentLifecycleError, AgentError)
    assert issubclass(AgentExecutionError, AgentError)
    assert issubclass(AgentTimeoutError, AgentExecutionError)
    assert issubclass(AgentCapabilityError, AgentError)
    assert issubclass(AgentPermissionError, AgentError)
    assert issubclass(AgentApprovalRequiredError, AgentPermissionError)
    assert issubclass(AgentResultError, AgentError)


def test_public_exports_contain_no_duplicates():
    """The public export list must not contain duplicate names."""

    assert len(agents.__all__) == len(set(agents.__all__))
