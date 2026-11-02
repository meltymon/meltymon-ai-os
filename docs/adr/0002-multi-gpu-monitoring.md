
# ADR 0002: Multi-GPU Monitoring Architecture

- **Status:** Accepted
- **Date:** 2026-11-02
- **Decision type:** Architecture

## Context

MELTYMON AI OS is designed to run on systems with different hardware configurations.

Local AI workloads can use:

- Integrated GPUs
- Dedicated GPUs
- Multiple GPUs
- GPUs from different manufacturers
- Heterogeneous combinations of available hardware

A monitoring architecture based on a single GPU would unnecessarily restrict the platform.

Different GPU vendors also expose hardware telemetry through different drivers and operating system interfaces.

The monitoring subsystem therefore needs a common abstraction that supports multiple devices and different vendor-specific implementations.

## Decision

GPU monitoring uses a backend-based architecture with individual device snapshots.

The architecture separates:

- Generic GPU information structures
- GPU monitoring snapshots
- Backend interfaces
- Device discovery
- Telemetry collection
- Device-specific errors

A monitoring backend is responsible for discovering and collecting information from devices it supports.

The generic monitoring layer coordinates the available backends and collects their results.

Individual GPU devices are represented independently.

The current implementation includes an Intel GPU backend using Linux sysfs interfaces.

Additional vendor-specific backends can be introduced without changing the fundamental monitoring data model.

## Collection State Semantics

The GPU monitoring result distinguishes three states:

| State | Meaning |
|---|---|
| `None` | GPU monitoring information is unavailable |
| `()` | Monitoring completed successfully, but no GPUs were discovered |
| Non-empty tuple | One or more GPU snapshots were collected |

These states must remain distinct.

An unavailable monitoring result must not be interpreted as a successful scan with no devices.

## Alternatives Considered

### Single-GPU monitoring

A single GPU object could represent the entire system.

Rejected because it cannot properly represent multiple devices or heterogeneous GPU configurations.

### Vendor-specific monitoring throughout the application

Every higher-level component could directly implement vendor-specific GPU handling.

Rejected because it would tightly couple health evaluation, diagnostics, and future orchestration to individual GPU implementations.

### Common backend abstraction

A generic monitoring interface could coordinate vendor-specific implementations.

Selected because it provides a consistent representation while keeping hardware-specific functionality isolated.

## Consequences

### Positive

- Supports multiple GPU devices
- Allows heterogeneous GPU configurations
- Separates generic monitoring from vendor-specific telemetry
- Enables independent device snapshots
- Supports device-specific health evaluation
- Supports device-specific diagnostics
- Allows additional GPU backends to be introduced incrementally

### Trade-offs

- Vendor-specific backends require individual implementation and testing.
- Available telemetry differs between hardware and drivers.
- Device discovery and backend failures require careful handling.
- Some telemetry fields may remain unavailable on certain devices.

## Implementation Status

Currently implemented:

- Generic GPU monitoring interfaces
- GPU information and snapshot structures
- Backend-based monitoring architecture
- Intel GPU discovery and telemetry
- Multiple device snapshots
- Device-specific monitoring information

Planned:

- NVIDIA GPU backend
- AMD GPU backend
- Extended hardware telemetry
- Additional hardware providers

## Related Documentation

- [Architecture](../ARCHITECTURE.md)
- [Development History](../DEVELOPMENT.md)
- [Testing Strategy](../TESTING.md)
- [Roadmap](../../ROADMAP.md)
