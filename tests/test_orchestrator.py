"""Tests for the MELTYMON AI OS orchestrator."""

import asyncio

import pytest

from meltymon_ai_os.agents.base import AgentBase
from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.lifecycle import AgentState
from meltymon_ai_os.agents.result import AgentResult
from meltymon_ai_os.orchestrator.engine import Orchestrator
from meltymon_ai_os.orchestrator.exceptions import (
    AgentNotRegisteredError,
    OrchestratorError,
)
from meltymon_ai_os.orchestrator.registry import AgentRegistry


class EchoAgent(AgentBase):
    """Agent that returns its input data."""

    async def _execute(self, context: AgentContext):
        return dict(context.input_data)


class FailingAgent(AgentBase):
    """Agent that raises an exception during execution."""

    async def _execute(self, context: AgentContext):
        raise RuntimeError("Simulated execution failure.")


class WaitingAgent(AgentBase):
    """Agent that waits until its execution is cancelled."""

    async def _execute(self, context: AgentContext):
        await asyncio.Event().wait()


class InvalidResultAgent(AgentBase):
    """Agent that deliberately returns an invalid result."""

    async def _execute(self, context: AgentContext):
        return None

    async def execute(self, context: AgentContext):
        return "invalid result"


class WrongAgentIdResult(AgentBase):
    """Agent that returns a result with a different agent ID."""

    async def _execute(self, context: AgentContext):
        return None

    async def execute(self, context: AgentContext):
        return AgentResult.success(
            agent_id="another-agent",
            correlation_id=context.correlation_id,
            output={"unexpected": True},
        )


class WrongCorrelationResult(AgentBase):
    """Agent that returns a different correlation ID."""

    async def _execute(self, context: AgentContext):
        return None

    async def execute(self, context: AgentContext):
        return AgentResult.success(
            agent_id=context.agent_id,
            correlation_id="wrong-correlation",
            output={"unexpected": True},
        )


def create_orchestrator(agent_class=EchoAgent):
    """Create an orchestrator with one registered agent."""

    registry = AgentRegistry()

    registry.register(
        "test-agent",
        lambda: agent_class(agent_id="test-agent"),
    )

    return Orchestrator(registry)


def test_constructor_requires_registry():
    with pytest.raises(TypeError):
        Orchestrator("invalid")


def test_registry_property_returns_injected_registry():
    registry = AgentRegistry()
    orchestrator = Orchestrator(registry)

    assert orchestrator.registry is registry


@pytest.mark.asyncio
async def test_dispatch_returns_successful_result():
    orchestrator = create_orchestrator()

    context = AgentContext(
        agent_id="test-agent",
        input_data={"message": "hello"},
    )

    result = await orchestrator.dispatch(context)

    assert result.is_success
    assert result.agent_id == context.agent_id
    assert result.correlation_id == context.correlation_id
    assert result.output["message"] == "hello"


@pytest.mark.asyncio
async def test_dispatch_preserves_failed_agent_result():
    orchestrator = create_orchestrator(FailingAgent)

    context = AgentContext(agent_id="test-agent")

    result = await orchestrator.dispatch(context)

    assert result.is_failure
    assert result.error == "Simulated execution failure."
    assert result.agent_id == context.agent_id
    assert result.correlation_id == context.correlation_id


@pytest.mark.asyncio
async def test_dispatch_unknown_agent_raises_orchestrator_error():
    orchestrator = Orchestrator(AgentRegistry())

    context = AgentContext(agent_id="unknown-agent")

    with pytest.raises(OrchestratorError) as exc_info:
        await orchestrator.dispatch(context)

    assert isinstance(
        exc_info.value.__cause__,
        AgentNotRegisteredError,
    )


@pytest.mark.asyncio
async def test_dispatch_wraps_factory_errors():
    registry = AgentRegistry()

    def broken_factory():
        raise RuntimeError("Factory failure.")

    registry.register("test-agent", broken_factory)

    orchestrator = Orchestrator(registry)

    context = AgentContext(agent_id="test-agent")

    with pytest.raises(OrchestratorError):
        await orchestrator.dispatch(context)


@pytest.mark.asyncio
async def test_dispatch_rejects_invalid_context():
    orchestrator = create_orchestrator()

    with pytest.raises(TypeError):
        await orchestrator.dispatch("invalid")


@pytest.mark.asyncio
async def test_dispatch_rejects_invalid_result():
    orchestrator = create_orchestrator(InvalidResultAgent)

    context = AgentContext(agent_id="test-agent")

    with pytest.raises(
        OrchestratorError,
        match="invalid result",
    ):
        await orchestrator.dispatch(context)


@pytest.mark.asyncio
async def test_dispatch_rejects_wrong_result_agent_id():
    orchestrator = create_orchestrator(WrongAgentIdResult)

    context = AgentContext(agent_id="test-agent")

    with pytest.raises(
        OrchestratorError,
        match="identifier",
    ):
        await orchestrator.dispatch(context)


@pytest.mark.asyncio
async def test_dispatch_rejects_wrong_correlation_id():
    orchestrator = create_orchestrator(WrongCorrelationResult)

    context = AgentContext(agent_id="test-agent")

    with pytest.raises(
        OrchestratorError,
        match="correlation ID",
    ):
        await orchestrator.dispatch(context)


@pytest.mark.asyncio
async def test_dispatch_propagates_cancellation():
    registry = AgentRegistry()
    agents = []

    def factory():
        agent = WaitingAgent(agent_id="test-agent")
        agents.append(agent)
        return agent

    registry.register("test-agent", factory)

    orchestrator = Orchestrator(registry)

    context = AgentContext(agent_id="test-agent")

    task = asyncio.create_task(orchestrator.dispatch(context))

    for _ in range(100):
        if agents and agents[0].state is AgentState.RUNNING:
            break

        await asyncio.sleep(0)

    assert agents
    assert agents[0].state is AgentState.RUNNING

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert agents[0].state is AgentState.CANCELLED
