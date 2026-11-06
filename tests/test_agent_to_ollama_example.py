"""Tests for the runnable Agent-to-Ollama vertical-slice example."""

from typing import Any

import pytest

from examples.agent_to_ollama import build_execution_manager
from meltymon_ai_os.agents import AgentContext
from meltymon_ai_os.backends.base import BaseBackend
from meltymon_ai_os.execution import ExecutionStatus


class FakeBackend(BaseBackend):
    """Deterministic backend substitute; no Ollama service is required."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {
            "model": "test-model",
            "response": "A deterministic test response.",
            "done": True,
        }
        self.calls: list[tuple[str, str]] = []

    async def check_connection(self) -> bool:
        return True

    async def list_models(self) -> list[dict[str, Any]]:
        return [{"name": "test-model"}]

    async def show_model(self, model: str) -> dict[str, Any]:
        return {"name": model}

    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append((model, prompt))
        return self.response


@pytest.mark.asyncio
async def test_successful_vertical_slice_returns_structured_report() -> None:
    backend = FakeBackend()
    manager = build_execution_manager(backend=backend, model="test-model")
    context = AgentContext(
        agent_id="ollama-prompt",
        input_data={"prompt": "Test the complete path."},
    )

    report = await manager.execute_many((context,))

    assert report.total == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert report.errors == 0

    record = report.records[0]
    assert record.status is ExecutionStatus.SUCCESS
    assert record.result is not None
    assert record.result.is_success
    assert record.result.agent_id == context.agent_id
    assert record.result.correlation_id == context.correlation_id
    assert record.result.output["response"] == "A deterministic test response."
    assert backend.calls == [("test-model", "Test the complete path.")]


@pytest.mark.asyncio
async def test_backend_exception_becomes_structured_agent_failure() -> None:
    class FailingBackend(FakeBackend):
        async def generate(
            self,
            model: str,
            prompt: str,
            **kwargs: Any,
        ) -> dict[str, Any]:
            raise ConnectionError("Backend unavailable.")

    manager = build_execution_manager(backend=FailingBackend(), model="test-model")
    context = AgentContext(
        agent_id="ollama-prompt",
        input_data={"prompt": "This request should fail."},
    )

    report = await manager.execute_many((context,))

    assert report.total == 1
    assert report.succeeded == 0
    assert report.failed == 1
    assert report.errors == 0
    assert report.records[0].status is ExecutionStatus.FAILURE
    assert report.records[0].result is not None
    assert report.records[0].result.error == "Backend unavailable."
    assert report.records[0].result.correlation_id == context.correlation_id


@pytest.mark.asyncio
async def test_invalid_backend_payload_becomes_structured_agent_failure() -> None:
    backend = FakeBackend(response={"model": "test-model", "done": True})
    manager = build_execution_manager(backend=backend, model="test-model")
    context = AgentContext(
        agent_id="ollama-prompt",
        input_data={"prompt": "The backend response has no generated text."},
    )

    report = await manager.execute_many((context,))

    assert report.failed == 1
    assert report.records[0].result is not None
    assert "does not contain generated text" in report.records[0].result.error
