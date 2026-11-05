"""Tests for the public execution package API."""

from meltymon_ai_os import execution
from meltymon_ai_os.execution.manager import ExecutionManager
from meltymon_ai_os.execution.policy import ExecutionPolicy
from meltymon_ai_os.execution.report import (
    ExecutionRecord,
    ExecutionReport,
    ExecutionStatus,
)


def test_public_exports_are_available() -> None:
    """Verify that all public execution classes are importable."""

    assert execution.ExecutionManager is ExecutionManager
    assert execution.ExecutionPolicy is ExecutionPolicy
    assert execution.ExecutionRecord is ExecutionRecord
    assert execution.ExecutionReport is ExecutionReport
    assert execution.ExecutionStatus is ExecutionStatus


def test_all_exports_exist() -> None:
    """Verify that every declared public export exists."""

    for name in execution.__all__:
        assert hasattr(execution, name)


def test_public_exports_contain_expected_names() -> None:
    """Verify the complete public API."""

    assert set(execution.__all__) == {
        "ExecutionManager",
        "ExecutionPolicy",
        "ExecutionRecord",
        "ExecutionReport",
        "ExecutionStatus",
    }


def test_public_exports_contain_no_duplicates() -> None:
    """Verify that public exports are unique."""

    assert len(execution.__all__) == len(set(execution.__all__))


def test_public_exports_are_classes() -> None:
    """Verify that all public exports are classes."""

    for name in execution.__all__:
        assert isinstance(getattr(execution, name), type)
