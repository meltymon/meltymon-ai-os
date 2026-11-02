
from abc import ABC, abstractmethod
from typing import Any


class BaseBackend(ABC):
    """Abstract interface for AI inference backends."""

    @abstractmethod
    async def check_connection(self) -> bool:
        """Check whether the backend is reachable."""
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """Return the models available on this backend."""
        raise NotImplementedError

    @abstractmethod
    async def show_model(self, model: str) -> dict[str, Any]:
        """Return detailed information about a specific model."""
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a response using the selected model."""
        raise NotImplementedError
