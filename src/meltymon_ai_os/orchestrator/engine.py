"""Asynchronous agent orchestration for MELTYMON AI OS."""

from __future__ import annotations

from meltymon_ai_os.agents.context import AgentContext
from meltymon_ai_os.agents.result import AgentResult

from .exceptions import OrchestratorError
from .registry import AgentRegistry


class Orchestrator:
    """Coordinate agent creation and execution."""

    def __init__(self, registry: AgentRegistry) -> None:
        if not isinstance(registry, AgentRegistry):
            raise TypeError("registry must be an AgentRegistry.")

        self._registry = registry

    @property
    def registry(self) -> AgentRegistry:
        """Return the associated agent registry."""
        return self._registry

    async def dispatch(self, context: AgentContext) -> AgentResult:
        """Create and execute the agent identified by the context."""

        if not isinstance(context, AgentContext):
            raise TypeError("context must be an AgentContext.")

        try:
            agent = self._registry.create(context.agent_id)
        except Exception as exc:
            raise OrchestratorError(
                f"Could not create agent '{context.agent_id}'."
            ) from exc

        try:
            result = await agent.execute(context)
        except Exception as exc:
            raise OrchestratorError(
                f"Agent '{context.agent_id}' execution failed unexpectedly."
            ) from exc

        if not isinstance(result, AgentResult):
            raise OrchestratorError(
                f"Agent '{context.agent_id}' returned an invalid result."
            )

        if result.agent_id != context.agent_id:
            raise OrchestratorError(
                "Agent result identifier does not match the context."
            )

        if result.correlation_id != context.correlation_id:
            raise OrchestratorError(
                "Agent result correlation ID does not match the context."
            )

        return result


__all__ = ["Orchestrator"]
