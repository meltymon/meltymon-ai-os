import asyncio

from meltymon_ai_os.backends.ollama import OllamaBackend
from meltymon_ai_os.config.settings import load_settings
from meltymon_ai_os.models.catalog import ModelCatalog


async def main() -> None:
    """Read installed Ollama models and inspect their metadata."""

    settings = load_settings()

    backend = OllamaBackend(
        base_url=settings.ollama.base_url,
        timeout=settings.ollama.timeout,
    )

    catalog = ModelCatalog(backend)

    print("Connecting to Ollama...")

    if not await backend.check_connection():
        print("ERROR: Ollama is not reachable.")
        return

    print("Connection successful!\n")

    models = await catalog.refresh()

    print(f"Discovered models: {len(models)}\n")

    for model in models:
        print(f"- {model.name}")

    print("\nInspecting selected models:\n")

    selected_models = [
        "gemma4:e4b",
        "qwen3:8b",
        "qwen2.5-coder:7b",
    ]

    for model_name in selected_models:
        if catalog.get(model_name) is None:
            print(f"Model not installed: {model_name}\n")
            continue

        model = await catalog.get_details(model_name)

        print(f"Model: {model.name}")
        print(f"Backend: {model.backend}")
        print(f"Family: {model.family}")
        print(f"Parameters: {model.parameter_size}")
        print(f"Quantization: {model.quantization}")
        print(f"Context length: {model.context_length}")
        print(f"Capabilities: {', '.join(model.capabilities)}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
