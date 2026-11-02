
# MELTYMON AI OS – Architecture

This document describes the current software architecture of MELTYMON AI OS.

It focuses on implemented components, their responsibilities, their relationships, and the architectural principles guiding future development.

Planned components are explicitly identified as such. Their presence in the project structure does not imply that their functionality has already been implemented.

---

## 1. Architectural Overview

MELTYMON AI OS is designed as a modular, local-first AI orchestration platform.

The architecture separates AI backend integration, model management, hardware monitoring, health evaluation, diagnostics, configuration, and public interfaces.

The current implementation establishes the foundation for these subsystems.

The intended high-level architecture is:

```text
                    MELTYMON AI OS
                           |
          +----------------+----------------+
          |                |                |
       AI Layer        System Layer     Core Services
          |                |                |
     AI Backends       Monitoring        Configuration
          |                |                |
       Ollama          CPU / RAM        Settings
          |                |                |
     Model Catalog       NUMA           Validation
          |                |                |
     Model Metadata       GPU
                           |
                    System Monitor
                           |
                   Monitoring Service
                           |
              +------------+------------+
              |            |            |
          Snapshot       Health     Diagnostics
          / API        Evaluation      Engine
              |
         Serialization
              |
        JSON / Dictionary
```

This diagram represents the current implemented foundation. Future agent, orchestration, memory, and security layers will build on top of it.

---

## 2. Design Principles

The architecture follows several core principles.

### Modularity

Each subsystem has a clearly defined responsibility.

Components should communicate through explicit interfaces rather than depending on unrelated implementation details.

### Local-first operation

The initial AI backend integration targets a local Ollama instance.

The default API endpoint is:

`http://127.0.0.1:11434`

Local execution is the default, not an afterthought.

### Hardware awareness

The platform collects information about available system resources and hardware.

This provides a foundation for future resource-aware model selection and workload scheduling.

### Fault isolation

An error in one monitoring component or GPU device should not unnecessarily prevent unrelated components from working.

### Testability

Components should be testable independently and without requiring specific physical hardware.

### Explicit state representation

Missing information, unavailable monitoring, and successful empty results must remain distinguishable.

### Extensibility

New AI backends, GPU monitoring providers, and future services should be integrable without redesigning the entire platform.

---

## 3. Package Structure

The source code is organized into separate packages.

The following tree describes the architectural organization. Some directories currently contain only initial scaffolding.

```text
src/meltymon_ai_os/
|
+-- agents/
|   +-- __init__.py
|
+-- audit/
|   +-- __init__.py
|
+-- backends/
|   +-- ollama.py
|
+-- config/
|   +-- settings.py
|
+-- memory/
|   +-- __init__.py
|
+-- models/
|   +-- catalog.py
|   +-- metadata.py
|
+-- monitoring/
|   +-- api.py
|   +-- diagnostics.py
|   +-- gpu.py
|   +-- health.py
|   +-- numa.py
|   +-- resources.py
|   +-- serialization.py
|   +-- service.py
|   +-- system.py
|
+-- orchestrator/
|   +-- __init__.py
|
+-- security/
|   +-- __init__.py
|
+-- validation/
|   +-- __init__.py
```

The actual source tree may evolve as new components are introduced.

---

## 4. Configuration Layer

**Module:** `config/settings.py`

The configuration layer provides centralized application settings.

It currently uses:

- YAML configuration
- Environment variable overrides
- Pydantic validation

### Current settings

The configuration includes settings for:

- Ollama connection URL
- Ollama request timeout
- Default model selection

### Environment variables

The following environment variables are supported:

| Variable | Purpose |
|---|---|
| `MELTYMON_OLLAMA_BASE_URL` | Ollama API endpoint |
| `MELTYMON_OLLAMA_TIMEOUT` | HTTP timeout |
| `MELTYMON_DEFAULT_MODEL` | Default model |

### Validation

Configuration values are validated before being used.

For example, the Ollama URL must use a supported HTTP scheme and a valid host.

Timeout values must be greater than zero and must not exceed the configured upper limit.

### Architectural role

The configuration layer centralizes application settings and prevents individual components from implementing their own configuration mechanisms.

---

## 5. AI Backend Layer

**Module:** `backends/ollama.py`

The backend layer provides a consistent interface for communicating with AI inference services.

The initial implementation integrates Ollama.

### Ollama backend

The current implementation supports asynchronous operations for:

- Checking service availability
- Listing installed models
- Retrieving model information
- Generating text

Communication uses HTTP requests with configurable timeouts.

Text generation currently uses the non-streaming Ollama generation endpoint.

### Backend abstraction

The backend architecture is intended to separate provider-specific communication from model management and orchestration.

This makes future integrations possible without requiring the rest of the platform to depend directly on Ollama-specific API responses.

### Current limitation

Ollama is the currently implemented backend.

Additional providers are planned but not yet implemented.

---

## 6. Model Management

**Modules:**

- `models/catalog.py`
- `models/metadata.py`

The model management layer provides a normalized representation of models available through supported backends.

### Model catalog

The ModelCatalog:

- Retrieves models from a backend
- Refreshes the local catalog
- Normalizes model information
- Provides access to individual model entries
- Retrieves extended model details

### Model metadata

Model metadata can contain:

- Name
- Backend
- Model family
- Parameter size
- Quantization
- Model size
- Modification timestamp
- Digest
- Context length
- Capabilities
- Additional model information

### Capability information

The metadata model provides convenience properties for capabilities such as:

- Vision
- Tool usage
- Thinking

### Architectural role

The model catalog provides a provider-independent model representation.

Future orchestration components can use this information to select suitable models based on task requirements and hardware resources.

---

## 7. Hardware Monitoring Layer

**Package:** `monitoring/`

The monitoring layer collects system and hardware information.

It is designed to support different monitoring providers through separate components and interfaces.

### 7.1 CPU and memory

**Module:** `monitoring/resources.py`

The resource monitoring component collects information about CPU and system memory.

The collected information provides a basic overview of available system resources.

### 7.2 NUMA

**Module:** `monitoring/numa.py`

The NUMA component discovers the system's NUMA topology and collects per-node memory statistics.

This is particularly relevant for multi-socket systems and large memory configurations.

### 7.3 GPU monitoring

**Module:** `monitoring/gpu.py`

The GPU monitoring component defines a generic architecture for GPU discovery and telemetry collection.

Its responsibilities include:

- GPU information structures
- Monitoring snapshots
- Backend interfaces
- Device discovery
- Telemetry collection
- Error tracking

The GPU monitor can work with multiple monitoring backends.

The current implementation includes an Intel GPU backend.

### 7.4 Intel GPU backend

The Intel implementation obtains available telemetry through Linux sysfs interfaces.

Depending on the device and driver, collected information includes:

- Temperature
- Power consumption
- Power limits
- Energy information
- Frequency information

Not all telemetry fields are available on every Intel GPU.

### 7.5 Multiple GPUs

GPU monitoring is designed around individual device snapshots.

This avoids treating a system with several GPUs as though it had only one GPU.

Individual devices can be monitored independently.

Backend and device telemetry failures are tracked separately wherever possible.

### Current limitations

- Intel is the currently implemented vendor-specific GPU backend.
- NVIDIA support is planned.
- AMD support is planned.
- Available telemetry depends on hardware and driver support.
- Generic interfaces exist for extending the implementation.

---

## 8. System Monitoring Orchestration

**Module:** `monitoring/system.py`

The SystemMonitor coordinates the individual monitoring components.

It collects information from the available resource monitors and combines the results into a unified system snapshot.

### Responsibilities

- Coordinate monitoring components
- Collect system information
- Execute independent collection operations concurrently where appropriate
- Combine component results
- Preserve monitoring errors

### System snapshot

The SystemSnapshot represents the collected system state.

It brings together information from CPU, memory, NUMA, and GPU monitoring.

### GPU collection semantics

The GPU field distinguishes three important states:

| Value | Meaning |
|---|---|
| `None` | GPU monitoring information is unavailable |
| `()` | Monitoring completed successfully, but no GPUs were found |
| Non-empty tuple | One or more GPU snapshots were collected |

These states must remain distinct.

A successful scan that finds no GPUs is not equivalent to a failed or unavailable monitoring operation.

---

## 9. Health Evaluation

**Module:** `monitoring/health.py`

The HealthEvaluator analyzes monitoring information and evaluates it against configurable thresholds.

### Responsibilities

- Evaluate resource conditions
- Apply health thresholds
- Identify abnormal conditions
- Support device-specific GPU checks
- Handle missing monitoring information

### GPU health checks

Individual GPUs can be evaluated separately.

Device-specific identifiers allow health results to be associated with the correct hardware.

### Architectural separation

The health evaluator does not perform hardware telemetry collection itself.

It consumes monitoring results and evaluates their meaning.

This separation keeps monitoring and health evaluation independent.

---

## 10. Diagnostic Engine

**Module:** `monitoring/diagnostics.py`

The DiagnosticEngine applies rules to available monitoring and health information.

It produces structured diagnostic findings.

### Responsibilities

- Evaluate diagnostic rules
- Classify severity
- Generate structured findings
- Identify affected resources
- Handle missing telemetry
- Preserve relevant backend and device error information

### Device-specific diagnostics

Individual GPU devices can produce their own diagnostic findings.

This allows the platform to identify which device is affected rather than reporting only a generic GPU problem.

### Relationship to health evaluation

Health evaluation determines whether defined conditions are satisfied.

Diagnostics provide more detailed findings about detected problems.

Both components are separate but complementary.

---

## 11. Monitoring Service

**Module:** `monitoring/service.py`

The MonitoringService combines the monitoring, health evaluation, and diagnostic components.

It provides a higher-level interface for retrieving a monitoring result.

### Responsibilities

- Trigger system monitoring
- Evaluate system health
- Run diagnostic rules
- Aggregate the results
- Return a structured monitoring result

### Architectural role

The service provides a convenient integration point for future platform components.

Consumers do not need to coordinate the individual monitoring and diagnostic components themselves.

---

## 12. Monitoring API and Serialization

**Modules:**

- `monitoring/api.py`
- `monitoring/serialization.py`

The API and serialization layer make monitoring information available to other components and external consumers.

### Monitoring API

The MonitoringAPI provides access to monitoring information through a public interface.

It supports retrieving monitoring data in structured representations.

### Serialization

The serialization layer converts supported Python objects into JSON-compatible data.

Supported types include:

- Dataclasses
- Date and datetime values
- Enumerations
- Paths
- Dictionaries
- Lists
- Tuples

Unsupported values and invalid structures are rejected rather than silently converted into potentially misleading output.

### Architectural role

This layer provides a common representation for future dashboards, integrations, agents, and external applications.

---

## 13. Current Monitoring Data Flow

The current monitoring flow can be summarized as follows:

```text
        Hardware and Operating System
                     |
          +----------+----------+
          |          |          |
         CPU        NUMA        GPU
          |          |          |
          +----------+----------+
                     |
               SystemMonitor
                     |
               SystemSnapshot
                     |
          +----------+----------+
          |                     |
     HealthEvaluator      DiagnosticEngine
          |                     |
          +----------+----------+
                     |
              MonitoringService
                     |
               MonitoringResult
                     |
              MonitoringAPI
                     |
                Serializer
                     |
               JSON / Dict
```

The diagram describes the implemented monitoring architecture.

---

## 14. Error Handling and Fault Isolation

Reliability is an important architectural requirement.

Monitoring operations may fail for several reasons:

- Hardware is unavailable
- A driver does not expose a telemetry field
- A device disappears
- A backend encounters an error
- A system interface cannot be accessed
- A monitoring component fails during collection

The architecture aims to isolate these failures.

### Component isolation

An error in one monitoring component should not automatically prevent unrelated components from collecting information.

### Device isolation

A failure affecting one GPU should not unnecessarily prevent monitoring of other GPUs.

### Error preservation

Errors are tracked so that health evaluation and diagnostics can distinguish missing information from successfully collected values.

### Explicit unavailable states

Unavailable telemetry should not be interpreted as a healthy measurement.

---

## 15. Testing Architecture

The project uses pytest to validate its components.

The architecture is designed to support hardware-independent tests.

Monitoring interfaces can be tested with controlled inputs and simulated hardware information.

This allows tests to validate:

- Device discovery
- Telemetry parsing
- Multi-GPU behavior
- Monitoring errors
- Health evaluation
- Diagnostic rules
- Serialization
- Service integration

The test suite is maintained separately from production modules.

See [Testing Strategy](TESTING.md) for details.

---

## 16. Planned Architectural Components

The following areas are part of the long-term architecture but are not yet implemented as functional subsystems.

### Agents

The planned agent layer will provide independent AI agents with defined responsibilities, capabilities, and execution contexts.

### Orchestration

The orchestration layer will coordinate tasks, agents, models, and hardware resources.

### Memory

The memory subsystem will provide persistent context and retrieval capabilities.

### Security

The security layer will establish permissions, execution boundaries, and auditing.

### User interface

Future management interfaces will expose model management, monitoring, diagnostics, and orchestration functionality.

These components will build on the current foundation as development progresses.

---

## 17. Related Documentation

- [Project Overview](../README.md)
- [Development History](DEVELOPMENT.md)
- [Roadmap](../ROADMAP.md)
- [Changelog](../CHANGELOG.md)
- [Testing Strategy](TESTING.md)
- [Architecture Decision Records](adr/)
- [Contributing](../CONTRIBUTING.md)
- [License](../LICENSE)

---

## Project Status

MELTYMON AI OS currently provides an initial implementation of local AI integration, model management, hardware monitoring, system health evaluation, diagnostics, and monitoring APIs.

The architecture is intentionally designed to support future expansion without turning the project into a tightly coupled monolithic application.
