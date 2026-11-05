"""Tests for execution reports and records."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.result import AgentResult
from meltymon_ai_os.execution.report import (
    ExecutionRecord,
    ExecutionReport,
    ExecutionStatus,
)


@pytest.fixture
def timestamps() -> tuple[datetime, datetime]:
    started = datetime(2026, 11, 3, 12, 0, 0, tzinfo=UTC)
    finished = started + timedelta(seconds=10)
    return started, finished


@pytest.fixture
def context() -> AgentContext:
    return AgentContext(
        agent_id="test-agent",
        correlation_id="test-correlation",
    )


@pytest.fixture
def successful_result(context: AgentContext) -> AgentResult:
    return AgentResult.success(
        agent_id=context.agent_id,
        correlation_id=context.correlation_id,
        output={"message": "success"},
    )


@pytest.fixture
def failed_result(context: AgentContext) -> AgentResult:
    return AgentResult.failure(
        agent_id=context.agent_id,
        correlation_id=context.correlation_id,
        error="Agent execution failed.",
    )


class TestExecutionRecord:
    """Test individual execution records."""

    def test_success_record(
        self,
        context: AgentContext,
        successful_result: AgentResult,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.SUCCESS,
            result=successful_result,
            started_at=started,
            finished_at=finished,
        )

        assert record.status is ExecutionStatus.SUCCESS
        assert record.result is successful_result
        assert record.error is None
        assert record.duration == 10.0

    def test_failure_record(
        self,
        context: AgentContext,
        failed_result: AgentResult,
    ) -> None:
        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.FAILURE,
            result=failed_result,
        )

        assert record.status is ExecutionStatus.FAILURE
        assert record.result is failed_result

    def test_error_record(
        self,
        context: AgentContext,
    ) -> None:
        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.ERROR,
            error="Unexpected orchestration error.",
        )

        assert record.status is ExecutionStatus.ERROR
        assert record.error == "Unexpected orchestration error."
        assert record.result is None

    def test_cancelled_record(
        self,
        context: AgentContext,
    ) -> None:
        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.CANCELLED,
            error="Execution cancelled.",
        )

        assert record.status is ExecutionStatus.CANCELLED
        assert record.error == "Execution cancelled."

    def test_record_is_immutable(
        self,
        context: AgentContext,
        successful_result: AgentResult,
    ) -> None:
        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.SUCCESS,
            result=successful_result,
        )

        with pytest.raises(FrozenInstanceError):
            record.status = ExecutionStatus.FAILURE  # type: ignore[misc]

    def test_rejects_invalid_context(self) -> None:
        with pytest.raises(TypeError):
            ExecutionRecord(
                context="invalid",  # type: ignore[arg-type]
                status=ExecutionStatus.ERROR,
                error="Failure.",
            )

    def test_rejects_invalid_status(
        self,
        context: AgentContext,
    ) -> None:
        with pytest.raises(TypeError):
            ExecutionRecord(
                context=context,
                status="success",  # type: ignore[arg-type]
                result=None,
            )

    def test_success_requires_successful_result(
        self,
        context: AgentContext,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.SUCCESS,
            )

    def test_failure_requires_failed_result(
        self,
        context: AgentContext,
        successful_result: AgentResult,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.FAILURE,
                result=successful_result,
            )

    def test_error_requires_description(
        self,
        context: AgentContext,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.ERROR,
                error=" ",
            )

    def test_rejects_mismatched_agent_id(
        self,
        context: AgentContext,
    ) -> None:
        result = AgentResult.success(
            agent_id="another-agent",
            correlation_id=context.correlation_id,
        )

        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.SUCCESS,
                result=result,
            )

    def test_rejects_mismatched_correlation_id(
        self,
        context: AgentContext,
    ) -> None:
        result = AgentResult.success(
            agent_id=context.agent_id,
            correlation_id="another-correlation",
        )

        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.SUCCESS,
                result=result,
            )

    def test_rejects_naive_datetime(
        self,
        context: AgentContext,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.ERROR,
                error="Failure.",
                started_at=datetime(2026, 11, 3, 12, 0, 0),
            )

    def test_rejects_finished_before_started(
        self,
        context: AgentContext,
    ) -> None:
        started = datetime(2026, 11, 3, 12, 0, 0, tzinfo=UTC)
        finished = started - timedelta(seconds=1)

        with pytest.raises(ValueError):
            ExecutionRecord(
                context=context,
                status=ExecutionStatus.ERROR,
                error="Failure.",
                started_at=started,
                finished_at=finished,
            )


class TestExecutionReport:
    """Test aggregate execution reports."""

    def test_empty_report(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        report = ExecutionReport(
            records=(),
            started_at=started,
            finished_at=finished,
        )

        assert report.total == 0
        assert report.succeeded == 0
        assert report.failed == 0
        assert report.errors == 0
        assert report.cancelled == 0
        assert report.duration == 10.0
        assert report.is_success is False
        assert report.has_failures is False
        assert report.has_cancellations is False

    def test_aggregates_all_execution_statuses(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        contexts = [AgentContext(agent_id=f"agent-{index}") for index in range(4)]

        results = [
            AgentResult.success(
                agent_id=contexts[0].agent_id,
                correlation_id=contexts[0].correlation_id,
            ),
            AgentResult.failure(
                agent_id=contexts[1].agent_id,
                correlation_id=contexts[1].correlation_id,
                error="Agent failure.",
            ),
        ]

        records = (
            ExecutionRecord(
                context=contexts[0],
                status=ExecutionStatus.SUCCESS,
                result=results[0],
                started_at=started,
                finished_at=finished,
            ),
            ExecutionRecord(
                context=contexts[1],
                status=ExecutionStatus.FAILURE,
                result=results[1],
                started_at=started,
                finished_at=finished,
            ),
            ExecutionRecord(
                context=contexts[2],
                status=ExecutionStatus.ERROR,
                error="Unexpected error.",
                started_at=started,
                finished_at=finished,
            ),
            ExecutionRecord(
                context=contexts[3],
                status=ExecutionStatus.CANCELLED,
                started_at=started,
                finished_at=finished,
            ),
        )

        report = ExecutionReport(
            records=records,
            started_at=started,
            finished_at=finished,
        )

        assert report.total == 4
        assert report.succeeded == 1
        assert report.failed == 1
        assert report.errors == 1
        assert report.cancelled == 1
        assert report.has_failures is True
        assert report.has_cancellations is True
        assert report.is_success is False

    def test_all_successful(
        self,
        context: AgentContext,
        successful_result: AgentResult,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.SUCCESS,
            result=successful_result,
            started_at=started,
            finished_at=finished,
        )

        report = ExecutionReport(
            records=(record,),
            started_at=started,
            finished_at=finished,
        )

        assert report.is_success is True
        assert report.succeeded == 1
        assert report.has_failures is False

    def test_report_is_immutable(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        report = ExecutionReport(
            records=(),
            started_at=started,
            finished_at=finished,
        )

        with pytest.raises(FrozenInstanceError):
            report.execution_id = "changed"  # type: ignore[misc]

    def test_rejects_list_instead_of_tuple(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        with pytest.raises(TypeError):
            ExecutionReport(
                records=[],  # type: ignore[arg-type]
                started_at=started,
                finished_at=finished,
            )

    def test_rejects_invalid_record(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        with pytest.raises(TypeError):
            ExecutionReport(
                records=("invalid",),  # type: ignore[arg-type]
                started_at=started,
                finished_at=finished,
            )

    def test_rejects_finished_before_started(self) -> None:
        started = datetime(2026, 11, 3, 12, 0, 0, tzinfo=UTC)
        finished = started - timedelta(seconds=1)

        with pytest.raises(ValueError):
            ExecutionReport(
                records=(),
                started_at=started,
                finished_at=finished,
            )

    def test_rejects_empty_execution_id(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        with pytest.raises(ValueError):
            ExecutionReport(
                records=(),
                started_at=started,
                finished_at=finished,
                execution_id=" ",
            )

    def test_normalizes_execution_id(
        self,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        report = ExecutionReport(
            records=(),
            started_at=started,
            finished_at=finished,
            execution_id="  batch-123  ",
        )

        assert report.execution_id == "batch-123"

    def test_rejects_record_starting_before_report(
        self,
        context: AgentContext,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.ERROR,
            error="Failure.",
            started_at=started - timedelta(seconds=1),
            finished_at=finished,
        )

        with pytest.raises(ValueError):
            ExecutionReport(
                records=(record,),
                started_at=started,
                finished_at=finished,
            )

    def test_rejects_record_finishing_after_report(
        self,
        context: AgentContext,
        timestamps: tuple[datetime, datetime],
    ) -> None:
        started, finished = timestamps

        record = ExecutionRecord(
            context=context,
            status=ExecutionStatus.ERROR,
            error="Failure.",
            started_at=started,
            finished_at=finished + timedelta(seconds=1),
        )

        with pytest.raises(ValueError):
            ExecutionReport(
                records=(record,),
                started_at=started,
                finished_at=finished,
            )
