"""Tests for agent lifecycle state management."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from meltymon_ai_os.agents.exceptions import AgentLifecycleError
from meltymon_ai_os.agents.lifecycle import (
    AgentLifecycle,
    AgentState,
)


def test_initial_state_is_created():
    lifecycle = AgentLifecycle()

    assert lifecycle.state is AgentState.CREATED
    assert lifecycle.history == ()
    assert not lifecycle.is_terminal
    assert not lifecycle.is_active


def test_initial_state_must_be_created():
    with pytest.raises(AgentLifecycleError):
        AgentLifecycle(initial_state=AgentState.RUNNING)


def test_invalid_initial_state_type():
    with pytest.raises(TypeError):
        AgentLifecycle(initial_state="created")


def test_valid_initialization_transition():
    lifecycle = AgentLifecycle()

    event = lifecycle.transition(AgentState.INITIALIZING)

    assert lifecycle.state is AgentState.INITIALIZING
    assert event.previous_state is AgentState.CREATED
    assert event.current_state is AgentState.INITIALIZING


def test_complete_successful_lifecycle():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.RUNNING)
    lifecycle.transition(AgentState.SUCCEEDED)

    assert lifecycle.state is AgentState.SUCCEEDED
    assert lifecycle.is_terminal
    assert not lifecycle.is_active
    assert len(lifecycle.history) == 4


def test_failed_initialization():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(
        AgentState.FAILED,
        reason="Initialization failed.",
    )

    assert lifecycle.state is AgentState.FAILED
    assert lifecycle.is_terminal
    assert lifecycle.history[-1].reason == "Initialization failed."


def test_failed_execution():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.RUNNING)
    lifecycle.transition(AgentState.FAILED)

    assert lifecycle.state is AgentState.FAILED
    assert lifecycle.is_terminal


def test_cancellation_from_created():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.CANCELLED)

    assert lifecycle.state is AgentState.CANCELLED
    assert lifecycle.is_terminal


def test_cancellation_from_ready():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.CANCELLED)

    assert lifecycle.state is AgentState.CANCELLED


def test_cancellation_from_running():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.RUNNING)
    lifecycle.transition(AgentState.CANCELLED)

    assert lifecycle.state is AgentState.CANCELLED


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (AgentState.CREATED, AgentState.READY),
        (AgentState.CREATED, AgentState.RUNNING),
        (AgentState.CREATED, AgentState.SUCCEEDED),
        (AgentState.INITIALIZING, AgentState.RUNNING),
        (AgentState.READY, AgentState.SUCCEEDED),
        (AgentState.RUNNING, AgentState.INITIALIZING),
    ],
)
def test_invalid_transitions_are_rejected(start, target):
    lifecycle = AgentLifecycle()

    if start is AgentState.INITIALIZING:
        lifecycle.transition(AgentState.INITIALIZING)
    elif start is AgentState.READY:
        lifecycle.transition(AgentState.INITIALIZING)
        lifecycle.transition(AgentState.READY)
    elif start is AgentState.RUNNING:
        lifecycle.transition(AgentState.INITIALIZING)
        lifecycle.transition(AgentState.READY)
        lifecycle.transition(AgentState.RUNNING)

    with pytest.raises(AgentLifecycleError):
        lifecycle.transition(target)


@pytest.mark.parametrize(
    "terminal_state",
    [
        AgentState.SUCCEEDED,
        AgentState.FAILED,
        AgentState.CANCELLED,
    ],
)
def test_terminal_states_cannot_be_left(terminal_state):
    lifecycle = AgentLifecycle()

    if terminal_state is AgentState.CANCELLED:
        lifecycle.transition(AgentState.CANCELLED)
    else:
        lifecycle.transition(AgentState.INITIALIZING)

        if terminal_state is AgentState.SUCCEEDED:
            lifecycle.transition(AgentState.READY)
            lifecycle.transition(AgentState.RUNNING)

        lifecycle.transition(terminal_state)

    for target in AgentState:
        assert not lifecycle.can_transition(target)

        with pytest.raises(AgentLifecycleError):
            lifecycle.transition(target)


def test_can_transition():
    lifecycle = AgentLifecycle()

    assert lifecycle.can_transition(AgentState.INITIALIZING)
    assert lifecycle.can_transition(AgentState.CANCELLED)
    assert not lifecycle.can_transition(AgentState.RUNNING)


def test_can_transition_rejects_invalid_type():
    lifecycle = AgentLifecycle()

    assert not lifecycle.can_transition("running")


def test_transition_rejects_invalid_type():
    lifecycle = AgentLifecycle()

    with pytest.raises(TypeError):
        lifecycle.transition("running")


def test_transition_reason_is_normalized():
    lifecycle = AgentLifecycle()

    event = lifecycle.transition(
        AgentState.INITIALIZING,
        reason="  Startup  ",
    )

    assert event.reason == "Startup"


def test_empty_reason_is_rejected():
    lifecycle = AgentLifecycle()

    with pytest.raises(ValueError):
        lifecycle.transition(
            AgentState.INITIALIZING,
            reason="   ",
        )


def test_non_string_reason_is_rejected():
    lifecycle = AgentLifecycle()

    with pytest.raises(TypeError):
        lifecycle.transition(
            AgentState.INITIALIZING,
            reason=123,
        )


def test_event_timestamp_is_utc():
    lifecycle = AgentLifecycle()

    event = lifecycle.transition(AgentState.INITIALIZING)

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo is UTC


def test_history_is_immutable():
    lifecycle = AgentLifecycle()
    lifecycle.transition(AgentState.INITIALIZING)

    history = lifecycle.history

    assert isinstance(history, tuple)

    with pytest.raises(AttributeError):
        history.append(None)


def test_events_are_immutable():
    lifecycle = AgentLifecycle()
    event = lifecycle.transition(AgentState.INITIALIZING)

    with pytest.raises(AttributeError):
        event.reason = "modified"


def test_history_preserves_transition_order():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.RUNNING)

    history = lifecycle.history

    assert [event.current_state for event in history] == [
        AgentState.INITIALIZING,
        AgentState.READY,
        AgentState.RUNNING,
    ]


def test_event_records_previous_state():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    event = lifecycle.transition(AgentState.READY)

    assert event.previous_state is AgentState.INITIALIZING
    assert event.current_state is AgentState.READY


def test_is_active_only_while_running():
    lifecycle = AgentLifecycle()

    assert not lifecycle.is_active

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)
    lifecycle.transition(AgentState.RUNNING)

    assert lifecycle.is_active

    lifecycle.transition(AgentState.SUCCEEDED)

    assert not lifecycle.is_active


def test_concurrent_transitions_preserve_valid_state():
    lifecycle = AgentLifecycle()

    lifecycle.transition(AgentState.INITIALIZING)
    lifecycle.transition(AgentState.READY)

    def attempt_transition():
        try:
            lifecycle.transition(AgentState.RUNNING)
            return True
        except AgentLifecycleError:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: attempt_transition(),
                range(8),
            )
        )

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert lifecycle.state is AgentState.RUNNING
    assert len(lifecycle.history) == 3
