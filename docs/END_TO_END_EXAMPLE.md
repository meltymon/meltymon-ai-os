# End-to-End Agent Example

This example demonstrates one complete, read-only execution path through the
existing MELTYMON AI OS foundations:

```text
AgentContext
    |
    v
ExecutionManager
    |
    v
Orchestrator
    |
    v
AgentRegistry -- creates a fresh agent instance
    |
    v
OllamaPromptAgent
    |
    v
Injected BaseBackend implementation
    |
    v
OllamaBackend -> local Ollama API
    |
    v
AgentResult
    |
    v
ExecutionRecord + ExecutionReport
```

The example is deliberately small. Its purpose is to demonstrate the wiring
between the Agent Runtime, registry, orchestrator, execution manager, backend
abstraction and structured result/report types. It is not a claim that every
platform subsystem is integrated.

## Requirements

- Python 3.11 or newer
- MELTYMON AI OS installed in the active virtual environment
- Ollama running locally
- The model passed with `--model` already available in Ollama

From the repository root:

```fish
python -m pip install -e ".[test]"
ollama pull gemma4:e4b
```

## Run the example

```fish
python examples/agent_to_ollama.py \
    --model gemma4:e4b \
    --prompt "Explain NUMA in two concise sentences."
```

For a different local Ollama endpoint:

```fish
python examples/agent_to_ollama.py \
    --ollama-url http://127.0.0.1:11434 \
    --model gemma4:e4b
```

The script prints a JSON summary with the execution ID, agent ID, correlation
ID, status, duration, structured output and any error. Generated text, IDs and
duration naturally vary between runs.

## What each layer does

1. **AgentContext** carries immutable input data and a correlation ID.
2. **ExecutionManager** applies the batch policy and creates the execution report.
3. **Orchestrator** dispatches the context to the registered agent.
4. **AgentRegistry** uses a factory to create a fresh agent instance.
5. **OllamaPromptAgent** validates the prompt and calls the injected backend.
6. **OllamaBackend** sends the request to the local Ollama API.
7. **AgentResult** records success or failure while preserving correlation.
8. **ExecutionRecord / ExecutionReport** expose the final execution state.

The backend is injected through the agent factory. The agent depends on the
`BaseBackend` contract rather than directly on Ollama. Tests can therefore use
a deterministic fake backend without starting Ollama or downloading a model.

## Run tests without Ollama

```fish
pytest -q tests/test_agent_to_ollama_example.py
```

The tests cover:

- A successful execution through the execution manager and orchestrator.
- A backend exception represented as a structured failed agent result.
- An invalid backend payload represented as a structured failed agent result.
- Preservation of the context correlation ID in the result.

No live Ollama service, downloaded model or physical AI hardware is required
for these tests.

## Scope and safety

This example sends a prompt to an explicitly configured inference backend and
prints the returned text and execution metadata. It does not execute shell
commands, modify host files, install software or grant agent permissions.

It does not implement authorization, human approval, durable audit storage,
persistent memory, resource-aware scheduling or process isolation. Those
remain separate platform requirements and must be addressed before agents
perform sensitive or host-changing actions.

## Status and limitations

This is a vertical-slice demonstration of existing interfaces, not a
production-readiness certification. The broader project test suite and
consolidated review workflow remain the wider quality checks.

Related documentation:

- [Architecture](ARCHITECTURE.md)
- [Testing Strategy](TESTING.md)
- [Contributing](../CONTRIBUTING.md)
- [Project TODO](../TODO.md)
