# MELTYMON AI OS — Architecture

This document describes the architecture and implementation boundaries of MELTYMON AI OS. It distinguishes working components from scaffolding and planned functionality. A package directory, interface, or exception type alone does not imply that an end-to-end feature is available.

## 1. Architectural overview

MELTYMON AI OS is a modular, local-first platform for operating and eventually orchestrating local AI workloads. Its current implementation combines configuration, an Ollama backend, model metadata, hardware monitoring, health evaluation, diagnostics, an Agent Runtime, controlled execution, and initial agent orchestration.

The implementation is a foundation, not yet a complete autonomous-agent platform. In particular, the current code does not provide complete agent-to-model integration, automatic model selection, resource-aware scheduling, persistent agent memory, or an enforced authorization system.

### 1.1 Component status

| Area | Responsibility | Current status |
|---|---|---|
| Configuration | Central settings and validation | Implemented |
| AI backend | Communication with inference services | Ollama implementation available |
| Model management | Catalog and normalized model metadata | Implemented foundation |
| Monitoring | CPU, memory, NUMA, and GPU telemetry | Implemented foundation |
| Health evaluation | Health state derived from monitoring data | Implemented foundation |
| Diagnostics | Rule-based findings and severity | Implemented foundation |
| Monitoring API | Public Python access and serialization | Implemented |
| Agent Runtime | Agent contract, context, results, lifecycle, capabilities | Implemented |
| Execution | Bounded asynchronous batch execution and reports | Implemented |
| Orchestration | Factory registry and agent dispatch | Initial implementation |
| Audit, Memory, Security, Validation | Future supporting subsystems | Package scaffolding only |
| User interface | Interactive management interface | Planned |

### 1.2 High-level structure

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
```

This is a logical view of the implemented subsystems, not a claim that every subsystem is already connected end to end. In particular, the Agent Runtime and the Ollama/model/monitoring layers remain separate foundations pending integration work.

## 2. Architectural principles

### Modularity and explicit contracts

Each subsystem has a defined responsibility. Components should communicate through explicit interfaces and stable data contracts rather than reaching into unrelated implementation details.

### Local-first operation

The initial inference integration targets a local Ollama service. The default endpoint is `http://127.0.0.1:11434`. The architecture should not require a cloud AI service for its basic local operating model.

### Hardware awareness

CPU, memory, NUMA, and GPU information provide the foundation for future resource-aware model selection and workload scheduling. Collecting telemetry does not, by itself, implement scheduling or optimization.

### Fault isolation

A failure in one monitoring provider, GPU device, or agent should be represented locally wherever possible. Independent components should remain usable when a peer component fails.

### Testability

Components should be testable without dedicated physical hardware or a running inference service wherever practical. External dependencies and hardware interfaces should be replaceable with controlled test doubles.

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
| `config/` | `settings.py`, configuration data | Application settings and validation |
| `execution/` | `manager.py`, `policy.py`, `report.py` | Batch execution, policy, records, reports |
| `memory/` | `__init__.py` | Reserved package; scaffolding only |
| `models/` | `catalog.py`, `metadata.py` | Model discovery and normalized metadata |
| `monitoring/` | `api.py`, `diagnostics.py`, `gpu.py`, `gpu_intel.py`, `health.py`, `numa.py`, `resources.py`, `serialization.py`, `service.py`, `system.py` | Hardware monitoring, health, diagnostics, API |
| `orchestrator/` | `engine.py`, `exceptions.py`, `registry.py` | Agent factory registry and dispatch |
| `security/` | `__init__.py` | Reserved package; scaffolding only |
| `validation/` | `__init__.py` | Reserved package; scaffolding only |

The packages `audit`, `memory`, `security`, and `validation` are structural foundations, not complete functional subsystems. The repository does not currently contain a complete graphical user interface.

## 4. Configuration layer

**Module:** `config/settings.py`

Configuration is centralized and validated using YAML settings, environment-variable overrides, and Pydantic models.

The documented environment variables are:

| Variable | Purpose |
|---|---|
| `MELTYMON_OLLAMA_BASE_URL` | Ollama API endpoint |
| `MELTYMON_OLLAMA_TIMEOUT` | Ollama request timeout |
| `MELTYMON_DEFAULT_MODEL` | Default model selection |

Values are validated before use. For example, the Ollama endpoint must use a supported HTTP scheme and valid host, and timeout values must be positive and within the configured limit. Components should consume centralized settings rather than defining competing configuration mechanisms.

## 5. AI backend and model management

### 5.1 Backend layer

**Modules:** `backends/base.py`, `backends/ollama.py`

The backend layer separates provider-specific communication from the rest of the application. Ollama is the currently implemented provider. Its asynchronous operations include service availability checks, model listing, model detail retrieval, and text generation. HTTP communication uses configurable timeouts; generation currently uses the non-streaming endpoint.

Additional providers are possible through the backend abstraction but are not currently implemented.

### 5.2 Model catalog

**Modules:** `models/catalog.py`, `models/metadata.py`

The model management layer retrieves model information from a backend, refreshes the local catalog, normalizes provider data, exposes individual entries, and retrieves extended model details.

Normalized metadata can represent model name, backend, family, parameter size, quantization, disk size, modification time, digest, context length, capabilities, and provider-specific information. Convenience capability information includes areas such as vision, tool use, and thinking when the provider exposes sufficient data.

The catalog provides a provider-independent representation. It does not yet perform automatic model selection based on task requirements or hardware capacity.

## 6. Hardware monitoring and system insight

The `monitoring/` package collects system and device information and turns it into snapshots that can be evaluated and serialized.

### 6.1 CPU and memory

**Module:** `monitoring/resources.py`

Collects CPU and system-memory information to describe available resources and current utilization.

### 6.2 NUMA

**Module:** `monitoring/numa.py`

Discovers NUMA topology and collects per-node information such as CPU lists, memory statistics, and topology distances. This is relevant to multi-socket and large-memory systems.

### 6.3 GPU monitoring

**Modules:** `monitoring/gpu.py`, `monitoring/gpu_intel.py`

The GPU architecture separates device snapshots, monitoring interfaces, discovery, telemetry collection, and error reporting. Devices are represented individually so that a multi-GPU host is not reduced to a single aggregate device.

The currently implemented vendor-specific backend is Intel, using Linux sysfs interfaces. Depending on hardware and driver support, telemetry can include temperature, power consumption or limits, energy, and frequency. Not every device exposes every field. NVIDIA and AMD backends are future work.

Monitoring state has deliberate semantics: unavailable monitoring information, a successful scan with no detected devices, and a non-empty set of device snapshots are distinct outcomes. Callers must not collapse these states into one generic empty value.

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

The Agent Runtime defines the contract and lifecycle for independently executable agents. It is implemented as a reusable runtime foundation; it does not imply that agents are already connected to a model or granted system permissions.

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

Agents return structured, immutable results. The exception hierarchy gives the runtime and callers explicit failure categories. An agent-level timeout is represented as a failed agent result rather than being treated as a successful completion.

## 8. Execution layer

**Modules:** `execution/manager.py`, `execution/policy.py`, `execution/report.py`

The execution layer runs batches of agent contexts under explicit policies.

Implemented controls include:

- A semaphore-backed maximum concurrency limit.
- Batch-level timeout handling.
- Continue-on-error and fail-fast policies.
- Cooperative cancellation handling.
- Immutable execution records and aggregate reports.
- Preservation of input order in the resulting report.

Fail-fast prevents tasks that have not started from being launched after a failure is observed. It does not automatically terminate work that is already running. Cancellation of running asynchronous work is cooperative and depends on the task responding to cancellation.

Execution records distinguish `SUCCESS`, `FAILURE`, `ERROR`, and `CANCELLED`. These states should remain distinct: a valid agent-level failure is not identical to an unexpected runtime error, and neither is identical to cancellation.

## 9. Orchestration layer

**Modules:** `orchestrator/engine.py`, `orchestrator/registry.py`, `orchestrator/exceptions.py`

The registry stores agent factory callables rather than long-lived agent instances. The orchestrator resolves a registered factory, creates a fresh agent, validates the created instance, and dispatches the supplied context.

Factory validation checks relevant properties such as the returned type, agent identity, and initial lifecycle state. After execution, the orchestrator validates the result contract, including result type, agent identity, and correlation identifier.

This is initial orchestration infrastructure. It is not yet a task planner or multi-agent reasoning engine. It does not automatically select models, assign resources, enforce permissions, or provide persistent execution history.

### 9.1 Execution flow

```text
Caller
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

## 10. Security and trust boundaries

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

## 11. Current integration boundaries and limitations

The current codebase provides several functional subsystems, but their existence does not mean they are fully integrated.

Not currently implemented as complete end-to-end functionality:

- Automatic invocation of Ollama/model generation from the Agent Runtime.
- Automatic model selection based on agent requirements or model metadata.
- Resource-aware agent scheduling using live monitoring data.
- A complete monitoring-to-orchestrator feedback loop.
- Agent-to-agent communication and multi-agent planning.
- Persistent agent memory, execution history, and recovery.
- A complete permission and approval enforcement system.
- Durable audit logging.
- A graphical management interface.

These are explicit development boundaries, not hidden assumptions. Future implementation should connect the existing contracts incrementally and add integration tests that demonstrate the complete behavior.

## 12. Testing and quality

The architecture is designed to support isolated, deterministic testing. Hardware-facing code should be tested with controlled telemetry and simulated interfaces; backend communication should be tested with mocked HTTP responses where a live service is not required. Asynchronous execution tests should cover successful execution, failures, timeout behavior, fail-fast semantics, and cancellation.

The repository's [Testing Strategy](TESTING.md) documents the test organization, commands, isolation approach, and recorded test baseline. The [Development History](DEVELOPMENT.md) records completed implementation milestones. The [Roadmap](../ROADMAP.md) describes future work.

---

**Architecture status:** This document describes the implementation boundary at Milestone 10. It is intended to be updated alongside code changes; planned functionality must remain clearly labeled until it is implemented and tested.
