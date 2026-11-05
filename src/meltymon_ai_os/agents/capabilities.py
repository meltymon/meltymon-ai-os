"""Capability definitions and immutable capability sets for agents."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from .exceptions import AgentCapabilityError

_CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


def _normalize_capability(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Capability names must be strings.")

    name = value.strip()

    if not name:
        raise ValueError("Capability name cannot be empty.")

    if not _CAPABILITY_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid capability name: {value!r}")

    return name


@dataclass(frozen=True, slots=True)
class Capability:
    """A single named capability."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _normalize_capability(self.name),
        )


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    """An immutable collection of capabilities assigned to an agent."""

    _names: frozenset[str] = field(default_factory=frozenset)

    def __init__(
        self,
        capabilities: Iterable[str | Capability] = (),
    ) -> None:
        if isinstance(capabilities, (str, bytes)):
            raise TypeError("Pass an iterable of capabilities, not a string.")

        names = frozenset(
            _normalize_capability(item.name if isinstance(item, Capability) else item)
            for item in capabilities
        )

        object.__setattr__(self, "_names", names)

    def __contains__(self, capability: str | Capability) -> bool:
        name = (
            capability.name
            if isinstance(capability, Capability)
            else _normalize_capability(capability)
        )
        return name in self._names

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._names))

    def __len__(self) -> int:
        return len(self._names)

    def __bool__(self) -> bool:
        return bool(self._names)

    @property
    def names(self) -> frozenset[str]:
        """Return the immutable set of capability names."""
        return self._names

    def has(self, capability: str | Capability) -> bool:
        """Check whether a capability is available."""
        return capability in self

    def missing(
        self,
        required: Iterable[str | Capability],
    ) -> frozenset[str]:
        """Return required capabilities that are not available."""
        required_names = frozenset(
            _normalize_capability(item.name if isinstance(item, Capability) else item)
            for item in required
        )
        return required_names - self._names

    def require(self, capability: str | Capability) -> None:
        """Raise AgentCapabilityError if a capability is unavailable."""
        name = (
            capability.name
            if isinstance(capability, Capability)
            else _normalize_capability(capability)
        )

        if name not in self._names:
            raise AgentCapabilityError(f"Agent does not have capability: {name}")

    def require_all(
        self,
        capabilities: Iterable[str | Capability],
    ) -> None:
        """Require all specified capabilities."""
        missing = self.missing(capabilities)

        if missing:
            names = ", ".join(sorted(missing))
            raise AgentCapabilityError(
                f"Agent is missing required capabilities: {names}"
            )


__all__ = [
    "Capability",
    "CapabilitySet",
]
