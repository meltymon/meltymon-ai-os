"""Tests for the central system monitoring orchestrator."""

import asyncio
from datetime import datetime, timezone

from meltymon_ai_os.monitoring.system import SystemMonitor


class FakeMonitor:
    """Simple asynchronous monitor for testing."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.called = False
        self.errors = {}

    async def collect(self):
        self.called = True

        if self.error is not None:
            raise self.error

        return self.result


def test_collect_returns_all_component_snapshots():
    resources = object()
    numa = object()
    gpu = (object(), object())

    resource_monitor = FakeMonitor(resources)
    numa_monitor = FakeMonitor(numa)
    gpu_monitor = FakeMonitor(gpu)

    monitor = SystemMonitor(
        resource_monitor=resource_monitor,
        numa_monitor=numa_monitor,
        gpu_monitor=gpu_monitor,
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.resources is resources
    assert snapshot.numa is numa
    assert snapshot.gpu is gpu
    assert snapshot.healthy is True
    assert snapshot.errors == {}

    assert snapshot.available_components == (
        "resources",
        "numa",
        "gpu",
    )

    assert resource_monitor.called
    assert numa_monitor.called
    assert gpu_monitor.called


def test_gpu_failure_does_not_affect_other_components():
    resources = object()
    numa = object()

    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(resources),
        numa_monitor=FakeMonitor(numa),
        gpu_monitor=FakeMonitor(
            error=RuntimeError("GPU unavailable")
        ),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.resources is resources
    assert snapshot.numa is numa
    assert snapshot.gpu is None
    assert snapshot.healthy is False
    assert "GPU unavailable" in snapshot.errors["gpu"]


def test_resource_failure_does_not_affect_other_components():
    numa = object()
    gpu = (object(),)

    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(
            error=OSError("Resource monitoring failed")
        ),
        numa_monitor=FakeMonitor(numa),
        gpu_monitor=FakeMonitor(gpu),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.resources is None
    assert snapshot.numa is numa
    assert snapshot.gpu is gpu
    assert "resources" in snapshot.errors


def test_multiple_component_failures_are_reported():
    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(
            error=RuntimeError("CPU monitoring failed")
        ),
        numa_monitor=FakeMonitor(
            error=RuntimeError("NUMA monitoring failed")
        ),
        gpu_monitor=FakeMonitor((object(),)),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.resources is None
    assert snapshot.numa is None
    assert snapshot.gpu is not None
    assert set(snapshot.errors) == {"resources", "numa"}


def test_none_result_is_reported_as_failure():
    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(None),
        numa_monitor=FakeMonitor(object()),
        gpu_monitor=FakeMonitor((object(),)),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.resources is None
    assert snapshot.errors["resources"] == "No data returned"
    assert snapshot.numa is not None
    assert snapshot.gpu is not None


def test_snapshot_contains_utc_timestamp():
    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(object()),
        numa_monitor=FakeMonitor(object()),
        gpu_monitor=FakeMonitor(()),
    )

    snapshot = asyncio.run(monitor.collect())

    assert isinstance(snapshot.timestamp, datetime)
    assert snapshot.timestamp.tzinfo == timezone.utc


def test_available_components_is_empty_when_all_fail():
    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(
            error=RuntimeError("Resources unavailable")
        ),
        numa_monitor=FakeMonitor(
            error=RuntimeError("NUMA unavailable")
        ),
        gpu_monitor=FakeMonitor(
            error=RuntimeError("GPU unavailable")
        ),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.available_components == ()
    assert snapshot.healthy is False
    assert len(snapshot.errors) == 3


def test_gpu_backend_errors_are_preserved():
    gpu_monitor = FakeMonitor(
        result=(object(),),
    )
    gpu_monitor.errors = {
        "gpu.0000:02:00.0": "RuntimeError: Telemetry unavailable",
        "gpu.backend.nvidia": "RuntimeError: Driver unavailable",
    }

    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(object()),
        numa_monitor=FakeMonitor(object()),
        gpu_monitor=gpu_monitor,
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.gpu == (gpu_monitor.result[0],)
    assert snapshot.errors == gpu_monitor.errors
    assert snapshot.healthy is False


def test_empty_gpu_tuple_is_successful_collection():
    monitor = SystemMonitor(
        resource_monitor=FakeMonitor(object()),
        numa_monitor=FakeMonitor(object()),
        gpu_monitor=FakeMonitor(()),
    )

    snapshot = asyncio.run(monitor.collect())

    assert snapshot.gpu == ()
    assert "gpu" in snapshot.available_components
    assert snapshot.healthy is True
    assert snapshot.errors == {}


def test_system_monitor_integrates_real_components():
    """Test integration with the actual monitoring modules."""

    monitor = SystemMonitor()
    snapshot = asyncio.run(monitor.collect())

    assert snapshot is not None
    assert snapshot.timestamp is not None

    if snapshot.resources is not None:
        assert snapshot.resources.cpu_count > 0
        assert snapshot.resources.memory_total_bytes > 0
        assert 0 <= snapshot.resources.cpu_percent <= 100

    if snapshot.numa is not None:
        assert snapshot.numa.node_count >= 0

    if snapshot.gpu is not None:
        assert isinstance(snapshot.gpu, tuple)

    for component, error in snapshot.errors.items():
        assert (
            component in ("resources", "numa", "gpu")
            or component.startswith("gpu.")
        )
        assert isinstance(error, str)
        assert error
