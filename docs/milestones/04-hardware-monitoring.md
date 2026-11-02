
# Milestone 04 – Hardware Monitoring

- **Status:** Implemented foundation
- **Development date:** 2026-11-02
- **Related commit:** `56bcb75`

## Objective

Establish a hardware monitoring subsystem that provides information about the resources available to local AI workloads.

The monitoring architecture is designed to support different hardware configurations, including systems with multiple CPU sockets, NUMA nodes, and GPUs.

Hardware awareness is a fundamental requirement for future resource-aware AI orchestration.

## Implemented Components

### CPU and System Memory

**Module:** `monitoring/resources.py`

The resource monitoring component collects information about:

- CPU resources
- System memory
- Memory utilization
- Available system resources

The collected information provides a basic overview of the current system state.

### NUMA Monitoring

**Module:** `monitoring/numa.py`

The NUMA component discovers the system's NUMA topology and collects per-node memory information.

This is particularly relevant for systems with:

- Multiple CPU sockets
- Multiple NUMA nodes
- Large memory configurations
- Workloads with significant memory requirements

NUMA information provides a foundation for future hardware-aware workload placement.

### GPU Monitoring Architecture

**Module:** `monitoring/gpu.py`

The GPU monitoring subsystem provides a generic backend-based architecture.

Its responsibilities include:

- GPU information structures
- Device-specific monitoring snapshots
- Backend interfaces
- Device discovery
- Telemetry collection
- Monitoring error tracking

The architecture supports multiple devices and allows vendor-specific implementations to be added independently.

### Intel GPU Monitoring

The currently implemented vendor-specific backend focuses on Intel GPUs.

It uses Linux sysfs interfaces to collect available hardware telemetry.

Depending on device and driver support, information includes:

- GPU temperature
- Power consumption
- Power limits
- Energy information
- Frequency information

Not every telemetry field is available on every device.

### Multiple GPU Devices

GPU monitoring is designed around individual device snapshots.

This allows multiple GPUs to be represented independently.

The monitoring architecture distinguishes between:

- Monitoring unavailable
- Successful discovery without GPUs
- Successful collection of one or more GPU snapshots

Backend and device telemetry failures are tracked separately wherever possible.

## Central Monitoring Integration

**Module:** `monitoring/system.py`

The SystemMonitor coordinates the individual monitoring components.

It combines CPU, memory, NUMA, and GPU information into a unified system snapshot.

Independent collection operations are executed concurrently where appropriate.

The resulting snapshot provides a consistent representation of the collected system state.

## Architectural Considerations

Hardware monitoring must account for significant differences between systems.

These include:

- Different CPU architectures
- Different NUMA configurations
- Different GPU manufacturers
- Different GPU drivers
- Different telemetry interfaces
- Missing or unavailable hardware information

A common monitoring architecture allows higher-level components to consume structured information without depending directly on vendor-specific interfaces.

## Current Limitations

- Intel is the currently implemented vendor-specific GPU backend.
- NVIDIA GPU monitoring is planned.
- AMD GPU monitoring is planned.
- Available telemetry depends on hardware and driver support.
- Advanced hardware capability discovery is not yet implemented.
- Resource-aware workload scheduling is planned.

## Result

The platform gained an initial hardware monitoring foundation covering CPU resources, system memory, NUMA topology, and GPU monitoring.

This provides the basis for future health evaluation, diagnostics, and resource-aware AI orchestration.

## Future Improvements

- NVIDIA GPU backend
- AMD GPU backend
- Extended Intel GPU telemetry
- Additional hardware monitoring providers
- Hardware capability discovery
- Improved resource utilization monitoring
- Resource availability interfaces
- Hardware-aware workload scheduling

## Related Documentation

- [Architecture](../ARCHITECTURE.md)
- [Development History](../DEVELOPMENT.md)
- [Health and Diagnostics](05-health-and-diagnostics.md)
- [Testing Strategy](../TESTING.md)
- [Roadmap](../../ROADMAP.md)
- [Multi-GPU Architecture ADR](../adr/0002-multi-gpu-monitoring.md)
- [Error Isolation ADR](../adr/0003-monitoring-error-isolation.md)
