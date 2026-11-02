
import pytest

from meltymon_ai_os.models.catalog import ModelCatalog


class FakeBackend:
    """Simulated backend for isolated catalog tests."""

    async def list_models(self):
        return [
            {
                "name": "gemma4:e4b",
                "size": 7500000000,
                "digest": "test-digest",
                "modified_at": "2026-11-02T12:00:00Z",
                "details": {
                    "family": "gemma4",
                    "parameter_size": "7.5B",
                    "quantization_level": "Q4_K_M",
                },
            },
            {
                "name": "qwen3:8b",
                "size": 8200000000,
                "digest": "test-digest-2",
                "details": {
                    "family": "qwen3",
                    "parameter_size": "8.2B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]

    async def show_model(self, model):
        return {
            "capabilities": [
                "completion",
                "vision",
                "tools",
                "thinking",
            ],
            "model_info": {
                "general.architecture": "gemma4",
                "gemma4.context_length": 131072,
            },
        }


@pytest.mark.asyncio
async def test_catalog_refresh():
    catalog = ModelCatalog(FakeBackend())

    models = await catalog.refresh()

    assert len(models) == 2
    assert catalog.get("gemma4:e4b") is not None
    assert catalog.get("qwen3:8b") is not None


@pytest.mark.asyncio
async def test_catalog_model_metadata():
    catalog = ModelCatalog(FakeBackend())

    await catalog.refresh()

    model = catalog.get("gemma4:e4b")

    assert model.name == "gemma4:e4b"
    assert model.family == "gemma4"
    assert model.parameter_size == "7.5B"
    assert model.quantization == "Q4_K_M"
    assert model.size_bytes == 7500000000


@pytest.mark.asyncio
async def test_catalog_get_details():
    catalog = ModelCatalog(FakeBackend())

    await catalog.refresh()

    model = await catalog.get_details("gemma4:e4b")

    assert model.supports_vision
    assert model.supports_tools
    assert model.supports_thinking
    assert model.model_info["gemma4.context_length"] == 131072
    assert model.context_length == 131072


@pytest.mark.asyncio
async def test_catalog_unknown_model():
    catalog = ModelCatalog(FakeBackend())

    await catalog.refresh()

    with pytest.raises(KeyError):
        await catalog.get_details("unknown:model")
