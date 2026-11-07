# MELTYMON AI OS — Architecture

This document describes the architecture and implementation boundaries of MELTYMON AI OS. It distinguishes implemented components, tested integration paths, structural scaffolding, and planned functionality. A package directory, interface, or exception type alone does not imply that an end-to-end feature is available.

## 1. Purpose and architectural overview

MELTYMON AI OS is a modular, local-first Linux platform for operating and progressively orchestrating local AI workloads. Its current implementation combines centralized configuration, an Ollama backend, model metadata, hardware monitoring, health evaluation, diagnostics, an Agent Runtime, controlled asynchronous execution, and initial agent orchestration.

The project is an evolving engineering foundation, not yet a complete autonomous-agent platform. Several subsystems are functional independently, and an explicit agent-to-Ollama reference path is available and tested. However, automatic model selection, hardware-aware scheduling, persistent agent memory, platform-wide authorization, and a general monitoring-to-orchestration feedback loop are not implemented.

### 1.1 Component status

| Area | Responsibility | Current status |
|---|---|---|
| Configuration | YAML settings, environment overrides, validation | Implemented |
| AI backend | Provider abstraction and inference communication | Ollama implementation available |
| Model management | Model catalog and normalized metadata | Implemented foundation |
| Monitoring | CPU, memory, NUMA, and GPU telemetry | Implemented foundation |
| Health evaluation | Health state derived from monitoring data | Implemented foundation |
| Diagnostics | Rule-based findings and severity | Implemented foundation |
| Monitoring API | Public Python access and serialization | Implemented |
| Agent Runtime | Agent contract, context, results, lifecycle, capabilities | Implemented |
| Execution | Bounded asynchronous batch execution and reports | Implemented |
| Orchestration | Factory registry and agent dispatch | Initial implementation |
| Agent-to-Ollama reference path | Explicitly wired prompt agent and backend invocation | Runnable example and automated integration test |
| Audit, Memory, Security, Validation | Supporting subsystems | Package scaffolding only |
| User interface | Interactive management interface | Planned |

The status labels describe the current repository implementation. “Implemented foundation” means that a subsystem provides useful functionality but does not imply that all planned integrations or operational capabilities exist.

### 1.2 High-level architecture

```text
                         MELTYMON AI OS
                               |
       +-----------------------+-----------------------+
       |                       |                       |
  AI and Models           System Insight          Agent Runtime
       |                       |                       |
  Backend interface        Monitoring             Agent contract
       |                       |                       |
     Ollama            CPU / RAM / NUMA / GPU      Context / Result
       |                       |                       |
  Model catalog          Health evaluation         Lifecycle
  Model metadata         Diagnostics               Capabilities
                               |                       |
                       Monitoring service       Execution manager
                               |                       |
                       Public monitoring API       Orchestrator
                                                       |
                                                Agent registry
                                                   (factories)
                                                       |
                                             Explicit agent/backend
                                               integration example
```

This is a logical view of the implemented subsystems and the reference integration path. It does not claim that every subsystem is automatically connected or that the platform performs autonomous planning.

## 2. Architectural principles

### Modularity and explicit contracts

Each subsystem has a defined responsibility. Components communicate through explicit interfaces and stable data contracts rather than reaching into unrelated implementation details. Provider-specific communication is separated from backend-independent model and agent contracts.

### Local-first operation

The initial inference integration targets a local Ollama service. The default endpoint is `http://127.0.0.1:11434`. The architecture does not require a cloud AI service for its basic local operating model.

### Hardware awareness

CPU, memory, NUMA, and GPU information provide the foundation for future resource-aware model selection and workload scheduling. Collecting telemetry does not, by itself, implement scheduling or optimization.

### Fault isolation

A failure in one monitoring provider, GPU device, or agent should be represented locally wherever possible. Independent components should remain usable when a peer component fails. Monitoring backends and individual devices are handled as separate failure boundaries.

### Testability

Components should be testable without dedicated physical hardware or a running inference service wherever practical. External dependencies and hardware interfaces can be replaced with controlled test doubles. Live-service examples and deterministic automated tests are distinct validation levels.

### Explicit state and immutable data

Unavailable information, a successful empty result, and an actual failure must remain distinguishable. Immutable data structures are used for important contracts such as agent contexts, results, capabilities, and execution reports to reduce accidental mutation and hidden side effects.

### Controlled execution

Agent execution is bounded by lifecycle rules, concurrency limits, timeout policies, and explicit cancellation handling. Cancellation is cooperative: it requests that asynchronous work stop; it is not a guarantee that arbitrary already-running code can be forcibly terminated.

## 3. Package structure

The source code is organized below `src/meltymon_ai_os/`.

| Package | Main modules | Responsibility |
|---|---|---|
| `agents/` | `base.py`, `capabilities.py`, `context.py`, `exceptions.py`, `lifecycle.py`, `result.py` | Agent contract, capabilities, context, lifecycle, results |
| `audit/` | `__init__.py` | Reserved package; scaffolding only |
| `backends/` | `base.py`, `ollama.py` | Backend contract and Ollama integration |
| `config/` | `settings.py`, `settings.yaml` | Application settings and validation |
| `execution/` | `manager.py`, `policy.py`, `report.py` | Batch execution, policy, records, reports |
| `memory/` | `__init__.py` | Reserved package; scaffolding only |
| `models/` | `catalog.py`, `metadata.py` | Model discovery and normalized metadata |
| `monitoring/` | `api.py`, `diagnostics.py`, `gpu.py`, `gpu_intel.py`, `health.py`, `numa.py`, `resources.py`, `serialization.py`, `service.py`, `system.py` | Hardware monitoring, health, diagnostics, API |
| `orchestrator/` | `engine.py`, `exceptions.py`, `registry.py` | Agent factory registry and dispatch |
| `security/` | `__init__.py` | Reserved package; scaffolding only |
| `validation/` | `__init__.py` | Reserved package; scaffolding only |

The packages `audit`, `memory`, `security`, and `validation` are structural foundations, not complete functional subsystems. The repository does not currently contain a complete graphical user interface.

## 4. Configuration architecture

**Module:** `config/settings.py`

Configuration is loaded from YAML settings, supports environment-variable overrides, and is validated using Pydantic models. The default configuration file is `config/settings.yaml` within the package. An alternative configuration path can be supplied to `load_settings()`.

The supported environment variables are:

| Variable | Purpose |
|---|---|
| `MELTYMON_OLLAMA_BASE_URL` | Overrides the Ollama API endpoint |
| `MELTYMON_OLLAMA_TIMEOUT` | Overrides the Ollama request timeout |
| `MELTYMON_DEFAULT_MODEL` | Overrides the default model selection |

The default settings currently define the Ollama endpoint as `http://127.0.0.1:11434`, a request timeout of 60 seconds, and `gemma4:e4b` as the default model.

Configuration values are validated before use. Invalid configuration roots and sections are rejected, and timeout values must satisfy the configured constraints. The settings module provides the central configuration mechanism; components that receive configuration explicitly remain responsible for being wired to it by their caller.

## 5. AI backend and model management

### 5.1 Backend layer

**Modules:** `backends/base.py`, `backends/ollama.py`

The backend layer separates provider-specific communication from the rest of the application. `BaseBackend` defines the provider-independent contract. Ollama is the currently implemented provider.

Its asynchronous operations include service availability checks, model listing, model detail retrieval, and text generation. HTTP communication uses configurable timeouts. Text generation currently uses the non-streaming endpoint.

Additional providers can be introduced through the backend abstraction but are not currently implemented. The backend can be injected into an agent or other caller; the general Agent Runtime does not automatically construct or select a backend.

### 5.2 Model catalog

**Modules:** `models/catalog.py`, `models/metadata.py`

The model management layer retrieves model information from a backend, refreshes the local catalog, normalizes provider data, exposes individual entries, and retrieves extended model details.

Normalized metadata can represent model name, backend, family, parameter size, quantization, disk size, modification time, digest, context length, capabilities, and provider-specific information. Convenience capability information includes areas such as vision, tool use, and thinking when the provider exposes sufficient data.

The catalog provides a provider-independent representation. It does not yet perform automatic model selection based on task requirements, agent capabilities, or hardware capacity.

## 6. Monitoring, health evaluation, and diagnostics

The `monitoring/` package collects system and device information and turns it into snapshots that can be evaluated and serialized.

### 6.1 CPU and memory

**Module:** `monitoring/resources.py`

Collects CPU and system-memory information to describe available resources and current utilization.

### 6.2 NUMA

**Module:** `monitoring/numa.py`

Discovers NUMA topology and collects per-node information such as CPU lists, memory statistics, and topology distances. This is relevant to multi-socket and large-memory systems.

### 6.3 GPU monitoring

**Modules:** `monitoring/gpu.py`, `monitoring/gpu_intel.py`

The GPU architecture separates device snapshots, monitoring interfaces, discovery, telemetry collection, and error reporting. Devices are represented individually so that a multi-GPU host is not reduced to a single aggregate device. Detection is refreshed during collection cycles.

The currently implemented vendor-specific backend is Intel, using Linux DRM/sysfs interfaces. Depending on hardware and driver support, telemetry can include temperature, average power consumption, configured power limits, energy consumption, and GPU frequency information. Not every device exposes every field.

The current Intel sysfs implementation does **not** provide GPU utilization or VRAM usage telemetry. Additional telemetry through interfaces such as `intel_gpu_top` is separate future work. NVIDIA and AMD backends are also future work.

Monitoring state has deliberate semantics:

| State | Meaning |
|---|---|
| `None` | GPU monitoring information is unavailable |
| Empty tuple `()` | Collection succeeded, but no supported GPU devices were detected |
| Non-empty tuple | One or more GPU snapshots are available |

Backend failures and individual device collection failures are isolated and recorded independently where possible. Callers must not collapse unavailable monitoring, a successful empty scan, and a non-empty set of device snapshots into one generic empty value.

### 6.4 Health evaluation

**Module:** `monitoring/health.py`

Health evaluation interprets available monitoring data using configurable thresholds and device-specific checks. Missing telemetry must not be mistaken for a healthy measurement. The evaluator reports what can be established from available data; it does not repair hardware or automatically optimize workloads.

### 6.5 Diagnostics

**Module:** `monitoring/diagnostics.py`

The diagnostic engine applies rules to monitoring and health information and produces structured findings with severity classification. It is rule-based rather than an autonomous root-cause analysis engine. Recommendations and findings depend on the information actually available to the rules.

### 6.6 Monitoring integration and public API

**Modules:** `monitoring/system.py`, `monitoring/service.py`, `monitoring/api.py`, `monitoring/serialization.py`

The system monitor coordinates collection. The monitoring service combines snapshots, health evaluation, and diagnostic results. The public API exposes monitoring information, while serialization converts supported structures into dictionaries and JSON-compatible data.

These modules provide a monitoring interface that can be consumed by future orchestration and user-interface work. A complete live feedback loop from monitoring into agent scheduling is not yet implemented.

## 7. Agent Runtime

The Agent Runtime defines the contract and lifecycle for independently executable agents. It is implemented as a reusable runtime foundation; it does not imply that every agent is connected to a model or granted system permissions.

### 7.1 Agent base contract

**Modules:** `agents/base.py`, `agents/lifecycle.py`

The base agent defines the common execution contract and lifecycle hooks. Lifecycle state transitions are explicit and tracked. Agent instances are single-use: an instance is not intended to be restarted and reused for a later execution. The orchestrator obtains a fresh instance from a registered factory for each dispatch.

### 7.2 Context and correlation

**Module:** `agents/context.py`

An immutable execution context carries the data required for an agent invocation, including correlation information. Correlation identifiers allow related work and results to be associated without relying on mutable global state.

### 7.3 Capabilities

**Module:** `agents/capabilities.py`

Capabilities describe declared agent functionality. They are descriptive declarations and checks, not operating-system permissions, authorization grants, or security enforcement. A capability declaration must never be interpreted as proof that an action is authorized.

### 7.4 Results and exceptions

**Modules:** `agents/result.py`, `agents/exceptions.py`

Agents return structured, immutable results. The exception hierarchy gives the runtime and callers explicit failure categories. An agent-level failure is represented in the structured result contract; unexpected dispatch/runtime errors remain distinguishable at the orchestration and execution boundaries.

## 8. Execution architecture

**Modules:** `execution/manager.py`, `execution/policy.py`, `execution/report.py`

The execution layer runs batches of agent contexts under explicit policies.

Implemented controls include:

- A semaphore-backed maximum concurrency limit.
- Batch-level timeout handling.
- Continue-on-error and fail-fast policies.
- Cooperative cancellation handling.
- Immutable execution records and aggregate reports.
- Preservation of input order in the resulting report.
- Propagation of external cancellation after child tasks have been cancelled and awaited.

Fail-fast prevents tasks that have not started from being launched after a failure is observed. It does not automatically terminate work that is already running. Cancellation of running asynchronous work is cooperative and depends on the task responding to cancellation.

Execution records distinguish `SUCCESS`, `FAILURE`, `ERROR`, and `CANCELLED`. These states should remain distinct: a valid agent-level failure is not identical to an unexpected runtime error, and neither is identical to cancellation.

## 9. Orchestration architecture

**Modules:** `orchestrator/engine.py`, `orchestrator/registry.py`, `orchestrator/exceptions.py`

The registry stores agent factory callables rather than long-lived agent instances. The orchestrator resolves a registered factory, creates a fresh agent, validates the created instance, and dispatches the supplied context.

Factory validation checks relevant properties such as the returned type, agent identity, and initial lifecycle state. After execution, the orchestrator validates the result contract, including result type, agent identity, and correlation identifier.

This is initial orchestration infrastructure. It is not yet a task planner or multi-agent reasoning engine. It does not automatically select models, assign resources, enforce permissions, or provide persistent execution history.

### 9.1 Orchestration execution flow

```text
Caller
  |
  v
Execution Manager (for batch execution)
  |
  v
Orchestrator
  |
  +--> Agent Registry
  |       |
  |       +--> registered factory
  |                 |
  |                 v
  |           fresh Agent instance
  |
  +--> validate instance
  |
  +--> execute with Agent Context
  |       |
  |       +--> lifecycle hooks
  |       +--> structured Agent Result
  |
  +--> validate result contract
  |
  v
Execution Record / Aggregate Report
```

For batch work, the Execution Manager applies concurrency and failure policies around individual invocations and creates the aggregate report.

### 9.2 Explicit Agent-to-Ollama reference path

The repository includes a runnable integration example in [`examples/agent_to_ollama.py`](../examples/agent_to_ollama.py). It defines an `OllamaPromptAgent` that receives a backend and model through dependency injection, validates its prompt input, invokes the backend's asynchronous `generate()` operation, and returns structured agent output.

The example wires the components explicitly:

1. Construct an Ollama backend.
2. Inject the backend and selected model into the prompt agent factory.
3. Register the factory with the agent registry.
4. Create an `Orchestrator` and an `ExecutionManager`.
5. Submit an `AgentContext` and receive an `ExecutionReport`.

The corresponding [`tests/test_agent_to_ollama_example.py`](../tests/test_agent_to_ollama_example.py) exercises the complete vertical slice using a deterministic fake backend. It verifies successful generation, structured result/report data, and backend/payload failure handling without requiring a live Ollama service.

This proves that the explicit reference path works. It does **not** establish automatic backend construction, model selection, discovery-driven agent configuration, resource-aware scheduling, or a general-purpose autonomous agent integration.

## 10. Data flow and component interaction

The implemented monitoring path and the explicit agent reference path are separate flows:

**Monitoring flow**

```text
CPU / Memory / NUMA / GPU providers
                 |
                 v
           System Monitor
                 |
                 v
          System Snapshot
                 |
                 v
          Health Evaluator
                 |
                 v
           Health Report
                 |
                 v
         Diagnostic Engine
                 |
                 v
         Diagnostic Report
                 |
                 v
        Monitoring Result
          /          \
         v            v
   Monitoring API  Serialization
```

**Agent reference flow**

```text
Caller supplies AgentContext
             |
             v
      Execution Manager
             |
             v
        Orchestrator
             |
             v
       Agent Registry
             |
             v
     Agent factory creates
       a fresh agent
             |
             v
     OllamaPromptAgent
             |
             v
   Injected backend.generate()
             |
             v
      Structured output
             |
             v
       AgentResult
             |
             v
   ExecutionRecord / Report
```

The monitoring flow does not currently feed live resource information into agent scheduling. The agent reference flow is explicitly configured by the caller and does not automatically consult the model catalog or monitoring subsystem.

## 11. Security and trust boundaries

Security is an architectural requirement, but the current repository does not yet implement a complete authorization subsystem.

The following concepts must remain separate:

| Concept | Meaning | Current status |
|---|---|---|
| Capability | What an agent declares it can do | Implemented as agent metadata/checks |
| Execution policy | How a batch is scheduled and how failures are handled | Implemented in the execution layer |
| Permission | Whether an identity is allowed to perform an action | Not implemented as a complete system |
| Approval | Whether a sensitive action requires explicit human authorization | Not implemented |
| Audit record | Durable evidence of actions and decisions | Audit package is scaffolding only |

A future security design must define identity, authorization decisions, approval boundaries, sensitive-operation handling, and audit integrity. Until then, capability declarations and execution policies must not be presented as security controls.

The Ollama backend targets a configurable HTTP endpoint. Deployments that expose the service beyond the local host must account for network reachability and access controls at the service and infrastructure layers; the current project does not provide a platform-wide authorization layer.

## 12. Integration boundaries and current limitations

The current codebase provides several functional subsystems and one explicit, tested agent-to-Ollama reference path. Their existence does not mean that the complete platform is fully integrated.

The following capabilities are not currently implemented as general end-to-end platform functionality:

- Automatic backend construction and injection for arbitrary agents.
- Automatic model selection based on agent requirements, task metadata, or model catalog information.
- Resource-aware agent scheduling using live monitoring data.
- A complete monitoring-to-orchestrator feedback loop.
- Agent-to-agent communication and multi-agent planning.
- Persistent agent memory, execution history, and recovery.
- A complete permission and approval enforcement system.
- Durable audit logging.
- A graphical management interface.

These are explicit development boundaries, not hidden assumptions. Future implementation should connect the existing contracts incrementally and add integration tests that demonstrate the complete behavior.

## 13. Testing, quality assurance, and development

The architecture is designed to support isolated, deterministic testing. Hardware-facing code should be tested with controlled telemetry and simulated interfaces; backend communication should be tested with mocked HTTP responses where a live service is not required. Asynchronous execution tests should cover successful execution, failures, timeout behavior, fail-fast semantics, and cancellation.

The repository includes focused tests for configuration, backends, model management, monitoring, the Agent Runtime, execution policies and reports, orchestration, and the agent-to-Ollama reference example.

The recorded local quality run on 5 November 2026 reported:

- 491 pytest tests passed.
- Mypy reported no issues in 39 source files.
- The recorded Ruff invocation contained incompatible command-line options and therefore did not constitute a successful lint run.

These are historical results from that recorded run, not a claim about the current checkout or a substitute for rerunning the quality workflow after changes. Test counts and tool outcomes should be refreshed when the project is validated again.

The repository's [Testing Strategy](TESTING.md) documents the test organization, commands, and isolation approach. The [Development History](DEVELOPMENT.md) records implementation milestones. The [Roadmap](../ROADMAP.md) describes future work. The consolidated review workflow is available through `python scripts/review.py`.

## 14. Architecture evolution

The architecture is intended to evolve incrementally. New functionality should extend explicit contracts, preserve fault isolation, and include tests for both expected behavior and failure conditions.

Priority integration steps include:

- Connect agent configuration to the backend and model catalog through explicit, testable dependency boundaries.
- Define model-selection inputs and deterministic selection policies before implementing automatic selection.
- Introduce resource-aware scheduling only after monitoring data, resource requirements, and scheduling decisions have explicit contracts.
- Design permissions, approvals, and durable audit records as separate security mechanisms rather than extending descriptive agent capabilities.
- Add integration tests for cross-subsystem behavior and live-service tests where they provide additional evidence.

Planned capabilities must remain labeled as planned until implementation and tests demonstrate them.

---

**Architecture status:** This document describes the repository state after Milestone 10, including the explicitly wired and tested agent-to-Ollama reference path. It is intended to be updated alongside code changes; planned functionality must remain clearly labeled until it is implemented and tested.
