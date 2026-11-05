from typing import Any

import httpx

from meltymon_ai_os.backends.base import BaseBackend


class OllamaBackend(BaseBackend):
    """Asynchronous backend adapter for a local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def check_connection(self) -> bool:
        """Check whether Ollama is reachable."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(f"{self.base_url}/api/version")
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[dict[str, Any]]:
        """Return all locally available Ollama models."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = data.get("models")

        if not isinstance(models, list):
            raise ValueError(  # noqa: TRY004
                "Invalid Ollama API response: expected 'models' to be a list"
            )

        return models

    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a non-streaming response using Ollama."""
        payload = {
            **kwargs,
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def show_model(
        self,
        model: str,
    ) -> dict[str, Any]:
        """Return detailed information about an Ollama model."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"{self.base_url}/api/show",
                json={"model": model},
            )
            response.raise_for_status()
            return response.json()
