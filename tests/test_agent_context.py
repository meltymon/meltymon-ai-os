"""Tests for immutable agent execution contexts."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from meltymon_ai_os.agents.context import AgentContext


def test_context_creation():
    context = AgentContext(agent_id="research-agent")

    assert context.agent_id == "research-agent"
    assert context.input_data == {}
    assert context.metadata == {}
    assert context.correlation_id
    assert context.created_at.tzinfo == UTC


def test_identifiers_are_normalized():
    context = AgentContext(
        agent_id="  research-agent  ",
        correlation_id="  request-123  ",
    )

    assert context.agent_id == "research-agent"
    assert context.correlation_id == "request-123"


def test_correlation_ids_are_unique_by_default():
    first = AgentContext(agent_id="agent")
    second = AgentContext(agent_id="agent")

    assert first.correlation_id != second.correlation_id


def test_input_data_is_immutable():
    source = {"query": "test"}
    context = AgentContext(
        agent_id="agent",
        input_data=source,
    )

    source["query"] = "modified"

    assert context.input_data["query"] == "test"

    with pytest.raises(TypeError):
        context.input_data["query"] = "modified"


def test_metadata_is_immutable():
    context = AgentContext(
        agent_id="agent",
        metadata={"environment": "test"},
    )

    with pytest.raises(TypeError):
        context.metadata["environment"] = "production"


def test_nested_data_is_immutable():
    context = AgentContext(
        agent_id="agent",
        input_data={
            "payload": {
                "items": [1, 2, 3],
            }
        },
    )

    assert context.input_data["payload"]["items"] == (1, 2, 3)

    with pytest.raises(TypeError):
        context.input_data["payload"]["new"] = True


def test_nested_source_mutation_does_not_affect_context():
    source = {
        "payload": {
            "items": [1, 2, 3],
        }
    }

    context = AgentContext(
        agent_id="agent",
        input_data=source,
    )

    source["payload"]["items"].append(4)

    assert context.input_data["payload"]["items"] == (1, 2, 3)


def test_input_accessors():
    context = AgentContext(
        agent_id="agent",
        input_data={"query": "hello"},
    )

    assert context.get_input("query") == "hello"
    assert context.get_input("missing") is None
    assert context.get_input("missing", "default") == "default"
    assert context.has_input("query")
    assert not context.has_input("missing")


def test_metadata_accessors():
    context = AgentContext(
        agent_id="agent",
        metadata={"environment": "test"},
    )

    assert context.get_metadata("environment") == "test"
    assert context.get_metadata("missing", "default") == "default"
    assert context.has_metadata("environment")
    assert not context.has_metadata("missing")


@pytest.mark.parametrize(
    "agent_id",
    ["", "   ", None, 123],
)
def test_invalid_agent_id(agent_id):
    with pytest.raises((TypeError, ValueError)):
        AgentContext(agent_id=agent_id)


@pytest.mark.parametrize(
    "correlation_id",
    ["", "   ", None, 123],
)
def test_invalid_correlation_id(correlation_id):
    with pytest.raises((TypeError, ValueError)):
        AgentContext(
            agent_id="agent",
            correlation_id=correlation_id,
        )


@pytest.mark.parametrize(
    "input_data",
    ["not-a-mapping", [1, 2, 3], 123, None],
)
def test_invalid_input_data(input_data):
    with pytest.raises(TypeError):
        AgentContext(
            agent_id="agent",
            input_data=input_data,
        )


@pytest.mark.parametrize(
    "metadata",
    ["not-a-mapping", [1, 2, 3], 123, None],
)
def test_invalid_metadata(metadata):
    with pytest.raises(TypeError):
        AgentContext(
            agent_id="agent",
            metadata=metadata,
        )


def test_non_string_mapping_keys_are_rejected():
    with pytest.raises(TypeError):
        AgentContext(
            agent_id="agent",
            input_data={123: "invalid"},
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        AgentContext(
            agent_id="agent",
            input_data={"value": value},
        )


def test_unsupported_objects_are_rejected():
    with pytest.raises(TypeError):
        AgentContext(
            agent_id="agent",
            input_data={"value": object()},
        )


def test_created_at_must_be_timezone_aware():
    with pytest.raises(ValueError):
        AgentContext(
            agent_id="agent",
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

    context = AgentContext(
        agent_id="agent",
        created_at=local_time,
    )

    assert context.created_at.hour == 20
    assert context.created_at.tzinfo == UTC


def test_context_is_frozen():
    context = AgentContext(agent_id="agent")

    with pytest.raises(AttributeError):
        context.agent_id = "another-agent"


def test_context_uses_independent_default_mappings():
    first = AgentContext(agent_id="first")
    second = AgentContext(agent_id="second")

    assert first.input_data is not second.input_data
    assert first.metadata is not second.metadata
