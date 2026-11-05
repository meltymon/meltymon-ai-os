"""Tests for the MELTYMON AI OS agent base class."""

import asyncio

import pytest

from meltymon_ai_os.agents.base import AgentBase
from meltymon_ai_os.agents.capabilities import CapabilitySet
from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.exceptions import (
    AgentConfigurationError,
    AgentLifecycleError,
)
from meltymon_ai_os.agents.lifecycle import AgentState


class SuccessfulAgent(AgentBase):
    async def _execute(self, context):
        return {
            "message": "success",
            "value": context.get_input("value"),
        }


class InitializingAgent(AgentBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialized = False

    async def _initialize(self, context):
        self.initialized = True

    async def _execute(self, context):
        return {"initialized": self.initialized}


class FailingAgent(AgentBase):
    async def _execute(self, context):
        raise RuntimeError("Execution failed.")


class InitializingFailingAgent(AgentBase):
    async def _initialize(self, context):
        raise RuntimeError("Initialization failed.")

    async def _execute(self, context):
        return None


class SlowAgent(AgentBase):
    async def _execute(self, context):
        await asyncio.sleep(1)
        return {"finished": True}


class BlockingAgent(AgentBase):
    async def _execute(self, context):
        await asyncio.Event().wait()


class InternalTimeoutAgent(AgentBase):
    async def _execute(self, context):
        raise TimeoutError("Internal operation timed out.")


class UnsupportedOutputAgent(AgentBase):
    async def _execute(self, context):
        return object()


class ConcurrentAgent(AgentBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.execution_count = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def _execute(self, context):
        self.execution_count += 1
        self.started.set()

        await self.release.wait()

        return {"execution_count": self.execution_count}


def make_context(agent_id="test-agent"):
    return AgentContext(
        agent_id=agent_id,
        input_data={"value": 42},
    )


def test_agent_creation():
    agent = SuccessfulAgent(agent_id="test-agent")

    assert agent.agent_id == "test-agent"
    assert agent.state is AgentState.CREATED
    assert isinstance(agent.capabilities, CapabilitySet)
    assert agent.timeout is None


def test_agent_identifier_is_normalized():
    agent = SuccessfulAgent(agent_id="  test-agent  ")

    assert agent.agent_id == "test-agent"


@pytest.mark.parametrize("agent_id", ["", "   "])
def test_empty_agent_identifier_is_rejected(agent_id):
    with pytest.raises(ValueError):
        SuccessfulAgent(agent_id=agent_id)


def test_non_string_agent_identifier_is_rejected():
    with pytest.raises(TypeError):
        SuccessfulAgent(agent_id=123)


def test_capabilities_are_normalized():
    agent = SuccessfulAgent(
        agent_id="test-agent",
        capabilities=["llm.generate", "system.monitor"],
    )

    assert agent.capabilities.has("llm.generate")
    assert agent.capabilities.has("system.monitor")


def test_existing_capability_set_is_supported():
    capabilities = CapabilitySet(["llm.generate"])

    agent = SuccessfulAgent(
        agent_id="test-agent",
        capabilities=capabilities,
    )

    assert agent.capabilities is capabilities


@pytest.mark.parametrize(
    "timeout",
    [0, -1, float("inf"), float("nan")],
)
def test_invalid_timeout_is_rejected(timeout):
    with pytest.raises(ValueError):
        SuccessfulAgent(
            agent_id="test-agent",
            timeout=timeout,
        )


@pytest.mark.parametrize("timeout", ["1", True])
def test_non_numeric_timeout_is_rejected(timeout):
    with pytest.raises(TypeError):
        SuccessfulAgent(
            agent_id="test-agent",
            timeout=timeout,
        )


@pytest.mark.asyncio
async def test_successful_execution():
    agent = SuccessfulAgent(agent_id="test-agent")
    context = make_context()

    result = await agent.execute(context)

    assert result.is_success
    assert result.output == {
        "message": "success",
        "value": 42,
    }
    assert result.agent_id == "test-agent"
    assert result.correlation_id == context.correlation_id
    assert agent.state is AgentState.SUCCEEDED


@pytest.mark.asyncio
async def test_successful_execution_records_lifecycle():
    agent = SuccessfulAgent(agent_id="test-agent")

    await agent.execute(make_context())

    states = [event.current_state for event in agent.lifecycle.history]

    assert states == [
        AgentState.INITIALIZING,
        AgentState.READY,
        AgentState.RUNNING,
        AgentState.SUCCEEDED,
    ]


@pytest.mark.asyncio
async def test_initialization_runs_before_execution():
    agent = InitializingAgent(agent_id="test-agent")

    result = await agent.execute(make_context())

    assert agent.initialized is True
    assert result.is_success
    assert result.output == {"initialized": True}


@pytest.mark.asyncio
async def test_execution_failure_returns_failure_result():
    agent = FailingAgent(agent_id="test-agent")

    result = await agent.execute(make_context())

    assert result.is_failure
    assert result.error == "Execution failed."
    assert result.metadata["exception_type"] == "RuntimeError"
    assert agent.state is AgentState.FAILED


@pytest.mark.asyncio
async def test_initialization_failure_returns_failure_result():
    agent = InitializingFailingAgent(agent_id="test-agent")

    result = await agent.execute(make_context())

    assert result.is_failure
    assert result.error == "Initialization failed."
    assert agent.state is AgentState.FAILED


@pytest.mark.asyncio
async def test_timeout_returns_failure_result():
    agent = SlowAgent(
        agent_id="test-agent",
        timeout=0.01,
    )

    result = await agent.execute(make_context())

    assert result.is_failure
    assert result.metadata["exception_type"] == "AgentTimeoutError"
    assert "timeout" in result.error.lower()
    assert agent.state is AgentState.FAILED


@pytest.mark.asyncio
async def test_internal_timeout_is_not_misclassified():
    agent = InternalTimeoutAgent(
        agent_id="test-agent",
        timeout=1.0,
    )

    result = await agent.execute(make_context())

    assert result.is_failure
    assert result.error == "Internal operation timed out."
    assert result.metadata["exception_type"] == "TimeoutError"
    assert agent.state is AgentState.FAILED


@pytest.mark.asyncio
async def test_external_cancellation_is_reraised():
    agent = BlockingAgent(agent_id="test-agent")

    task = asyncio.create_task(agent.execute(make_context()))

    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert agent.state is AgentState.CANCELLED


@pytest.mark.asyncio
async def test_cancelled_execution_records_lifecycle():
    agent = BlockingAgent(agent_id="test-agent")

    task = asyncio.create_task(agent.execute(make_context()))

    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert agent.lifecycle.history[-1].current_state is AgentState.CANCELLED


@pytest.mark.asyncio
async def test_context_agent_id_must_match():
    agent = SuccessfulAgent(agent_id="test-agent")

    with pytest.raises(AgentConfigurationError):
        await agent.execute(make_context("different-agent"))

    assert agent.state is AgentState.CREATED


@pytest.mark.asyncio
async def test_invalid_context_type_is_rejected():
    agent = SuccessfulAgent(agent_id="test-agent")

    with pytest.raises(TypeError):
        await agent.execute({"value": 42})


@pytest.mark.asyncio
async def test_agent_can_only_execute_once():
    agent = SuccessfulAgent(agent_id="test-agent")

    await agent.execute(make_context())

    with pytest.raises(AgentLifecycleError):
        await agent.execute(make_context())


@pytest.mark.asyncio
async def test_failed_agent_cannot_be_reexecuted():
    agent = FailingAgent(agent_id="test-agent")

    await agent.execute(make_context())

    with pytest.raises(AgentLifecycleError):
        await agent.execute(make_context())


@pytest.mark.asyncio
async def test_unsupported_output_becomes_failure():
    agent = UnsupportedOutputAgent(agent_id="test-agent")

    result = await agent.execute(make_context())

    assert result.is_failure
    assert result.metadata["exception_type"] == "TypeError"
    assert "unsupported value type" in result.error
    assert agent.state is AgentState.FAILED


@pytest.mark.asyncio
async def test_concurrent_execution_does_not_run_agent_twice():
    agent = ConcurrentAgent(agent_id="test-agent")
    context = make_context()

    first_task = asyncio.create_task(agent.execute(context))

    await agent.started.wait()

    second_task = asyncio.create_task(agent.execute(context))

    await asyncio.sleep(0)

    agent.release.set()

    first_result = await first_task

    assert first_result.is_success

    with pytest.raises(AgentLifecycleError):
        await second_task

    assert agent.execution_count == 1
    assert agent.state is AgentState.SUCCEEDED
