import inspect
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from meltymon_ai_os.monitoring.resources import (
    ResourceMonitor,
    ResourceSnapshot,
)


def test_resource_snapshot_memory_conversion():
    snapshot = ResourceSnapshot(
        timestamp=datetime.now(timezone.utc),
        cpu_percent=25.0,
        memory_percent=50.0,
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
        memory_used_bytes=8 * 1024**3,
        cpu_count=8,
    )

    assert snapshot.memory_used_gb == 8.0
    assert snapshot.memory_total_gb == 16.0


@pytest.mark.asyncio
async def test_collect_returns_resource_snapshot():
    monitor = ResourceMonitor()

    mock_memory = MagicMock()
    mock_memory.percent = 50.0
    mock_memory.total = 16 * 1024**3
    mock_memory.available = 8 * 1024**3
    mock_memory.used = 8 * 1024**3

    with (
        patch(
            "meltymon_ai_os.monitoring.resources.psutil.cpu_percent",
            return_value=25.0,
        ),
        patch(
            "meltymon_ai_os.monitoring.resources.psutil.virtual_memory",
            return_value=mock_memory,
        ),
    ):
        snapshot = await monitor.collect()

    assert isinstance(snapshot, ResourceSnapshot)
    assert snapshot.cpu_percent == 25.0
    assert snapshot.memory_percent == 50.0
    assert snapshot.memory_total_bytes == 16 * 1024**3
    assert snapshot.memory_available_bytes == 8 * 1024**3
    assert snapshot.memory_used_bytes == 8 * 1024**3
    assert snapshot.cpu_count >= 1
    assert snapshot.timestamp.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_collect_is_async():
    monitor = ResourceMonitor()

    assert inspect.iscoroutinefunction(monitor.collect)
