"""Tests for hardware-independent GPU monitoring."""

from datetime import UTC, datetime

import pytest

from meltymon_ai_os.monitoring.gpu import (
    BaseGPUBackend,
    GPUInfo,
    GPUMonitor,
    GPUSnapshot,
)


class FakeGPUBackend(BaseGPUBackend):
    """Simulated GPU backend for unit testing."""

    def __init__(
        self,
        devices=None,
        *,
        detect_error=None,
        collect_errors=None,
    ):
        self.devices = (
            devices
            if devices is not None
            else [
                GPUInfo(
                    name="Test GPU",
                    vendor="TestVendor",
                    driver="test-driver",
                    device_id="0000:01:00.0",
                    backend="test",
                )
            ]
        )
        self.detect_error = detect_error
        self.collect_errors = collect_errors or {}
        self.detect_calls = 0
        self.collect_calls = []

    async def detect(self) -> list[GPUInfo]:
        self.detect_calls += 1

        if self.detect_error is not None:
            raise self.detect_error

        return self.devices

    async def collect(self, gpu: GPUInfo) -> GPUSnapshot:
        self.collect_calls.append(gpu.device_id)

        if gpu.device_id in self.collect_errors:
            raise self.collect_errors[gpu.device_id]

        return GPUSnapshot(
            timestamp=datetime.now(UTC),
            gpu=gpu,
            utilization_percent=45.0,
            memory_used_bytes=4 * 1024**3,
            memory_total_bytes=8 * 1024**3,
        )


def create_gpu(
    name: str,
    device_id: str,
) -> GPUInfo:
    return GPUInfo(
        name=name,
        vendor="TestVendor",
        driver="test-driver",
        device_id=device_id,
        backend="test",
    )


def test_gpu_info_creation():
    gpu = GPUInfo(
        name="Intel Arc A750",
        vendor="Intel",
        driver="i915",
        backend="intel",
    )

    assert gpu.name == "Intel Arc A750"
    assert gpu.vendor == "Intel"
    assert gpu.driver == "i915"


def test_gpu_snapshot_memory_percent():
    gpu = create_gpu("Test GPU", "0000:01:00.0")

    snapshot = GPUSnapshot(
        timestamp=datetime.now(UTC),
        gpu=gpu,
        memory_used_bytes=4 * 1024**3,
        memory_total_bytes=8 * 1024**3,
    )

    assert snapshot.memory_percent == 50.0


def test_gpu_snapshot_without_memory_information():
    gpu = create_gpu("Test GPU", "0000:01:00.0")

    snapshot = GPUSnapshot(
        timestamp=datetime.now(UTC),
        gpu=gpu,
    )

    assert snapshot.memory_percent is None


@pytest.mark.asyncio
async def test_gpu_monitor_detect():
    backend = FakeGPUBackend()
    monitor = GPUMonitor(backends=[backend])

    detected = await monitor.detect()

    assert len(detected) == 1
    assert detected[0].name == "Test GPU"
    assert monitor.errors == {}


@pytest.mark.asyncio
async def test_gpu_monitor_collect():
    backend = FakeGPUBackend()
    monitor = GPUMonitor(backends=[backend])

    snapshots = await monitor.collect()

    assert len(snapshots) == 1
    assert snapshots[0].utilization_percent == 45.0
    assert snapshots[0].memory_percent == 50.0
    assert isinstance(snapshots, tuple)


@pytest.mark.asyncio
async def test_gpu_monitor_collects_multiple_gpus():
    devices = [
        create_gpu("GPU 0", "0000:01:00.0"),
        create_gpu("GPU 1", "0000:02:00.0"),
        create_gpu("GPU 2", "0000:03:00.0"),
    ]

    backend = FakeGPUBackend(devices=devices)
    monitor = GPUMonitor(backends=[backend])

    snapshots = await monitor.collect()

    assert len(snapshots) == 3
    assert [snapshot.gpu.device_id for snapshot in snapshots] == [
        "0000:01:00.0",
        "0000:02:00.0",
        "0000:03:00.0",
    ]


@pytest.mark.asyncio
async def test_gpu_monitor_isolates_device_collection_errors():
    devices = [
        create_gpu("GPU 0", "0000:01:00.0"),
        create_gpu("GPU 1", "0000:02:00.0"),
        create_gpu("GPU 2", "0000:03:00.0"),
    ]

    backend = FakeGPUBackend(
        devices=devices,
        collect_errors={
            "0000:02:00.0": RuntimeError("Telemetry unavailable"),
        },
    )

    monitor = GPUMonitor(backends=[backend])

    snapshots = await monitor.collect()

    assert len(snapshots) == 2
    assert {snapshot.gpu.device_id for snapshot in snapshots} == {
        "0000:01:00.0",
        "0000:03:00.0",
    }

    assert "gpu.0000:02:00.0" in monitor.errors
    assert "Telemetry unavailable" in monitor.errors["gpu.0000:02:00.0"]


@pytest.mark.asyncio
async def test_gpu_monitor_isolates_backend_detection_errors():
    working_gpu = create_gpu("Working GPU", "0000:02:00.0")

    broken_backend = FakeGPUBackend(detect_error=RuntimeError("Detection failed"))
    working_backend = FakeGPUBackend(devices=[working_gpu])

    monitor = GPUMonitor(
        backends=[
            broken_backend,
            working_backend,
        ]
    )

    snapshots = await monitor.collect()

    assert len(snapshots) == 1
    assert snapshots[0].gpu == working_gpu
    assert "gpu.backend.fake" in monitor.errors
    assert "Detection failed" in monitor.errors["gpu.backend.fake"]


@pytest.mark.asyncio
async def test_gpu_monitor_returns_empty_tuple_without_devices():
    backend = FakeGPUBackend(devices=[])
    monitor = GPUMonitor(backends=[backend])

    snapshots = await monitor.collect()

    assert snapshots == ()
    assert monitor.errors == {}


@pytest.mark.asyncio
async def test_gpu_monitor_refreshes_detection_each_cycle():
    first_gpu = create_gpu("GPU 0", "0000:01:00.0")
    second_gpu = create_gpu("GPU 1", "0000:02:00.0")

    backend = FakeGPUBackend(devices=[first_gpu])
    monitor = GPUMonitor(backends=[backend])

    first_snapshots = await monitor.collect()

    backend.devices = [second_gpu]

    second_snapshots = await monitor.collect()

    assert first_snapshots[0].gpu == first_gpu
    assert second_snapshots[0].gpu == second_gpu
    assert backend.detect_calls == 2


def test_gpu_monitor_uses_intel_backend_by_default():
    from meltymon_ai_os.monitoring.gpu_intel import (
        IntelGPUBackend,
    )

    monitor = GPUMonitor()

    assert len(monitor.backends) == 1
    assert isinstance(monitor.backends[0], IntelGPUBackend)


def test_gpu_monitor_accepts_explicit_empty_backend_list():
    monitor = GPUMonitor(backends=[])

    assert monitor.backends == []
