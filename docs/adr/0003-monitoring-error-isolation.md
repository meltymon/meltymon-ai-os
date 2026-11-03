# ADR 0003: Monitoring Error Isolation

- **Status:** Accepted
- **Date:** 2026-11-02
- **Decision:** Isolate monitoring collection failures at backend, device and system-component level.

## 1. Context

System monitoring depends on multiple independent hardware components and monitoring backends.

A failure in one backend or device must not prevent the collection and evaluation of data from other available components.

The original monitoring implementation did not provide sufficient isolation between backend and device failures. Exceptions could interrupt collection and prevent otherwise valid monitoring results from being returned.

Multi-GPU support also requires individual device results and errors to remain distinguishable.

## 2. Decision

The monitoring architecture isolates collection failures at the following levels:

1. Backend discovery
2. Individual GPU device collection
3. System monitoring components

A failure in one component must not unnecessarily interrupt monitoring of independent components.

Health evaluation processes per-device checks and converts reported monitoring errors into degraded health checks.

Diagnostic generation translates health checks into device-specific findings. Neither health evaluation nor diagnostic generation currently provides a separate exception-isolation boundary.

### GPU monitoring semantics

The GPU monitoring interface distinguishes three states:

- `None`: GPU monitoring data is unavailable because collection failed.
- `()`: Collection completed successfully, but no GPU devices were detected.
- Non-empty tuple: One or more GPU snapshots were collected.

Errors are retained with their corresponding backend or device identity wherever available.

### Monitoring service

The monitoring service combines the available system snapshot, health evaluation and diagnostic results into a structured monitoring result.

Partial collection failures remain observable without discarding successful results from independent components.

## 3. Implementation

The decision is implemented through:

- Independent exception handling in GPU backend discovery.
- Independent exception handling during device collection.
- Error tracking for individual backends and devices.
- Repeated device detection during monitoring cycles.
- Multi-GPU snapshot representation.
- Per-device health evaluation.
- Device-specific diagnostic findings.
- Structured monitoring results through `MonitoringService`.

## 4. Testing

Regression and integration tests verify:

- Backend failures do not prevent other backends from operating.
- Individual GPU collection failures do not hide successful devices.
- Empty GPU collections are treated as successful results.
- Device detection is refreshed during collection cycles.
- Backend and device identities are preserved in error information.
- Multiple GPUs are evaluated independently.
- Missing metrics on one device do not suppress valid results from another.
- Monitoring service results preserve snapshots, health information and diagnostics.

## 5. Consequences

### Positive consequences

- Improved resilience against partial hardware failures.
- Independent monitoring of multiple GPU devices.
- Better visibility into backend and device errors.
- More predictable monitoring behavior.
- Easier testing of individual monitoring components.
- Improved extensibility for additional GPU vendors and monitoring backends.

### Trade-offs

- More complex error propagation and result structures.
- Additional handling required by consumers of monitoring results.
- Partial failures must be interpreted explicitly by API consumers.

## 6. Future Considerations

Additional monitoring backends, including NVIDIA and AMD, should follow the same error-isolation principles.

Future telemetry integrations must preserve the distinction between unavailable data, missing hardware and successfully collected measurements.

Independent error isolation for health evaluation and diagnostic generation may be considered in a future version if required.

## 7. References

- `src/meltymon_ai_os/monitoring/gpu.py`
- `src/meltymon_ai_os/monitoring/system.py`
- `src/meltymon_ai_os/monitoring/health.py`
- `src/meltymon_ai_os/monitoring/diagnostics.py`
- `src/meltymon_ai_os/monitoring/service.py`
- `tests/test_gpu_monitor.py`
- `tests/test_system_monitor.py`
- `tests/test_health.py`
- `tests/test_diagnostics.py`
- `tests/test_monitoring_service.py`
