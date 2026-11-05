"""Tests for the integrated MELTYMON AI OS monitoring service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from meltymon_ai_os.monitoring.diagnostics import (
    DiagnosticReport,
)
from meltymon_ai_os.monitoring.gpu import GPUInfo, GPUSnapshot
from meltymon_ai_os.monitoring.health import (
    HealthReport,
    HealthStatus,
)
from meltymon_ai_os.monitoring.numa import (
    NUMAMemoryStats,
    NUMANode,
    NUMASnapshot,
)
from meltymon_ai_os.monitoring.resources import ResourceSnapshot
from meltymon_ai_os.monitoring.service import (
    MonitoringResult,
    MonitoringService,
)
from meltymon_ai_os.monitoring.system import (
    SystemSnapshot,
)

_TIMESTAMP = datetime(2026, 11, 2, tzinfo=UTC)


def create_snapshot(
    *,
    cpu_percent: float = 20.0,
    memory_percent: float = 40.0,
    gpu_temperature: float = 50.0,
    gpu_memory_used: int = 40,
    errors: dict[str, str] | None = None,
) -> SystemSnapshot:
    """Create a representative complete system snapshot."""

    resources = ResourceSnapshot(
        timestamp=_TIMESTAMP,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        memory_total_bytes=100,
        memory_available_bytes=100 - int(memory_percent),
        memory_used_bytes=int(memory_percent),
        cpu_count=56,
    )

    numa_memory = NUMAMemoryStats(
        total_bytes=100,
        free_bytes=60,
        used_bytes=40,
        statistics={},
    )

    numa_node = NUMANode(
        node_id=0,
        cpus=(0, 1, 2, 3),
        memory=numa_memory,
        distances=(10,),
    )

    numa = NUMASnapshot(
        timestamp=_TIMESTAMP,
        nodes=(numa_node,),
    )

    gpu = GPUSnapshot(
        timestamp=_TIMESTAMP,
        gpu=GPUInfo(
            name="Intel Arc A750",
            vendor="Intel",
            driver="i915",
            device_id="8086:56a1",
            backend="intel",
        ),
        temperature_celsius=gpu_temperature,
        memory_used_bytes=gpu_memory_used,
        memory_total_bytes=100,
    )

    return SystemSnapshot(
        timestamp=_TIMESTAMP,
        resources=resources,
        numa=numa,
        gpu=(gpu,),
        errors=errors or {},
    )


@pytest.mark.asyncio
async def test_service_collects_complete_monitoring_result():
    service = MonitoringService()

    result = await service.collect()

    assert isinstance(result, MonitoringResult)
    assert isinstance(result.snapshot, SystemSnapshot)
    assert isinstance(result.health, HealthReport)
    assert isinstance(result.diagnostics, DiagnosticReport)


@pytest.mark.asyncio
async def test_default_service_reports_healthy_system():
    snapshot = create_snapshot()

    monitor = Mock()
    monitor.collect = AsyncMock(return_value=snapshot)

    service = MonitoringService(monitor=monitor)

    result = await service.collect()

    assert result.health.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_service_generates_cpu_diagnostic():
    snapshot = create_snapshot(cpu_percent=85.0)

    monitor = Mock()
    monitor.collect = AsyncMock(return_value=snapshot)

    service = MonitoringService(monitor=monitor)

    result = await service.collect()

    assert result.health.status == HealthStatus.DEGRADED
    assert result.diagnostics.findings


@pytest.mark.asyncio
async def test_service_generates_critical_gpu_diagnostic():
    snapshot = create_snapshot(gpu_temperature=95.0)

    monitor = Mock()
    monitor.collect = AsyncMock(return_value=snapshot)

    service = MonitoringService(monitor=monitor)

    result = await service.collect()

    assert result.health.status == HealthStatus.CRITICAL
    assert result.diagnostics.findings


@pytest.mark.asyncio
async def test_service_preserves_snapshot_timestamp():
    snapshot = create_snapshot()

    monitor = Mock()
    monitor.collect = AsyncMock(return_value=snapshot)

    service = MonitoringService(monitor=monitor)

    result = await service.collect()

    assert result.snapshot.timestamp == _TIMESTAMP
