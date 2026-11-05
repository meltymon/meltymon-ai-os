"""Tests for immutable agent execution results."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from meltymon_ai_os.agents.exceptions import AgentExecutionError
from meltymon_ai_os.agents.result import (
    AgentResult,
    AgentResultStatus,
)


def test_successful_result_creation():
    result = AgentResult.success(
        agent_id="research-agent",
        correlation_id="request-123",
        output={"answer": 42},
    )

    assert result.agent_id == "research-agent"
    assert result.correlation_id == "request-123"
    assert result.status is AgentResultStatus.SUCCESS
    assert result.output["answer"] == 42
    assert result.error is None
    assert result.is_success
    assert not result.is_failure


def test_failed_result_creation():
    result = AgentResult.failure(
        agent_id="research-agent",
        correlation_id="request-123",
        error="Execution failed.",
    )

    assert result.status is AgentResultStatus.FAILURE
    assert result.error == "Execution failed."
    assert result.is_failure
    assert not result.is_success


def test_successful_result_can_be_unwrapped():
    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
        output="hello",
    )

    assert result.unwrap() == "hello"


def test_failed_result_cannot_be_unwrapped():
    result = AgentResult.failure(
        agent_id="agent",
        correlation_id="request",
        error="Something went wrong.",
    )

    with pytest.raises(
        AgentExecutionError,
        match="Something went wrong.",
    ):
        result.unwrap()


def test_success_without_output_is_valid():
    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
    )

    assert result.output is None
    assert result.unwrap() is None


def test_failure_requires_error():
    with pytest.raises(ValueError):
        AgentResult.failure(
            agent_id="agent",
            correlation_id="request",
            error="   ",
        )


def test_success_cannot_contain_error():
    with pytest.raises(ValueError):
        AgentResult(
            agent_id="agent",
            correlation_id="request",
            status=AgentResultStatus.SUCCESS,
            error="Unexpected error.",
        )


def test_status_must_be_enum():
    with pytest.raises(TypeError):
        AgentResult(
            agent_id="agent",
            correlation_id="request",
            status="success",
        )


@pytest.mark.parametrize(
    "agent_id",
    ["", "   ", None, 123],
)
def test_invalid_agent_id(agent_id):
    with pytest.raises((TypeError, ValueError)):
        AgentResult.success(
            agent_id=agent_id,
            correlation_id="request",
        )


@pytest.mark.parametrize(
    "correlation_id",
    ["", "   ", None, 123],
)
def test_invalid_correlation_id(correlation_id):
    with pytest.raises((TypeError, ValueError)):
        AgentResult.success(
            agent_id="agent",
            correlation_id=correlation_id,
        )


def test_identifiers_are_normalized():
    result = AgentResult.success(
        agent_id="  agent  ",
        correlation_id="  request  ",
    )

    assert result.agent_id == "agent"
    assert result.correlation_id == "request"


def test_output_is_immutable():
    source = {"answer": 42}

    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
        output=source,
    )

    source["answer"] = 99

    assert result.output["answer"] == 42

    with pytest.raises(TypeError):
        result.output["answer"] = 100


def test_nested_output_is_immutable():
    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
        output={
            "data": {
                "items": [1, 2, 3],
            }
        },
    )

    assert result.output["data"]["items"] == (1, 2, 3)

    with pytest.raises(TypeError):
        result.output["data"]["new"] = True


def test_metadata_is_immutable():
    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
        metadata={"source": "local"},
    )

    with pytest.raises(TypeError):
        result.metadata["source"] = "remote"


def test_non_string_mapping_keys_are_rejected():
    with pytest.raises(TypeError):
        AgentResult.success(
            agent_id="agent",
            correlation_id="request",
            output={123: "invalid"},
        )


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        AgentResult.success(
            agent_id="agent",
            correlation_id="request",
            output={"value": value},
        )


def test_unsupported_output_objects_are_rejected():
    with pytest.raises(TypeError):
        AgentResult.success(
            agent_id="agent",
            correlation_id="request",
            output={"value": object()},
        )


def test_metadata_must_be_a_mapping():
    with pytest.raises(TypeError):
        AgentResult.success(
            agent_id="agent",
            correlation_id="request",
            metadata=["invalid"],
        )


def test_created_at_must_be_timezone_aware():
    with pytest.raises(ValueError):
        AgentResult(
            agent_id="agent",
            correlation_id="request",
            status=AgentResultStatus.SUCCESS,
            created_at=datetime(2026, 11, 3, 20, 0),
        )


def test_created_at_is_normalized_to_utc():
    local_time = datetime(
        2026,
        11,
        3,
        21,
        0,
        tzinfo=timezone(timedelta(hours=1)),
    )

    result = AgentResult(
        agent_id="agent",
        correlation_id="request",
        status=AgentResultStatus.SUCCESS,
        created_at=local_time,
    )

    assert result.created_at.hour == 20
    assert result.created_at.tzinfo == UTC


def test_result_is_frozen():
    result = AgentResult.success(
        agent_id="agent",
        correlation_id="request",
    )

    with pytest.raises(AttributeError):
        result.agent_id = "another-agent"


def test_default_metadata_is_independent():
    first = AgentResult.success(
        agent_id="first",
        correlation_id="request-1",
    )
    second = AgentResult.success(
        agent_id="second",
        correlation_id="request-2",
    )

    assert first.metadata is not second.metadata
