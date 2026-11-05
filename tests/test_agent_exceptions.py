"""Tests for the agent exception hierarchy."""

import pytest

from meltymon_ai_os.agents.exceptions import (
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


def test_agent_exception_hierarchy():
    """Verify exception inheritance and catch behavior."""

    exceptions = [
        AgentConfigurationError,
        AgentLifecycleError,
        AgentExecutionError,
        AgentCapabilityError,
        AgentPermissionError,
        AgentResultError,
    ]

    for exception in exceptions:
        assert issubclass(exception, AgentError)

    assert issubclass(AgentTimeoutError, AgentExecutionError)
    assert issubclass(AgentApprovalRequiredError, AgentPermissionError)

    with pytest.raises(AgentExecutionError):
        raise AgentTimeoutError("Execution timed out")

    with pytest.raises(AgentPermissionError):
        raise AgentApprovalRequiredError("Approval required")
