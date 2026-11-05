# MELTYMON AI OS – Project TODO

This file is the practical task register for the next development steps.
It complements the [Roadmap](ROADMAP.md): the roadmap describes the long-term direction,
while this file records actionable work, priorities, dependencies, and acceptance criteria.

**Project stage:** Pre-alpha / early development  
**Last reviewed:** 2026-11-05  
**Status baseline:** Milestone 10 – initial Agent Runtime, Execution Layer, and orchestration foundations

> A checked box means the acceptance criteria have been demonstrated by code and tests.
> A package directory, interface, or documentation entry alone does not count as completion.

## Priority definitions

- **P0 – Critical foundation:** Required before exposing more powerful or autonomous behavior.
- **P1 – High:** Needed to make the current foundations reliable and demonstrably useful.
- **P2 – Medium:** Important platform capabilities after the first end-to-end workflow.
- **P3 – Later:** Optimization, expansion, and release polish.

---

## P0 – First end-to-end workflow and safety boundaries

### TODO-001 – Connect Agent Runtime to Ollama

- [ ] Define how an agent receives a model/backend dependency without hard-coding Ollama into the runtime.
- [ ] Connect an agent invocation to the existing backend and normalized model catalog.
- [ ] Define request, response, timeout, and provider-error behavior.
- [ ] Preserve correlation IDs across agent, backend, and execution records.
- [ ] Add mocked integration tests for success, unavailable backend, malformed response, timeout, and cancellation.
- [ ] Add one documented, read-only example that runs an agent against a local Ollama model.

**Acceptance criteria:** A test demonstrates the complete path from agent context through model invocation to a structured agent result. The test does not require a live Ollama service.

### TODO-002 – Define the security boundary before allowing host actions

- [ ] Define agent identity and the principal on whose behalf an action runs.
- [ ] Design explicit authorization checks; capability declarations must remain descriptive metadata.
- [ ] Define human approval requirements for sensitive or destructive actions.
- [ ] Define a deny-by-default policy for actions without an authorization decision.
- [ ] Define secret handling and redaction rules for configuration, prompts, results, and logs.
- [ ] Document the threat model and trust boundaries.

**Acceptance criteria:** Tests prove that unauthorized actions are denied, approval-required actions cannot proceed without approval, and sensitive values are not exposed in logs. Do not add write-capable host tools before this boundary exists.

### TODO-003 – Add durable audit events

- [ ] Define a versioned audit-event schema with actor, action, target, timestamp, correlation ID, decision, and outcome.
- [ ] Record authorization decisions and approval outcomes.
- [ ] Define storage, retention, integrity, and failure behavior.
- [ ] Ensure audit failure cannot silently turn a denied action into an allowed action.
- [ ] Add tests for event completeness, redaction, ordering, and storage failures.

**Acceptance criteria:** Security-relevant decisions and execution outcomes can be reconstructed from durable, privacy-conscious audit records.

---

## P1 – Integration, correctness, and quality gates

### TODO-004 – Integrate monitoring with execution

- [ ] Make monitoring snapshots available through a stable, injected interface.
- [ ] Add resource-aware admission checks for CPU, RAM, NUMA, and supported GPU telemetry.
- [ ] Define behavior when telemetry is missing, stale, or unavailable.
- [ ] Keep scheduling decisions explainable and observable.
- [ ] Add deterministic tests using simulated hardware data.

**Acceptance criteria:** An execution decision can explain which resource information it used and why a workload was admitted, delayed, or rejected.

### TODO-005 – Strengthen execution and cancellation semantics

- [ ] Test cancellation while tasks are queued, starting, running, and cleaning up.
- [ ] Test simultaneous failures and timeout races.
- [ ] Verify that every execution record reaches a consistent terminal state.
- [ ] Document that asyncio cancellation is cooperative and does not forcibly stop arbitrary blocking work.
- [ ] Decide whether potentially blocking or untrusted agents need process isolation.

**Acceptance criteria:** Failure, timeout, cancellation, and cleanup behavior is deterministic, documented, and covered by regression tests.

### TODO-006 – Make the CI quality gates match the local review workflow

- [ ] Add Ruff lint and format checks to GitHub Actions.
- [ ] Add Mypy to GitHub Actions.
- [ ] Add Bandit static security analysis to GitHub Actions.
- [ ] Decide how and how often pip-audit should run; make skipped dependency scans visible.
- [ ] Add an explicit, maintainable coverage threshold after reviewing the current baseline.
- [ ] Keep package build and distribution metadata validation in CI.
- [ ] Document which checks are mandatory and which are optional.

**Acceptance criteria:** A pull request receives a reproducible, visible result for all mandatory quality gates. A skipped check is never represented as a passed check.

### TODO-007 – Separate live Ollama smoke tests from the pytest suite

- [ ] Move the current manually executable `tests/test_ollama_live.py` script to a clearly named smoke-test location, or convert it into an explicitly marked integration test.
- [ ] Keep normal CI independent of a running Ollama service.
- [ ] Add mocked HTTP tests for backend operations and error cases.
- [ ] Provide a documented opt-in command for a live local Ollama check.

**Acceptance criteria:** Standard pytest collection contains real automated tests; live-service checks are clearly opt-in and cannot make ordinary CI flaky.

### TODO-008 – Add end-to-end integration and recovery tests

- [ ] Test the complete agent → execution manager → orchestrator → backend → result path.
- [ ] Test multiple agents with bounded concurrency.
- [ ] Test partial failure and recovery behavior.
- [ ] Test correlation IDs and structured execution reports across the complete path.
- [ ] Test behavior when monitoring or the model backend becomes unavailable mid-run.

**Acceptance criteria:** The most important platform workflow is validated across package boundaries, not only through isolated unit tests.

---

## P2 – Platform capabilities

### TODO-009 – Implement persistent memory

- [ ] Define memory types, ownership, and agent-specific scopes.
- [ ] Select a storage abstraction and persistence format.
- [ ] Implement write, retrieval, indexing, and search interfaces.
- [ ] Define retention, deletion, export, and data-protection behavior.
- [ ] Add isolation tests to prevent cross-agent or cross-user memory leakage.

**Acceptance criteria:** Memory survives process restarts, obeys explicit scope boundaries, and has tested lifecycle and deletion behavior.

### TODO-010 – Add model selection and resource-aware scheduling

- [ ] Extend model metadata with validated resource requirements where available.
- [ ] Define model/agent compatibility rules.
- [ ] Select models using declared requirements and current resource availability.
- [ ] Define fallback behavior when no suitable model or resource allocation exists.
- [ ] Explain scheduling decisions in structured diagnostics.

**Acceptance criteria:** Model selection is deterministic for a given input snapshot and produces an explainable decision.

### TODO-011 – Expand hardware provider coverage

- [ ] Improve Intel GPU telemetry and document driver/kernel dependencies.
- [ ] Implement NVIDIA monitoring behind the existing backend abstraction.
- [ ] Implement AMD monitoring behind the same abstraction.
- [ ] Add hardware-independent tests for each provider.
- [ ] Add optional hardware integration tests where devices are available.

**Acceptance criteria:** Missing or failing hardware providers do not interrupt monitoring of other devices.

### TODO-012 – Build an operational interface

- [ ] Decide whether the first interface should be CLI, local API, TUI, or web UI.
- [ ] Expose system health and resource snapshots.
- [ ] Expose model inventory and backend status.
- [ ] Expose agent registration and execution status.
- [ ] Expose diagnostics and audit events with appropriate access controls.

**Acceptance criteria:** An operator can understand platform state and inspect an execution without reading internal log files.

---

## P3 – Release and long-term quality

### TODO-013 – Performance and reliability evaluation

- [ ] Benchmark monitoring overhead and sampling behavior.
- [ ] Measure execution throughput and concurrency limits.
- [ ] Evaluate memory consumption under sustained workloads.
- [ ] Test long-running operation and repeated backend failures.
- [ ] Document supported hardware/software combinations.

### TODO-014 – Installation and release preparation

- [ ] Define the supported installation and upgrade path.
- [ ] Define configuration migration and compatibility policy.
- [ ] Add release notes and a versioning policy.
- [ ] Validate source distribution and wheel installation in a clean environment.
- [ ] Create a release checklist and publish the first tagged release only after its criteria are met.

---

## Immediate next steps

The recommended order is:

1. **TODO-001:** Deliver one harmless, read-only agent-to-Ollama vertical slice.
2. **TODO-002 and TODO-003:** Design authorization, approval, and audit boundaries before introducing host-changing actions.
3. **TODO-007 and TODO-006:** Clarify live integration testing and strengthen automated CI gates.
4. **TODO-004, TODO-005, and TODO-008:** Connect monitoring and execution and prove failure behavior end to end.

Do not start with a large UI or additional model providers. First prove one complete, safe, observable workflow with the components already present.

## Maintenance rules

- Keep this file focused on actionable work; keep architectural rationale in ADRs and architecture documentation.
- Update the [Roadmap](ROADMAP.md) when a task materially changes a phase's status.
- Mark a task complete only after its acceptance criteria are met and tests/documentation are updated.
- Move completed historical work into the changelog or a dated milestone record rather than deleting project history.
- Split large tasks into smaller tasks or GitHub Issues when implementation begins.
- Reassess priorities after each integration milestone.
