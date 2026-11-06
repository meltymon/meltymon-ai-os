
# MELTYMON AI OS – Testing Strategy

This document describes the testing strategy, test organization, and quality assurance practices used in MELTYMON AI OS.

Testing is a fundamental part of the project's development process.

The objective is to ensure that individual components behave predictably, failures are handled correctly, and changes do not introduce regressions into existing functionality.

---

## 1. Testing Objectives

The test suite has several objectives:

- Verify individual component behavior.
- Validate interactions between components.
- Detect regressions during development.
- Test error handling and failure conditions.
- Validate hardware monitoring without requiring physical hardware.
- Ensure consistent data structures and serialization.
- Keep the development process reproducible.

Tests should be deterministic and should not depend on a specific developer workstation.

---

## 2. Testing Framework

The project uses:

- **pytest** – test execution and assertions
- **pytest-asyncio** – asynchronous test support
- **pytest-cov** – code coverage reporting

Test dependencies are defined in `pyproject.toml`.

Install the development test dependencies:

```fish
python -m pip install -e ".[test]"
```

---

## 3. Test Organization

Tests are located in the `tests/` directory.

The current test suite is organized by subsystem.

| Test module | Area |
|---|---|
| `test_settings.py` | Configuration and settings |
| `test_ollama_backend.py` | Ollama backend |
| `test_ollama_live.py` | Ollama live integration |
| `test_model_catalog.py` | Model catalog and metadata |
| `test_resource_monitor.py` | CPU and memory monitoring |
| `test_numa.py` | NUMA monitoring |
| `test_gpu_monitor.py` | GPU monitoring architecture |
| `test_intel_gpu.py` | Intel GPU monitoring |
| `test_system_monitor.py` | System monitoring orchestration |
| `test_health.py` | Health evaluation |
| `test_diagnostics.py` | Diagnostic engine |
| `test_monitoring_service.py` | Monitoring service |
| `test_monitoring_api.py` | Public monitoring API |
| `test_serialization.py` | Data serialization |
| `test_agent_base.py` | Agent base behavior and execution lifecycle |
| `test_agent_capabilities.py` | Capability definitions and checks |
| `test_agent_context.py` | Immutable execution context |
| `test_agent_exceptions.py` | Agent exception hierarchy |
| `test_agent_lifecycle.py` | Lifecycle state transitions |
| `test_agent_result.py` | Structured immutable agent results |
| `test_execution_manager.py` | Concurrent execution, fail-fast, timeout, and cancellation behavior |
| `test_execution_policy.py` | Execution policy validation |
| `test_execution_report.py` | Execution records and aggregate reports |
| `test_orchestrator.py` | Agent dispatch and result validation |
| `test_orchestrator_registry.py` | Factory registration and agent creation |
| `test_agent_package.py` | Agent package public exports |
| `test_execution_package.py` | Execution package public exports |
| `test_orchestrator_package.py` | Orchestrator package public exports |
| `test_review.py` | Automated review workflow behavior |

The test suite may be extended as new modules and capabilities are introduced. The current suite includes tests for the Agent Runtime, Execution Layer, Orchestrator, and review workflow introduced during Milestone 10.

---

## 4. Running Tests

Run the complete test suite:

```fish
pytest -q
```

Run tests for an individual component:

```fish
pytest -q tests/test_gpu_monitor.py
```

Run tests with detailed output:

```fish
pytest -v
```

Run tests with coverage reporting:

```fish
pytest --cov=meltymon_ai_os --cov-report=term-missing
```

Generate an HTML coverage report:

```fish
pytest --cov=meltymon_ai_os --cov-report=html
```

The HTML report is generated in `htmlcov/`.

---

## 5. Hardware-Independent Testing

Hardware monitoring is particularly challenging to test because hardware availability differs between development environments.

The project therefore uses controlled test inputs and simulated hardware information wherever appropriate.

### GPU monitoring

GPU monitoring tests should not require a physical Intel, NVIDIA, or AMD GPU.

Tests can validate:

- Backend discovery
- Device enumeration
- Telemetry parsing
- Multiple GPU devices
- Missing telemetry
- Backend errors
- Device-specific failures

### NUMA monitoring

NUMA tests should validate topology and memory information using controlled system information.

They should not require a specific multi-socket system.

### Resource monitoring

CPU and memory monitoring tests should validate the behavior of the monitoring component without depending on fixed hardware specifications.

### Testing principle

A test should validate the behavior of the implementation, not the configuration of the developer's workstation.

---

## 6. Asynchronous Testing

Several components communicate with external services or execute asynchronous operations.

The project uses `pytest-asyncio` for asynchronous tests.

The pytest configuration uses:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

This provides automatic asynchronous test handling and function-scoped fixture event loops.

Asynchronous tests should validate both successful operations and relevant failure conditions.

---

## 7. Mocking and Isolation

Tests should isolate the component under examination from unrelated external dependencies.

Examples include:

- Mocking HTTP responses
- Simulating Ollama API responses
- Providing controlled GPU telemetry
- Simulating missing system interfaces
- Testing backend exceptions
- Using temporary directories for filesystem operations

This keeps tests reproducible and avoids unnecessary modifications to the host system.

Live integration tests should be clearly distinguished from tests that can run without external services.

---

## 8. Error Handling and Regression Testing

Error handling is an important part of the platform architecture.

Tests should cover more than successful execution.

Relevant failure scenarios include:

- Ollama is unavailable.
- An HTTP request times out.
- A model cannot be retrieved.
- A monitoring backend fails.
- A GPU device cannot provide telemetry.
- One GPU fails while another remains available.
- A system monitoring component returns unavailable data.
- Serialization encounters unsupported values.

The monitoring architecture must preserve the distinction between unavailable information and successfully collected empty results.

Regression tests should be added whenever a defect is corrected.

---

## 9. Monitoring State Semantics

GPU monitoring uses three distinct collection states.

| State | Meaning |
|---|---|
| `None` | Monitoring information is unavailable |
| `()` | Monitoring succeeded, but no GPU devices were found |
| Non-empty tuple | One or more GPU snapshots are available |

Tests must preserve these semantics.

Treating all three states as equivalent could lead to misleading health evaluations or diagnostics.

---

## 10. Serialization Testing

Serialization tests validate the conversion of supported Python objects into JSON-compatible representations.

Relevant test cases include:

- Dataclasses
- Nested data structures
- Date and datetime objects
- Enumerations
- Paths
- Dictionaries
- Lists and tuples
- Unsupported types
- Invalid dictionary keys
- Non-finite floating-point values

Serialization must be predictable and must reject unsupported data rather than silently producing misleading results.

---

## 11. Code Quality Checks

In addition to automated tests, the development workflow uses Git's whitespace and patch validation.

Run:

```fish
git diff --check
```

This helps identify whitespace errors and related patch problems before changes are committed.

The test suite and patch checks should be run after relevant implementation changes.

The repository also provides a consolidated review workflow:

```fish
python scripts/review.py
```

To include the dependency vulnerability audit:

```fish
python scripts/review.py --audit-dependencies
```

The review workflow includes repository and patch integrity checks, Ruff linting and formatting, Mypy, pytest with statement and branch coverage, Bandit, optional pip-audit, package building, wheel import smoke testing, and Twine metadata validation. Individual checks depend on the installed development tools and the selected review options.

### Whitespace validation for untracked files

The automated review also checks untracked files for trailing whitespace.

Markdown files (`.md`, `.markdown`, `.md.new`, and `.markdown.new`) may use two or more trailing ASCII spaces to represent CommonMark hard line breaks.

All other trailing whitespace remains an error, including:

- A single trailing space in Markdown files
- Trailing tabs in Markdown files
- Mixed trailing spaces and tabs
- Any trailing whitespace in non-Markdown files

Binary and non-UTF-8 files are skipped by the text-based check. Regression tests cover these rules and missing-file handling.

---

## 12. Current Test Baseline

The earlier baseline from November 2, 2026 was 133 passing tests. After the Agent Runtime, Execution Layer, Orchestrator, and review workflow were added, the Milestone 10 review snapshot from November 5, 2026 reported:

| Metric | Result |
|---|---:|
| Tests passed | 491 |
| Statement coverage | 96.79% |
| Branch coverage | 91.50% |
| Review checks passed | 16 |
| Failed review checks | 0 |
| Skipped review checks | 0 |

These are historical results from the documented review run, not a fixed expected test count or a guarantee of future results. Always use the actual output of the current test and review run as authoritative.

---

## 13. Recommended Development Workflow

The recommended workflow for changes is:

1. Implement or modify one component.
2. Run the relevant component tests.
3. Review failures and correct implementation issues.
4. Run the complete test suite.
5. Run `git diff --check`.
6. Review the resulting changes.
7. Update relevant documentation.
8. Commit only after the changes have been reviewed and validated.

For documentation-only changes, `git diff --check` is generally sufficient.

---

## 14. Future Testing Improvements

Planned improvements include:

- Expanded integration testing
- End-to-end platform tests
- Performance benchmarks
- Resource consumption tests
- More failure and recovery scenarios
- Additional backend compatibility tests
- Extended hardware simulation
- Expanded CI and end-to-end integration testing
- Test coverage tracking

These improvements will be introduced as the platform grows.

---

## 15. Related Documentation

- [Project Overview](../README.md)
- [Architecture](ARCHITECTURE.md)
- [Development History](DEVELOPMENT.md)
- [Roadmap](../ROADMAP.md)
- [Changelog](../CHANGELOG.md)
- [Contributing](../CONTRIBUTING.md)
- [License](../LICENSE)
