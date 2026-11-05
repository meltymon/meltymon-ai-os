"""Tests for the concurrent execution manager."""

import asyncio

import pytest

from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.result import AgentResult
from meltymon_ai_os.execution.manager import ExecutionManager
from meltymon_ai_os.execution.policy import ExecutionPolicy
from meltymon_ai_os.execution.report import ExecutionStatus
from meltymon_ai_os.orchestrator.engine import Orchestrator


class FakeOrchestrator(Orchestrator):
    """Lightweight orchestrator substitute for isolated tests."""

    def __init__(self, handler) -> None:
        self.handler = handler

    async def dispatch(self, context: AgentContext) -> AgentResult:
        return await self.handler(context)


def make_contexts(count: int) -> tuple[AgentContext, ...]:
    """Create a collection of unique agent contexts."""

    return tuple(AgentContext(agent_id=f"agent-{index}") for index in range(count))


def make_success(context: AgentContext) -> AgentResult:
    """Create a successful result for a context."""

    return AgentResult.success(
        agent_id=context.agent_id,
        correlation_id=context.correlation_id,
        output={"agent": context.agent_id},
    )


def make_failure(context: AgentContext) -> AgentResult:
    """Create a failed result for a context."""

    return AgentResult.failure(
        agent_id=context.agent_id,
        correlation_id=context.correlation_id,
        error="Simulated agent failure.",
    )


class TestExecutionManager:
    """Test execution manager behavior."""

    def test_rejects_invalid_orchestrator(self) -> None:
        with pytest.raises(TypeError):
            ExecutionManager(orchestrator="invalid")  # type: ignore[arg-type]

    def test_rejects_invalid_policy(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        orchestrator = FakeOrchestrator(handler)

        with pytest.raises(TypeError):
            ExecutionManager(
                orchestrator=orchestrator,
                policy="invalid",  # type: ignore[arg-type]
            )

    def test_default_policy(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        orchestrator = FakeOrchestrator(handler)
        manager = ExecutionManager(orchestrator)

        assert manager.orchestrator is orchestrator
        assert manager.policy == ExecutionPolicy()
        assert manager.policy.max_concurrency == 4

    @pytest.mark.asyncio
    async def test_rejects_string_contexts(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        with pytest.raises(TypeError, match="iterable of AgentContext"):
            await manager.execute_many("invalid")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_rejects_non_iterable_contexts(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        with pytest.raises(TypeError, match="iterable of AgentContext"):
            await manager.execute_many(42)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_rejects_invalid_context_items(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        with pytest.raises(TypeError, match="Every item"):
            await manager.execute_many(
                ("invalid-context",)  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_empty_execution(self) -> None:
        async def handler(context: AgentContext) -> AgentResult:
            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        report = await manager.execute_many(())

        assert report.total == 0
        assert report.succeeded == 0
        assert report.is_success is False

    @pytest.mark.asyncio
    async def test_executes_multiple_agents(self) -> None:
        contexts = make_contexts(5)

        async def handler(context: AgentContext) -> AgentResult:
            await asyncio.sleep(0.01)
            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        report = await manager.execute_many(contexts)

        assert report.total == 5
        assert report.succeeded == 5
        assert report.failed == 0
        assert report.errors == 0
        assert report.is_success is True

    @pytest.mark.asyncio
    async def test_preserves_input_order(self) -> None:
        contexts = make_contexts(4)

        async def handler(context: AgentContext) -> AgentResult:
            index = int(context.agent_id.split("-")[1])

            await asyncio.sleep((3 - index) * 0.01)

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(max_concurrency=4),
        )

        report = await manager.execute_many(contexts)

        assert tuple(record.context.agent_id for record in report.records) == tuple(
            context.agent_id for context in contexts
        )

    @pytest.mark.asyncio
    async def test_respects_max_concurrency(self) -> None:
        contexts = make_contexts(8)

        active = 0
        maximum_active = 0
        lock = asyncio.Lock()

        async def handler(context: AgentContext) -> AgentResult:
            nonlocal active, maximum_active

            async with lock:
                active += 1
                maximum_active = max(maximum_active, active)

            await asyncio.sleep(0.02)

            async with lock:
                active -= 1

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(max_concurrency=2),
        )

        report = await manager.execute_many(contexts)

        assert report.succeeded == 8
        assert maximum_active == 2
        assert active == 0

    @pytest.mark.asyncio
    async def test_continues_after_agent_failure(self) -> None:
        contexts = make_contexts(3)

        async def handler(context: AgentContext) -> AgentResult:
            if context.agent_id == "agent-1":
                return make_failure(context)

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(
                max_concurrency=1,
                continue_on_error=True,
            ),
        )

        report = await manager.execute_many(contexts)

        assert report.total == 3
        assert report.succeeded == 2
        assert report.failed == 1
        assert report.cancelled == 0

    @pytest.mark.asyncio
    async def test_stops_after_failure_when_fail_fast_enabled(self) -> None:
        contexts = make_contexts(4)
        executed: list[str] = []

        async def handler(context: AgentContext) -> AgentResult:
            executed.append(context.agent_id)

            if context.agent_id == "agent-1":
                return make_failure(context)

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(
                max_concurrency=1,
                continue_on_error=False,
            ),
        )

        report = await manager.execute_many(contexts)

        assert executed == ["agent-0", "agent-1"]
        assert report.total == 4
        assert report.succeeded == 1
        assert report.failed == 1
        assert report.cancelled == 2

    @pytest.mark.asyncio
    async def test_stops_after_execution_error_when_fail_fast_enabled(self) -> None:
        contexts = make_contexts(4)
        executed: list[str] = []

        async def handler(context: AgentContext) -> AgentResult:
            executed.append(context.agent_id)

            if context.agent_id == "agent-1":
                raise RuntimeError("Simulated infrastructure error.")

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(
                max_concurrency=1,
                continue_on_error=False,
            ),
        )

        report = await manager.execute_many(contexts)

        assert executed == ["agent-0", "agent-1"]
        assert report.total == 4
        assert report.succeeded == 1
        assert report.errors == 1
        assert report.cancelled == 2
        assert report.records[1].status is ExecutionStatus.ERROR

    @pytest.mark.asyncio
    async def test_records_unexpected_execution_errors(self) -> None:
        contexts = make_contexts(3)

        async def handler(context: AgentContext) -> AgentResult:
            if context.agent_id == "agent-1":
                raise RuntimeError("Simulated infrastructure error.")

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(max_concurrency=1),
        )

        report = await manager.execute_many(contexts)

        assert report.total == 3
        assert report.succeeded == 2
        assert report.errors == 1
        assert report.has_failures is True

        error_record = report.records[1]

        assert error_record.status is ExecutionStatus.ERROR
        assert "RuntimeError" in error_record.error

    @pytest.mark.asyncio
    async def test_batch_timeout_cancels_unfinished_execution(self) -> None:
        contexts = make_contexts(2)

        async def handler(context: AgentContext) -> AgentResult:
            await asyncio.sleep(10)
            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(
                max_concurrency=1,
                batch_timeout=0.05,
            ),
        )

        report = await manager.execute_many(contexts)

        assert report.total == 2
        assert report.cancelled == 2
        assert report.succeeded == 0

        for record in report.records:
            assert record.status is ExecutionStatus.CANCELLED
            assert record.error == "Batch execution timed out."

    @pytest.mark.asyncio
    async def test_external_cancellation_propagates(self) -> None:
        context = make_contexts(1)[0]

        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def handler(context: AgentContext) -> AgentResult:
            started.set()

            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

            return make_success(context)

        manager = ExecutionManager(FakeOrchestrator(handler))

        task = asyncio.create_task(manager.execute_many((context,)))

        await asyncio.wait_for(started.wait(), timeout=1)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert cancelled.is_set()

    @pytest.mark.asyncio
    async def test_external_cancellation_cleans_up_queued_tasks(self) -> None:
        contexts = make_contexts(4)

        started = asyncio.Event()
        cancelled = asyncio.Event()
        executed: list[str] = []

        async def handler(context: AgentContext) -> AgentResult:
            executed.append(context.agent_id)
            started.set()

            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(max_concurrency=1),
        )

        task = asyncio.create_task(manager.execute_many(contexts))

        await asyncio.wait_for(started.wait(), timeout=1)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert cancelled.is_set()
        assert executed == ["agent-0"]

    @pytest.mark.asyncio
    async def test_every_context_has_exactly_one_record(self) -> None:
        contexts = make_contexts(10)

        async def handler(context: AgentContext) -> AgentResult:
            await asyncio.sleep(0.005)
            return make_success(context)

        manager = ExecutionManager(
            FakeOrchestrator(handler),
            ExecutionPolicy(max_concurrency=3),
        )

        report = await manager.execute_many(contexts)

        recorded_ids = [record.context.correlation_id for record in report.records]

        expected_ids = [context.correlation_id for context in contexts]

        assert len(recorded_ids) == len(expected_ids)
        assert recorded_ids == expected_ids
        assert len(set(recorded_ids)) == len(recorded_ids)
