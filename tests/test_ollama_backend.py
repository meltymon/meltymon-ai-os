import json

import httpx
import pytest

from meltymon_ai_os.backends.ollama import OllamaBackend


# Successful responses

@pytest.mark.asyncio
async def test_check_connection_success():
    def handler(request):
        assert request.url.path == "/api/version"
        return httpx.Response(200, json={"version": "0.13.0"})

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    assert await backend.check_connection() is True


@pytest.mark.asyncio
async def test_list_models():
    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "gemma4:e4b"}]},
        )

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    models = await backend.list_models()

    assert len(models) == 1
    assert models[0]["name"] == "gemma4:e4b"


@pytest.mark.asyncio
async def test_generate():
    def handler(request):
        payload = json.loads(request.content)

        assert payload["model"] == "gemma4:e4b"
        assert payload["prompt"] == "Hallo Ollama"
        assert payload["stream"] is False

        return httpx.Response(
            200,
            json={"response": "Hallo!"},
        )

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    result = await backend.generate(
        model="gemma4:e4b",
        prompt="Hallo Ollama",
    )

    assert result["response"] == "Hallo!"


# Error handling

@pytest.mark.asyncio
async def test_check_connection_unreachable():
    def handler(request):
        raise httpx.ConnectError(
            "Ollama nicht erreichbar",
            request=request,
        )

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    assert await backend.check_connection() is False


@pytest.mark.asyncio
async def test_list_models_http_error():
    def handler(request):
        return httpx.Response(500, json={"error": "Internal Server Error"})

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await backend.list_models()


@pytest.mark.asyncio
async def test_list_models_invalid_response():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "data"})

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    with pytest.raises(ValueError, match="expected 'models'"):
        await backend.list_models()


@pytest.mark.asyncio
async def test_generate_http_error():
    def handler(request):
        return httpx.Response(500, json={"error": "Generation failed"})

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await backend.generate(
            model="gemma4:e4b",
            prompt="Hallo Ollama",
        )

@pytest.mark.asyncio
async def test_show_model():
    expected = {
        "modelfile": "FROM gemma4:e4b",
        "capabilities": ["completion", "vision", "tools"],
        "model_info": {
            "general.architecture": "gemma4"
        },
    }

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/show"

        payload = json.loads(request.content)
        assert payload == {"model": "gemma4:e4b"}

        return httpx.Response(200, json=expected)

    backend = OllamaBackend(
        transport=httpx.MockTransport(handler)
    )

    result = await backend.show_model("gemma4:e4b")

    assert result == expected
