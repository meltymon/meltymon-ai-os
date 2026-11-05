"""Abstract base class for MELTYMON AI OS agents."""

from __future__ import annotations

import asyncio
import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .capabilities import Capability, CapabilitySet
from .context import AgentContext
from .exceptions import (
    AgentConfigurationError,
    AgentLifecycleError,
    AgentTimeoutError,
)
from .lifecycle import AgentLifecycle, AgentState
from .result import AgentResult


class AgentBase(ABC):
    """Common execution framework for all MELTYMON AI OS agents.

    Agents declare their capabilities but never grant themselves
    permissions or approve operations.

    Each instance represents one execution lifecycle. An agent instance
    cannot be executed more than once.
    """

    def __init__(
        self,
        *,
        agent_id: str,
        capabilities: CapabilitySet | Iterable[str | Capability] = (),
        timeout: float | None = None,
    ) -> None:
        if not isinstance(agent_id, str):
            raise TypeError("agent_id must be a string.")

        agent_id = agent_id.strip()

        if not agent_id:
            raise ValueError("agent_id must not be empty.")

        if isinstance(capabilities, CapabilitySet):
            capability_set = capabilities
        else:
            capability_set = CapabilitySet(capabilities)

        if timeout is not None:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise TypeError("timeout must be a number or None.")

            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("timeout must be a positive finite number.")

            timeout = float(timeout)

        self._agent_id = agent_id
        self._capabilities = capability_set
        self._timeout = timeout

        self._lifecycle = AgentLifecycle()
        self._execution_lock = asyncio.Lock()

    @property
    def agent_id(self) -> str:
        """Return the agent identifier."""
        return self._agent_id

    @property
    def capabilities(self) -> CapabilitySet:
        """Return the immutable set of declared capabilities."""
        return self._capabilities

    @property
    def lifecycle(self) -> AgentLifecycle:
        """Return the agent lifecycle manager."""
        return self._lifecycle

    @property
    def state(self) -> AgentState:
        """Return the current lifecycle state."""
        return self._lifecycle.state

    @property
    def timeout(self) -> float | None:
        """Return the configured execution timeout."""
        return self._timeout

    async def execute(self, context: AgentContext) -> AgentResult:
        """Initialize and execute the agent exactly once.

        Regular exceptions are converted into failure results.
        Configured execution timeouts become AgentTimeoutError results.
        External cancellation is recorded and re-raised.
        """
        if not isinstance(context, AgentContext):
            raise TypeError("context must be an AgentContext.")

        if context.agent_id != self._agent_id:
            raise AgentConfigurationError("Context agent_id does not match this agent.")

        async with self._execution_lock:
            if self._lifecycle.state is not AgentState.CREATED:
                raise AgentLifecycleError(
                    "An agent instance can only be executed once."
                )

            timeout_scope = None

            try:
                if self._timeout is None:
                    output = await self._run(context)
                else:
                    async with asyncio.timeout(self._timeout) as timeout_scope:
                        output = await self._run(context)

                result = AgentResult.success(
                    agent_id=self._agent_id,
                    correlation_id=context.correlation_id,
                    output=output,
                )

                self._lifecycle.transition(AgentState.SUCCEEDED)

                return result

            except TimeoutError as exc:
                if timeout_scope is None or not timeout_scope.expired():
                    error_message = str(exc).strip() or type(exc).__name__

                    self._transition_to_terminal(
                        AgentState.FAILED,
                        error_message,
                    )

                    return AgentResult.failure(
                        agent_id=self._agent_id,
                        correlation_id=context.correlation_id,
                        error=error_message,
                        metadata={
                            "exception_type": type(exc).__name__,
                        },
                    )

                error = AgentTimeoutError(
                    f"Agent execution exceeded its timeout of {self._timeout} seconds."
                )

                self._transition_to_terminal(
                    AgentState.FAILED,
                    str(error),
                )

                return AgentResult.failure(
                    agent_id=self._agent_id,
                    correlation_id=context.correlation_id,
                    error=str(error),
                    metadata={
                        "exception_type": type(error).__name__,
                    },
                )

            except asyncio.CancelledError:
                self._transition_to_terminal(
                    AgentState.CANCELLED,
                    "Execution cancelled.",
                )
                raise

            except Exception as exc:  # noqa: BLE001
                # Agent boundary: convert unexpected failures into results.
                error_message = str(exc).strip() or type(exc).__name__

                self._transition_to_terminal(
                    AgentState.FAILED,
                    error_message,
                )

                return AgentResult.failure(
                    agent_id=self._agent_id,
                    correlation_id=context.correlation_id,
                    error=error_message,
                    metadata={
                        "exception_type": type(exc).__name__,
                    },
                )

    async def _run(self, context: AgentContext) -> Any:
        """Execute the complete initialization and execution sequence."""
        self._lifecycle.transition(AgentState.INITIALIZING)

        await self._initialize(context)

        self._lifecycle.transition(AgentState.READY)
        self._lifecycle.transition(AgentState.RUNNING)

        return await self._execute(context)

    def _transition_to_terminal(
        self,
        state: AgentState,
        reason: str,
    ) -> None:
        """Move the lifecycle into a terminal state when possible."""
        if not self._lifecycle.is_terminal:
            self._lifecycle.transition(state, reason=reason)

    async def _initialize(self, context: AgentContext) -> None:
        """Optional asynchronous initialization hook.

        Subclasses may override this method.
        The default implementation performs no initialization.
        """

    @abstractmethod
    async def _execute(self, context: AgentContext) -> Any:
        """Implement the agent-specific execution logic.

        Capability checks can be performed through
        self.capabilities.require(...).

        This does not grant permission to perform an operation.
        Authorization and approval remain the responsibility
        of the orchestration and security layers.
        """


__all__ = ["AgentBase"]
