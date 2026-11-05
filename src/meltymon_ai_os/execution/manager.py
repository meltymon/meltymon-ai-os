"""Execution manager for concurrent MELTYMON AI OS agent execution."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.orchestrator.engine import Orchestrator

from .policy import ExecutionPolicy
from .report import (
    ExecutionRecord,
    ExecutionReport,
    ExecutionStatus,
)


class ExecutionManager:
    """Coordinate concurrent execution of multiple agents."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        if not isinstance(orchestrator, Orchestrator):
            raise TypeError("orchestrator must be an Orchestrator.")

        if policy is not None and not isinstance(
            policy,
            ExecutionPolicy,
        ):
            raise TypeError("policy must be an ExecutionPolicy.")

        self._orchestrator = orchestrator
        self._policy = ExecutionPolicy() if policy is None else policy

    @property
    def orchestrator(self) -> Orchestrator:
        """Return the associated orchestrator."""

        return self._orchestrator

    @property
    def policy(self) -> ExecutionPolicy:
        """Return the execution policy."""

        return self._policy

    async def execute_many(
        self,
        contexts: Iterable[AgentContext],
    ) -> ExecutionReport:
        """Execute multiple agent contexts concurrently.

        Results are returned in the original input order.

        The concurrency limit is enforced by an asyncio semaphore.
        A batch timeout cancels unfinished executions and records
        them as CANCELLED.

        External cancellation is propagated to the caller after
        all child tasks have been cancelled and awaited.
        """

        if isinstance(contexts, (str, bytes)):
            raise TypeError("contexts must be an iterable of AgentContext objects.")

        if not isinstance(contexts, Iterable):
            raise TypeError("contexts must be an iterable of AgentContext objects.")

        context_list = tuple(contexts)

        if not all(isinstance(context, AgentContext) for context in context_list):
            raise TypeError("Every item in contexts must be an AgentContext.")

        batch_started_at = datetime.now(UTC)

        if not context_list:
            return ExecutionReport(
                records=(),
                started_at=batch_started_at,
                finished_at=datetime.now(UTC),
            )

        semaphore = asyncio.Semaphore(self._policy.max_concurrency)
        stop_event = asyncio.Event()

        async def execute_one(
            context: AgentContext,
        ) -> ExecutionRecord:
            """Execute one context and convert its outcome to a record."""

            queued_at = datetime.now(UTC)

            try:
                async with semaphore:
                    if stop_event.is_set():
                        now = datetime.now(UTC)

                        return ExecutionRecord(
                            context=context,
                            status=ExecutionStatus.CANCELLED,
                            error=("Batch stopped after an earlier failure."),
                            started_at=now,
                            finished_at=now,
                        )

                    started_at = datetime.now(UTC)

                    try:
                        result = await self._orchestrator.dispatch(context)

                    except asyncio.CancelledError:
                        finished_at = datetime.now(UTC)

                        return ExecutionRecord(
                            context=context,
                            status=ExecutionStatus.CANCELLED,
                            error="Execution was cancelled.",
                            started_at=started_at,
                            finished_at=finished_at,
                        )

                    except Exception as exc:  # noqa: BLE001
                        # Execution boundary: isolate agent failures per record.
                        finished_at = datetime.now(UTC)

                        record = ExecutionRecord(
                            context=context,
                            status=ExecutionStatus.ERROR,
                            error=(f"{type(exc).__name__}: {exc}"),
                            started_at=started_at,
                            finished_at=finished_at,
                        )

                        if not self._policy.continue_on_error:
                            stop_event.set()

                        return record

                    finished_at = datetime.now(UTC)

                    status = (
                        ExecutionStatus.SUCCESS
                        if result.is_success
                        else ExecutionStatus.FAILURE
                    )

                    record = ExecutionRecord(
                        context=context,
                        status=status,
                        result=result,
                        started_at=started_at,
                        finished_at=finished_at,
                    )

                    if (
                        status is ExecutionStatus.FAILURE
                        and not self._policy.continue_on_error
                    ):
                        stop_event.set()

                    return record

            except asyncio.CancelledError:
                finished_at = datetime.now(UTC)

                return ExecutionRecord(
                    context=context,
                    status=ExecutionStatus.CANCELLED,
                    error="Execution was cancelled before completion.",
                    started_at=queued_at,
                    finished_at=finished_at,
                )

        tasks = [
            asyncio.create_task(
                execute_one(context),
                name=f"agent-execution-{index}",
            )
            for index, context in enumerate(context_list)
        ]

        task_indices = {task: index for index, task in enumerate(tasks)}

        pending = set(tasks)
        records: dict[int, ExecutionRecord] = {}

        loop = asyncio.get_running_loop()

        deadline = (
            None
            if self._policy.batch_timeout is None
            else loop.time() + self._policy.batch_timeout
        )

        try:
            while pending:
                timeout = None if deadline is None else max(0.0, deadline - loop.time())

                done, pending = await asyncio.wait(
                    pending,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if not done:
                    pending_tasks = list(pending)

                    for task in pending_tasks:
                        task.cancel()

                    outcomes = await asyncio.gather(
                        *pending_tasks,
                        return_exceptions=True,
                    )

                    for task, outcome in zip(
                        pending_tasks,
                        outcomes,
                        strict=True,
                    ):
                        index = task_indices[task]

                        if isinstance(outcome, ExecutionRecord):
                            if outcome.status is ExecutionStatus.CANCELLED:
                                records[index] = replace(
                                    outcome, error="Batch execution timed out."
                                )
                            else:
                                records[index] = outcome
                        else:
                            context = context_list[index]
                            now = datetime.now(UTC)

                            records[index] = ExecutionRecord(
                                context=context,
                                status=ExecutionStatus.CANCELLED,
                                error="Batch execution timed out.",
                                started_at=now,
                                finished_at=now,
                            )

                    pending.clear()
                    break

                for task in done:
                    index = task_indices[task]
                    records[index] = task.result()

        except asyncio.CancelledError:
            for task in pending:
                task.cancel()

            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            raise

        batch_finished_at = datetime.now(UTC)

        ordered_records = tuple(records[index] for index in range(len(context_list)))

        return ExecutionReport(
            records=ordered_records,
            started_at=batch_started_at,
            finished_at=batch_finished_at,
        )


__all__ = ["ExecutionManager"]
