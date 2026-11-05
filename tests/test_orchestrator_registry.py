"""Tests for the MELTYMON AI OS agent registry."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from meltymon_ai_os.agents.base import AgentBase
from meltymon_ai_os.agents.lifecycle import AgentState
from meltymon_ai_os.orchestrator.exceptions import (
    AgentAlreadyRegisteredError,
    AgentFactoryError,
    AgentNotRegisteredError,
)
from meltymon_ai_os.orchestrator.registry import AgentRegistry


class DummyAgent(AgentBase):
    """Minimal concrete agent for registry tests."""

    async def _execute(self, context):
        return {"status": "ok"}


def create_agent(agent_id: str = "test-agent") -> DummyAgent:
    """Create a fresh test agent."""
    return DummyAgent(agent_id=agent_id)


def move_agent_to_succeeded(agent: AgentBase) -> None:
    """Move an agent through its lifecycle to SUCCEEDED."""
    agent.lifecycle.transition(AgentState.INITIALIZING)
    agent.lifecycle.transition(AgentState.READY)
    agent.lifecycle.transition(AgentState.RUNNING)
    agent.lifecycle.transition(AgentState.SUCCEEDED)


def test_registry_starts_empty():
    registry = AgentRegistry()

    assert registry.get_registered_agents() == ()


def test_register_and_contains():
    registry = AgentRegistry()

    registry.register("test-agent", create_agent)

    assert registry.contains("test-agent")


def test_register_normalizes_agent_id():
    registry = AgentRegistry()

    registry.register("  test-agent  ", create_agent)

    assert registry.contains("test-agent")
    assert registry.get_registered_agents() == ("test-agent",)


def test_register_rejects_duplicate_agent_id():
    registry = AgentRegistry()

    registry.register("test-agent", create_agent)

    with pytest.raises(AgentAlreadyRegisteredError):
        registry.register("test-agent", create_agent)


def test_register_rejects_invalid_agent_id():
    registry = AgentRegistry()

    with pytest.raises(TypeError):
        registry.register(123, create_agent)

    with pytest.raises(ValueError):
        registry.register("   ", create_agent)


def test_register_rejects_non_callable_factory():
    registry = AgentRegistry()

    with pytest.raises(TypeError):
        registry.register("test-agent", None)


def test_get_registered_agents_returns_sorted_tuple():
    registry = AgentRegistry()

    registry.register("zeta", lambda: create_agent("zeta"))
    registry.register("alpha", lambda: create_agent("alpha"))

    result = registry.get_registered_agents()

    assert result == ("alpha", "zeta")
    assert isinstance(result, tuple)


def test_unregister_removes_agent():
    registry = AgentRegistry()

    registry.register("test-agent", create_agent)
    registry.unregister("test-agent")

    assert not registry.contains("test-agent")
    assert registry.get_registered_agents() == ()


def test_unregister_rejects_unknown_agent():
    registry = AgentRegistry()

    with pytest.raises(AgentNotRegisteredError):
        registry.unregister("unknown-agent")


def test_create_returns_fresh_agent_instances():
    registry = AgentRegistry()
    registry.register("test-agent", create_agent)

    first = registry.create("test-agent")
    second = registry.create("test-agent")

    assert isinstance(first, DummyAgent)
    assert isinstance(second, DummyAgent)
    assert first is not second
    assert first.agent_id == "test-agent"
    assert second.agent_id == "test-agent"
    assert first.state is AgentState.CREATED
    assert second.state is AgentState.CREATED


def test_create_rejects_unknown_agent():
    registry = AgentRegistry()

    with pytest.raises(AgentNotRegisteredError):
        registry.create("unknown-agent")


def test_create_wraps_factory_exception():
    registry = AgentRegistry()

    def broken_factory():
        raise RuntimeError("Factory failure")

    registry.register("test-agent", broken_factory)

    with pytest.raises(AgentFactoryError) as exc_info:
        registry.create("test-agent")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_create_rejects_wrong_factory_return_type():
    registry = AgentRegistry()
    registry.register("test-agent", lambda: object())

    with pytest.raises(AgentFactoryError):
        registry.create("test-agent")


def test_create_rejects_mismatched_agent_id():
    registry = AgentRegistry()
    registry.register(
        "test-agent",
        lambda: create_agent("different-agent"),
    )

    with pytest.raises(AgentFactoryError):
        registry.create("test-agent")


def test_create_rejects_agent_not_in_created_state():
    registry = AgentRegistry()

    def used_agent_factory():
        agent = create_agent()
        move_agent_to_succeeded(agent)
        return agent

    registry.register("test-agent", used_agent_factory)

    with pytest.raises(AgentFactoryError):
        registry.create("test-agent")


def test_concurrent_registration_allows_only_one_registration():
    registry = AgentRegistry()
    barrier = Barrier(8)

    def attempt_registration():
        barrier.wait()

        try:
            registry.register("shared-agent", create_agent)
            return "registered"
        except AgentAlreadyRegisteredError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: attempt_registration(),
                range(8),
            )
        )

    assert results.count("registered") == 1
    assert results.count("duplicate") == 7
    assert registry.get_registered_agents() == ("shared-agent",)
