"""Runnable end-to-end example: Agent Runtime -> Orchestrator -> Ollama.

Run from the repository root after installing the project:
    python examples/agent_to_ollama.py --model gemma4:e4b
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping
from typing import Any

from meltymon_ai_os.agents import AgentBase, AgentContext
from meltymon_ai_os.backends.base import BaseBackend
from meltymon_ai_os.backends.ollama import OllamaBackend
from meltymon_ai_os.execution import ExecutionManager, ExecutionPolicy
from meltymon_ai_os.orchestrator import AgentRegistry, Orchestrator


class OllamaPromptAgent(AgentBase):
    """Read-only agent that sends one prompt to an injected inference backend."""

    def __init__(self, *, backend: BaseBackend, model: str) -> None:
        if not isinstance(backend, BaseBackend):
            raise TypeError("backend must be a BaseBackend.")

        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string.")

        super().__init__(agent_id="ollama-prompt")
        self._backend = backend
        self._model = model.strip()

    async def _execute(self, context: AgentContext) -> dict[str, Any]:
        """Validate the input, call the backend and return structured output."""
        prompt = context.get_input("prompt")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Input 'prompt' must be a non-empty string.")

        response = await self._backend.generate(
            model=self._model,
            prompt=prompt,
        )

        if not isinstance(response, Mapping):
            raise TypeError("Backend response must be a mapping.")

        generated_text = response.get("response")
        if not isinstance(generated_text, str):
            raise ValueError("Backend response does not contain generated text.")

        return {
            "model": response.get("model", self._model),
            "response": generated_text,
            "done": response.get("done"),
        }


def build_execution_manager(
    *,
    backend: BaseBackend,
    model: str,
) -> ExecutionManager:
    """Wire the backend adapter, agent factory, registry and execution manager."""
    registry = AgentRegistry()
    registry.register(
        "ollama-prompt",
        lambda: OllamaPromptAgent(backend=backend, model=model),
    )

    return ExecutionManager(
        Orchestrator(registry),
        ExecutionPolicy(
            max_concurrency=1,
            continue_on_error=False,
            batch_timeout=90.0,
        ),
    )


async def run_prompt(
    *,
    model: str,
    prompt: str,
    ollama_url: str,
) -> dict[str, Any]:
    """Execute one prompt and return a JSON-serializable summary."""
    backend = OllamaBackend(base_url=ollama_url)
    manager = build_execution_manager(backend=backend, model=model)

    context = AgentContext(
        agent_id="ollama-prompt",
        input_data={"prompt": prompt},
        metadata={"example": "agent-to-ollama"},
    )

    report = await manager.execute_many((context,))
    record = report.records[0]
    result = record.result

    output = None
    error = record.error

    if result is not None:
        output = dict(result.output) if isinstance(result.output, Mapping) else result.output
        error = result.error

    return {
        "execution_id": report.execution_id,
        "agent_id": record.context.agent_id,
        "correlation_id": record.context.correlation_id,
        "status": record.status.value,
        "duration_seconds": round(record.duration, 3),
        "output": output,
        "error": error,
    }


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="An installed Ollama model.")
    parser.add_argument(
        "--prompt",
        default="Explain in two sentences why software tests are useful.",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama API base URL.",
    )
    args = parser.parse_args()

    summary = await run_prompt(
        model=args.model,
        prompt=args.prompt,
        ollama_url=args.ollama_url,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
