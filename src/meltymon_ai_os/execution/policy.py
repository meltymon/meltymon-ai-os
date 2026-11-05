"""Execution policies for MELTYMON AI OS."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Immutable configuration for a batch execution.

    Attributes:
        max_concurrency:
            Maximum number of agent executions running simultaneously.
        continue_on_error:
            Whether remaining executions should continue after a failure.
        batch_timeout:
            Optional maximum duration for the complete batch in seconds.
    """

    max_concurrency: int = 4
    continue_on_error: bool = True
    batch_timeout: float | None = None

    def __post_init__(self) -> None:
        """Validate all execution policy settings."""

        if isinstance(self.max_concurrency, bool) or not isinstance(
            self.max_concurrency, int
        ):
            raise TypeError("max_concurrency must be an integer.")

        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1.")

        if not isinstance(self.continue_on_error, bool):
            raise TypeError("continue_on_error must be a boolean.")

        if self.batch_timeout is not None:
            if isinstance(self.batch_timeout, bool) or not isinstance(
                self.batch_timeout, (int, float)
            ):
                raise TypeError("batch_timeout must be a number or None.")

            if not math.isfinite(self.batch_timeout):
                raise ValueError("batch_timeout must be finite.")

            if self.batch_timeout <= 0:
                raise ValueError("batch_timeout must be greater than zero.")

            object.__setattr__(
                self,
                "batch_timeout",
                float(self.batch_timeout),
            )


__all__ = ["ExecutionPolicy"]
