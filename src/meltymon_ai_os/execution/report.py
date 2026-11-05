"""Execution reports and records for MELTYMON AI OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.result import AgentResult


class ExecutionStatus(str, Enum):
    """Possible outcomes of an individual execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    CANCELLED = "cancelled"


def _validate_datetime(value: datetime, field_name: str) -> datetime:
    """Validate and normalize a timezone-aware datetime."""

    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware.")

    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Immutable record describing one agent execution."""

    context: AgentContext
    status: ExecutionStatus
    result: AgentResult | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate the execution record."""

        if not isinstance(self.context, AgentContext):
            raise TypeError("context must be an AgentContext.")

        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("status must be an ExecutionStatus.")

        if self.result is not None:
            if not isinstance(self.result, AgentResult):
                raise TypeError("result must be an AgentResult or None.")

            if self.result.agent_id != self.context.agent_id:
                raise ValueError("Result agent_id does not match the context.")

            if self.result.correlation_id != self.context.correlation_id:
                raise ValueError("Result correlation_id does not match the context.")

        if self.status is ExecutionStatus.SUCCESS:
            if self.result is None or not self.result.is_success:
                raise ValueError("SUCCESS requires a successful AgentResult.")

            if self.error is not None:
                raise ValueError("A successful execution cannot contain an error.")

        elif self.status is ExecutionStatus.FAILURE:
            if self.result is None or not self.result.is_failure:
                raise ValueError("FAILURE requires a failed AgentResult.")

        elif self.status is ExecutionStatus.ERROR:
            if not isinstance(self.error, str) or not self.error.strip():
                raise ValueError("ERROR requires a non-empty error description.")

        elif self.status is ExecutionStatus.CANCELLED:
            if self.error is not None and not isinstance(self.error, str):
                raise TypeError("error must be a string or None.")

        if self.error is not None:
            if not isinstance(self.error, str):
                raise TypeError("error must be a string or None.")

            object.__setattr__(self, "error", self.error.strip())

        started_at = _validate_datetime(
            self.started_at,
            "started_at",
        )
        finished_at = _validate_datetime(
            self.finished_at,
            "finished_at",
        )

        if finished_at < started_at:
            raise ValueError("finished_at cannot be earlier than started_at.")

        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "finished_at", finished_at)

    @property
    def duration(self) -> float:
        """Return execution duration in seconds."""

        return (self.finished_at - self.started_at).total_seconds()


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Immutable aggregate report for a batch execution."""

    records: tuple[ExecutionRecord, ...]
    started_at: datetime
    finished_at: datetime
    execution_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate and normalize the aggregate report."""

        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple.")

        if not all(isinstance(record, ExecutionRecord) for record in self.records):
            raise TypeError("Every record must be an ExecutionRecord.")

        if not isinstance(self.execution_id, str):
            raise TypeError("execution_id must be a string.")

        execution_id = self.execution_id.strip()

        if not execution_id:
            raise ValueError("execution_id must not be empty.")

        started_at = _validate_datetime(
            self.started_at,
            "started_at",
        )
        finished_at = _validate_datetime(
            self.finished_at,
            "finished_at",
        )

        if finished_at < started_at:
            raise ValueError("finished_at cannot be earlier than started_at.")

        for record in self.records:
            if record.started_at < started_at:
                raise ValueError("A record cannot start before the report.")

            if record.finished_at > finished_at:
                raise ValueError("A record cannot finish after the report.")

        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "finished_at", finished_at)

    @property
    def total(self) -> int:
        """Return the number of execution records."""

        return len(self.records)

    @property
    def succeeded(self) -> int:
        """Return the number of successful executions."""

        return sum(record.status is ExecutionStatus.SUCCESS for record in self.records)

    @property
    def failed(self) -> int:
        """Return the number of regular agent failures."""

        return sum(record.status is ExecutionStatus.FAILURE for record in self.records)

    @property
    def errors(self) -> int:
        """Return the number of unexpected execution errors."""

        return sum(record.status is ExecutionStatus.ERROR for record in self.records)

    @property
    def cancelled(self) -> int:
        """Return the number of cancelled executions."""

        return sum(
            record.status is ExecutionStatus.CANCELLED for record in self.records
        )

    @property
    def duration(self) -> float:
        """Return total batch duration in seconds."""

        return (self.finished_at - self.started_at).total_seconds()

    @property
    def is_success(self) -> bool:
        """Return whether every execution succeeded."""

        return self.total > 0 and self.succeeded == self.total

    @property
    def has_failures(self) -> bool:
        """Return whether any execution failed or raised an error."""

        return self.failed > 0 or self.errors > 0

    @property
    def has_cancellations(self) -> bool:
        """Return whether any execution was cancelled."""

        return self.cancelled > 0


__all__ = [
    "ExecutionRecord",
    "ExecutionReport",
    "ExecutionStatus",
]
