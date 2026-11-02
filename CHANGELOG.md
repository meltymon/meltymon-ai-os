
# Changelog

All notable changes to MELTYMON AI OS will be documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial modular Python package structure.
- YAML-based application configuration.
- Environment variable overrides for selected settings.
- Asynchronous Ollama backend integration.
- Ollama connection checks, model listing, model details, and text generation.
- Model catalog with normalized model metadata.
- CPU and system memory monitoring.
- NUMA topology and per-node memory monitoring.
- GPU monitoring interfaces supporting multiple devices and backends.
- Intel GPU detection and telemetry collection through Linux sysfs.
- System health evaluation with configurable thresholds.
- Rule-based diagnostic engine with severity classification.
- Central system monitoring orchestration.
- Monitoring service combining system snapshots, health evaluation, and diagnostics.
- Monitoring API for snapshot access and serialization.
- Recursive serialization of monitoring data into dictionaries and JSON.

### Changed

- Extended GPU monitoring from a single-device model to multi-device snapshots.
- Added device-specific health checks and diagnostic findings.
- Improved error isolation across monitoring components and GPU devices.
- Improved representation of unavailable monitoring data.
- Improved validation of health evaluation thresholds.
- Extended monitoring result handling for systems with multiple GPUs.

### Fixed

- Prevented individual GPU telemetry failures from interrupting collection from other devices.
- Isolated hardware detection errors from unrelated monitoring components.
- Improved handling of missing or unavailable telemetry values.
- Preserved device identifiers and backend information in diagnostic results.

### Tests

- Added automated tests for system monitoring and orchestration.
- Added tests for health evaluation and diagnostic rules.
- Added tests for monitoring service integration.
- Added multi-GPU monitoring test coverage.
- Added serialization tests for multiple GPU snapshots and empty GPU collections.

---

## Release History

No official releases have been published yet.
