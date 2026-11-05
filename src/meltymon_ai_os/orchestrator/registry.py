"""Agent registry for MELTYMON AI OS."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from meltymon_ai_os.agents.base import AgentBase
from meltymon_ai_os.agents.lifecycle import AgentState

from .exceptions import (
    AgentAlreadyRegisteredError,
    AgentFactoryError,
    AgentNotRegisteredError,
)

AgentFactory = Callable[[], AgentBase]


class AgentRegistry:
    """Thread-safe registry for agent factories.

    The registry stores factories, not agent instances.

    Every call to create() invokes the registered factory.
    Factories are responsible for returning a fresh AgentBase
    instance for every invocation.
    """

    def __init__(self) -> None:
        self._factories: dict[str, AgentFactory] = {}
        self._lock = RLock()

    @staticmethod
    def _validate_agent_id(agent_id: str) -> str:
        """Validate and normalize an agent identifier."""

        if not isinstance(agent_id, str):
            raise TypeError("agent_id must be a string.")

        agent_id = agent_id.strip()

        if not agent_id:
            raise ValueError("agent_id must not be empty.")

        return agent_id

    def register(
        self,
        agent_id: str,
        factory: AgentFactory,
    ) -> None:
        """Register an agent factory."""

        agent_id = self._validate_agent_id(agent_id)

        if not callable(factory):
            raise TypeError("factory must be callable.")

        with self._lock:
            if agent_id in self._factories:
                raise AgentAlreadyRegisteredError(
                    f"Agent is already registered: {agent_id}"
                )

            self._factories[agent_id] = factory

    def unregister(self, agent_id: str) -> None:
        """Remove an agent registration."""

        agent_id = self._validate_agent_id(agent_id)

        with self._lock:
            if agent_id not in self._factories:
                raise AgentNotRegisteredError(f"Agent is not registered: {agent_id}")

            del self._factories[agent_id]

    def contains(self, agent_id: str) -> bool:
        """Check whether an agent is registered."""

        agent_id = self._validate_agent_id(agent_id)

        with self._lock:
            return agent_id in self._factories

    def get_registered_agents(self) -> tuple[str, ...]:
        """Return all registered agent IDs."""

        with self._lock:
            return tuple(sorted(self._factories))

    def create(self, agent_id: str) -> AgentBase:
        """Create a new agent instance from its registered factory."""

        agent_id = self._validate_agent_id(agent_id)

        with self._lock:
            factory = self._factories.get(agent_id)

        if factory is None:
            raise AgentNotRegisteredError(f"Agent is not registered: {agent_id}")

        try:
            agent = factory()
        except Exception as exc:
            raise AgentFactoryError(f"Factory failed for agent: {agent_id}") from exc

        if not isinstance(agent, AgentBase):
            raise AgentFactoryError(
                f"Factory for '{agent_id}' did not return an AgentBase."
            )

        if agent.agent_id != agent_id:
            raise AgentFactoryError(
                f"Factory for '{agent_id}' returned an agent "
                f"with ID '{agent.agent_id}'."
            )

        if agent.state is not AgentState.CREATED:
            raise AgentFactoryError(
                f"Factory for '{agent_id}' returned an agent "
                f"that is not in CREATED state."
            )

        return agent


__all__ = [
    "AgentFactory",
    "AgentRegistry",
]
