
from typing import Any

from meltymon_ai_os.backends.base import BaseBackend
from meltymon_ai_os.models.metadata import ModelMetadata


class ModelCatalog:
    """Collect and normalize model metadata from an AI backend."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend
        self.models: dict[str, ModelMetadata] = {}

    @staticmethod
    def _extract_context_length(
        model_info: dict[str, Any],
    ) -> int | None:
        """Extract a known context length from model information."""

        for key, value in model_info.items():
            if key == "context_length" or key.endswith(
                ".context_length"
            ):
                if (
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and value > 0
                ):
                    return value

        return None

    async def refresh(self) -> list[ModelMetadata]:
        """Discover installed models and collect their metadata."""

        raw_models = await self.backend.list_models()
        discovered: dict[str, ModelMetadata] = {}

        for raw_model in raw_models:
            name = raw_model.get("name")

            if not isinstance(name, str) or not name.strip():
                continue

            details = raw_model.get("details") or {}

            if not isinstance(details, dict):
                details = {}

            metadata = ModelMetadata(
                name=name,
                backend=self.backend.__class__.__name__,
                family=details.get("family"),
                parameter_size=details.get("parameter_size"),
                quantization=details.get("quantization_level"),
                size_bytes=raw_model.get("size"),
                modified_at=raw_model.get("modified_at"),
                digest=raw_model.get("digest"),
                details=details,
            )

            discovered[name] = metadata

        self.models = discovered

        return list(self.models.values())

    async def get_details(self, model_name: str) -> ModelMetadata:
        """Enrich one model with detailed backend information."""

        if model_name not in self.models:
            raise KeyError(f"Model not found in catalog: {model_name}")

        raw_info = await self.backend.show_model(model_name)

        capabilities = raw_info.get("capabilities") or []
        model_info = raw_info.get("model_info") or {}

        if not isinstance(capabilities, list):
            capabilities = []

        if not isinstance(model_info, dict):
            model_info = {}

        capabilities = [
            capability
            for capability in capabilities
            if isinstance(capability, str)
        ]

        self.models[model_name] = self.models[model_name].model_copy(
            update={
                "capabilities": capabilities,
                "model_info": model_info,
                "context_length": self._extract_context_length(
                    model_info
                ),
            }
        )

        return self.models[model_name]

    def get(self, model_name: str) -> ModelMetadata | None:
        """Return cached metadata for a model."""

        return self.models.get(model_name)
