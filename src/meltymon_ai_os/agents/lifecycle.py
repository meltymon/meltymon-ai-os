"""Lifecycle state management for MELTYMON AI OS agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from threading import RLock
from typing import ClassVar

from .exceptions import AgentLifecycleError


class AgentState(str, Enum):
    """Supported agent lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    """Immutable record of a lifecycle transition."""

    previous_state: AgentState
    current_state: AgentState
    timestamp: datetime
    reason: str | None = None


class AgentLifecycle:
    """Thread-safe state machine for an agent execution."""

    _TRANSITIONS: ClassVar[dict[AgentState, frozenset[AgentState]]] = {
        AgentState.CREATED: frozenset(
            {
                AgentState.INITIALIZING,
                AgentState.CANCELLED,
            }
        ),
        AgentState.INITIALIZING: frozenset(
            {
                AgentState.READY,
                AgentState.FAILED,
                AgentState.CANCELLED,
            }
        ),
        AgentState.READY: frozenset(
            {
                AgentState.RUNNING,
                AgentState.CANCELLED,
            }
        ),
        AgentState.RUNNING: frozenset(
            {
                AgentState.SUCCEEDED,
                AgentState.FAILED,
                AgentState.CANCELLED,
            }
        ),
        AgentState.SUCCEEDED: frozenset(),
        AgentState.FAILED: frozenset(),
        AgentState.CANCELLED: frozenset(),
    }

    _TERMINAL_STATES: ClassVar[frozenset[AgentState]] = frozenset(
        {
            AgentState.SUCCEEDED,
            AgentState.FAILED,
            AgentState.CANCELLED,
        }
    )

    def __init__(
        self,
        initial_state: AgentState = AgentState.CREATED,
    ) -> None:
        if not isinstance(initial_state, AgentState):
            raise TypeError("initial_state must be an AgentState.")

        if initial_state is not AgentState.CREATED:
            raise AgentLifecycleError("An agent lifecycle must start in CREATED state.")

        self._state: AgentState = initial_state
        self._history: list[LifecycleEvent] = []
        self._lock = RLock()

    @property
    def state(self) -> AgentState:
        """Return the current lifecycle state."""
        with self._lock:
            return self._state

    @property
    def history(self) -> tuple[LifecycleEvent, ...]:
        """Return an immutable snapshot of transition history."""
        with self._lock:
            return tuple(self._history)

    @property
    def is_terminal(self) -> bool:
        """Return whether the lifecycle has reached a terminal state."""
        with self._lock:
            return self._state in self._TERMINAL_STATES

    @property
    def is_active(self) -> bool:
        """Return whether the agent is currently running."""
        with self._lock:
            return self._state is AgentState.RUNNING

    def can_transition(self, target: AgentState) -> bool:
        """Check whether a transition is permitted."""
        if not isinstance(target, AgentState):
            return False

        with self._lock:
            return target in self._TRANSITIONS[self._state]

    def transition(
        self,
        target: AgentState,
        *,
        reason: str | None = None,
    ) -> LifecycleEvent:
        """Perform a valid state transition and record the event."""

        if not isinstance(target, AgentState):
            raise TypeError("target must be an AgentState.")

        if reason is not None:
            if not isinstance(reason, str):
                raise TypeError("reason must be a string or None.")

            reason = reason.strip()

            if not reason:
                raise ValueError("reason must not be empty.")

        with self._lock:
            previous = self._state

            if target not in self._TRANSITIONS[previous]:
                raise AgentLifecycleError(
                    f"Invalid lifecycle transition: {previous.value} -> {target.value}."
                )

            event = LifecycleEvent(
                previous_state=previous,
                current_state=target,
                timestamp=datetime.now(UTC),
                reason=reason,
            )

            self._state = target
            self._history.append(event)

            return event


__all__ = [
    "AgentLifecycle",
    "AgentState",
    "LifecycleEvent",
]
