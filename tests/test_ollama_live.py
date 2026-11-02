import asyncio

from meltymon_ai_os.backends.ollama import OllamaBackend


async def main():
    backend = OllamaBackend()

    print("Prüfe Verbindung zu Ollama ...")

    connected = await backend.check_connection()

    if not connected:
        print("Ollama ist nicht erreichbar.")
        return

    print("Verbindung erfolgreich!")

    print("\nVerfügbare Modelle:")

    models = await backend.list_models()

    for model in models:
        print(f"- {model.get('name', 'Unbekannt')}")

    print(f"\nInsgesamt {len(models)} Modelle gefunden.")


if __name__ == "__main__":
    asyncio.run(main())
