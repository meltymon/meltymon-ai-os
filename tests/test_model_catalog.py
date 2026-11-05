import pytest

from meltymon_ai_os.models.catalog import ModelCatalog


class FakeBackend:
    """Simulated backend for isolated catalog tests."""

    def __init__(
        self,
        models=None,
        model_details=None,
        list_error=None,
        show_error=None,
    ):
        self.models = (
            models
            if models is not None
            else [
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
        )
        self.model_details = (
            model_details
            if model_details is not None
            else {
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
        )
        self.list_error = list_error
        self.show_error = show_error

    async def list_models(self):
        if self.list_error is not None:
            raise self.list_error

        return self.models

    async def show_model(self, model):
        if self.show_error is not None:
            raise self.show_error

        return self.model_details


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

    assert model is not None
    assert model.name == "gemma4:e4b"
    assert model.family == "gemma4"
    assert model.parameter_size == "7.5B"
    assert model.quantization == "Q4_K_M"
    assert model.size_bytes == 7500000000
    assert model.digest == "test-digest"


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

    with pytest.raises(KeyError, match="unknown:model"):
        await catalog.get_details("unknown:model")


@pytest.mark.asyncio
async def test_catalog_refresh_empty_backend():
    catalog = ModelCatalog(FakeBackend(models=[]))

    models = await catalog.refresh()

    assert models == []
    assert catalog.models == {}


@pytest.mark.asyncio
async def test_catalog_refresh_ignores_invalid_names():
    catalog = ModelCatalog(
        FakeBackend(
            models=[
                {"name": None},
                {"name": ""},
                {"name": "   "},
                {"name": 123},
                {"size": 1000},
                {"name": "valid:model"},
            ]
        )
    )

    models = await catalog.refresh()

    assert len(models) == 1
    assert models[0].name == "valid:model"


@pytest.mark.asyncio
async def test_catalog_refresh_ignores_invalid_details():
    catalog = ModelCatalog(
        FakeBackend(
            models=[
                {"name": "model:none", "details": None},
                {"name": "model:string", "details": "invalid"},
                {"name": "model:list", "details": ["invalid"]},
            ]
        )
    )

    models = await catalog.refresh()

    assert len(models) == 3
    assert all(model.details == {} for model in models)


@pytest.mark.asyncio
async def test_catalog_refresh_replaces_previous_models():
    backend = FakeBackend()
    catalog = ModelCatalog(backend)

    await catalog.refresh()

    backend.models = [{"name": "new:model"}]

    models = await catalog.refresh()

    assert len(models) == 1
    assert models[0].name == "new:model"
    assert catalog.get("gemma4:e4b") is None


@pytest.mark.asyncio
async def test_catalog_refresh_duplicate_name_uses_last_entry():
    catalog = ModelCatalog(
        FakeBackend(
            models=[
                {
                    "name": "same:model",
                    "details": {"family": "first"},
                },
                {
                    "name": "same:model",
                    "details": {"family": "second"},
                },
            ]
        )
    )

    models = await catalog.refresh()

    assert len(models) == 1
    assert models[0].family == "second"


@pytest.mark.asyncio
async def test_catalog_refresh_preserves_backend_name():
    catalog = ModelCatalog(FakeBackend())

    await catalog.refresh()

    model = catalog.get("gemma4:e4b")

    assert model is not None
    assert model.backend == "FakeBackend"


@pytest.mark.asyncio
async def test_catalog_get_returns_none_for_unknown_model():
    catalog = ModelCatalog(FakeBackend())

    assert catalog.get("missing:model") is None


@pytest.mark.asyncio
async def test_catalog_extract_direct_context_length():
    result = ModelCatalog._extract_context_length({"context_length": 8192})

    assert result == 8192


@pytest.mark.asyncio
async def test_catalog_extract_namespaced_context_length():
    result = ModelCatalog._extract_context_length({"gemma4.context_length": 131072})

    assert result == 131072


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        None,
        0,
        -1,
        True,
        False,
        "8192",
        8192.0,
        [],
        {},
    ],
)
async def test_catalog_extract_rejects_invalid_context_length(value):
    result = ModelCatalog._extract_context_length({"context_length": value})

    assert result is None


def test_catalog_extract_ignores_unrelated_keys():
    result = ModelCatalog._extract_context_length(
        {
            "architecture": "gemma4",
            "layers": 32,
            "other.context_length": "8192",
        }
    )

    assert result is None


def test_catalog_extract_uses_first_valid_context_length():
    result = ModelCatalog._extract_context_length(
        {
            "context_length": 0,
            "gemma4.context_length": 131072,
            "qwen.context_length": 32768,
        }
    )

    assert result == 131072


@pytest.mark.asyncio
async def test_catalog_get_details_filters_invalid_capabilities():
    catalog = ModelCatalog(
        FakeBackend(
            model_details={
                "capabilities": [
                    "vision",
                    123,
                    None,
                    "tools",
                    True,
                    "thinking",
                ],
                "model_info": {},
            }
        )
    )

    await catalog.refresh()
    model = await catalog.get_details("gemma4:e4b")

    assert model.capabilities == ["vision", "tools", "thinking"]
    assert model.supports_vision
    assert model.supports_tools
    assert model.supports_thinking


@pytest.mark.asyncio
async def test_catalog_get_details_normalizes_invalid_capabilities():
    catalog = ModelCatalog(
        FakeBackend(
            model_details={
                "capabilities": "vision",
                "model_info": {},
            }
        )
    )

    await catalog.refresh()
    model = await catalog.get_details("gemma4:e4b")

    assert model.capabilities == []


@pytest.mark.asyncio
async def test_catalog_get_details_normalizes_invalid_model_info():
    catalog = ModelCatalog(
        FakeBackend(
            model_details={
                "capabilities": [],
                "model_info": ["invalid"],
            }
        )
    )

    await catalog.refresh()
    model = await catalog.get_details("gemma4:e4b")

    assert model.model_info == {}
    assert model.context_length is None


@pytest.mark.asyncio
async def test_catalog_get_details_missing_fields():
    catalog = ModelCatalog(FakeBackend(model_details={}))

    await catalog.refresh()
    model = await catalog.get_details("gemma4:e4b")

    assert model.capabilities == []
    assert model.model_info == {}
    assert model.context_length is None


@pytest.mark.asyncio
async def test_catalog_get_details_preserves_existing_metadata():
    catalog = ModelCatalog(FakeBackend())

    await catalog.refresh()
    model = await catalog.get_details("gemma4:e4b")

    assert model.name == "gemma4:e4b"
    assert model.family == "gemma4"
    assert model.parameter_size == "7.5B"
    assert model.size_bytes == 7500000000


@pytest.mark.asyncio
async def test_catalog_list_models_backend_error_propagates():
    error = RuntimeError("Backend unavailable")
    catalog = ModelCatalog(FakeBackend(list_error=error))

    with pytest.raises(RuntimeError, match="Backend unavailable"):
        await catalog.refresh()


@pytest.mark.asyncio
async def test_catalog_show_model_backend_error_propagates():
    error = RuntimeError("Model lookup failed")
    catalog = ModelCatalog(FakeBackend(show_error=error))

    await catalog.refresh()

    with pytest.raises(RuntimeError, match="Model lookup failed"):
        await catalog.get_details("gemma4:e4b")
