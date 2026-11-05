"""Tests for execution policies."""

from dataclasses import FrozenInstanceError

import pytest

from meltymon_ai_os.execution.policy import ExecutionPolicy


class TestExecutionPolicy:
    """Test execution policy configuration and validation."""

    def test_default_values(self) -> None:
        policy = ExecutionPolicy()

        assert policy.max_concurrency == 4
        assert policy.continue_on_error is True
        assert policy.batch_timeout is None

    def test_custom_values(self) -> None:
        policy = ExecutionPolicy(
            max_concurrency=8,
            continue_on_error=False,
            batch_timeout=30,
        )

        assert policy.max_concurrency == 8
        assert policy.continue_on_error is False
        assert policy.batch_timeout == 30.0
        assert isinstance(policy.batch_timeout, float)

    def test_policy_is_immutable(self) -> None:
        policy = ExecutionPolicy()

        with pytest.raises(FrozenInstanceError):
            policy.max_concurrency = 8  # type: ignore[misc]

    @pytest.mark.parametrize(
        "value",
        [0, -1, -10],
    )
    def test_rejects_invalid_concurrency_values(
        self,
        value: int,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionPolicy(max_concurrency=value)

    @pytest.mark.parametrize(
        "value",
        [True, False, 4.0, "4", None],
    )
    def test_rejects_non_integer_concurrency_values(
        self,
        value: object,
    ) -> None:
        with pytest.raises(TypeError):
            ExecutionPolicy(max_concurrency=value)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "value",
        [0, -1, 0.0, -5.5],
    )
    def test_rejects_non_positive_batch_timeouts(
        self,
        value: float,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionPolicy(batch_timeout=value)

    @pytest.mark.parametrize(
        "value",
        [float("inf"), float("-inf"), float("nan")],
    )
    def test_rejects_non_finite_batch_timeouts(
        self,
        value: float,
    ) -> None:
        with pytest.raises(ValueError):
            ExecutionPolicy(batch_timeout=value)

    @pytest.mark.parametrize(
        "value",
        [True, False, "30", object()],
    )
    def test_rejects_invalid_batch_timeout_types(
        self,
        value: object,
    ) -> None:
        with pytest.raises(TypeError):
            ExecutionPolicy(batch_timeout=value)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "value",
        [1, 2, 10, 100],
    )
    def test_accepts_positive_concurrency_values(
        self,
        value: int,
    ) -> None:
        policy = ExecutionPolicy(max_concurrency=value)

        assert policy.max_concurrency == value

    def test_accepts_positive_float_batch_timeout(self) -> None:
        policy = ExecutionPolicy(batch_timeout=12.5)

        assert policy.batch_timeout == 12.5

    def test_accepts_none_batch_timeout(self) -> None:
        policy = ExecutionPolicy(batch_timeout=None)

        assert policy.batch_timeout is None

    @pytest.mark.parametrize(
        "value",
        [1, 0, "yes", None],
    )
    def test_rejects_non_boolean_continue_on_error(
        self,
        value: object,
    ) -> None:
        with pytest.raises(TypeError):
            ExecutionPolicy(
                continue_on_error=value  # type: ignore[arg-type]
            )
