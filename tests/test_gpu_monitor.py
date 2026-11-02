
from datetime import datetime, timezone

import pytest

from meltymon_ai_os.monitoring.gpu import (
    BaseGPUBackend,
    GPUInfo,
    GPUMonitor,
    GPUSnapshot,
)


class FakeGPUBackend(BaseGPUBackend):
    """Simulated GPU backend for unit testing."""

    async def detect(self) -> list[GPUInfo]:
        return [
            GPUInfo(
                name="Test GPU",
                vendor="TestVendor",
                driver="test-driver",
                device_id="0000:01:00.0",
                backend="test",
            )
        ]

    async def collect(self, gpu: GPUInfo) -> GPUSnapshot:
        return GPUSnapshot(
            timestamp=datetime.now(timezone.utc),
            gpu=gpu,
            utilization_percent=45.0,
            memory_used_bytes=4 * 1024**3,
            memory_total_bytes=8 * 1024**3,
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
    gpu = GPUInfo(
        name="Test GPU",
        vendor="TestVendor",
    )

    snapshot = GPUSnapshot(
        timestamp=datetime.now(timezone.utc),
        gpu=gpu,
        memory_used_bytes=4 * 1024**3,
        memory_total_bytes=8 * 1024**3,
    )

    assert snapshot.memory_percent == 50.0


def test_gpu_snapshot_without_memory_information():
    gpu = GPUInfo(
        name="Test GPU",
        vendor="TestVendor",
    )

    snapshot = GPUSnapshot(
        timestamp=datetime.now(timezone.utc),
        gpu=gpu,
    )

    assert snapshot.memory_percent is None


@pytest.mark.asyncio
async def test_gpu_monitor_detect():
    monitor = GPUMonitor(
        backends=[FakeGPUBackend()]
    )

    detected = await monitor.detect()

    assert len(detected) == 1
    assert detected[0].name == "Test GPU"


@pytest.mark.asyncio
async def test_gpu_monitor_collect():
    monitor = GPUMonitor(
        backends=[FakeGPUBackend()]
    )

    await monitor.detect()
    snapshots = await monitor.collect()

    assert len(snapshots) == 1
    assert snapshots[0].utilization_percent == 45.0
    assert snapshots[0].memory_percent == 50.0
