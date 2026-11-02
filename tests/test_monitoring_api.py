
"""Tests for the public MELTYMON AI OS monitoring API."""

import asyncio
import json

from datetime import datetime, timezone

from meltymon_ai_os.monitoring.api import MonitoringAPI
from meltymon_ai_os.monitoring.system import SystemSnapshot


class FakeSystemMonitor:
    """Fake system monitor for API tests."""

    def __init__(self, snapshot: SystemSnapshot) -> None:
        self.snapshot = snapshot
        self.call_count = 0

    async def collect(self) -> SystemSnapshot:
        self.call_count += 1
        return self.snapshot


def create_snapshot() -> SystemSnapshot:
    """Create a representative system snapshot."""
    return SystemSnapshot(
        timestamp=datetime(
            2026, 11, 2, 18, 30, tzinfo=timezone.utc
        ),
        resources=None,
        numa=None,
        gpu=None,
        errors={"gpu": "GPU unavailable"},
    )


def test_api_returns_system_snapshot():
    snapshot = create_snapshot()
    monitor = FakeSystemMonitor(snapshot)
    api = MonitoringAPI(monitor=monitor)

    result = asyncio.run(api.get_snapshot())

    assert result is snapshot
    assert monitor.call_count == 1


def test_api_returns_snapshot_as_dictionary():
    snapshot = create_snapshot()
    monitor = FakeSystemMonitor(snapshot)
    api = MonitoringAPI(monitor=monitor)

    result = asyncio.run(api.get_snapshot_dict())

    assert isinstance(result, dict)
    assert result["resources"] is None
    assert result["numa"] is None
    assert result["gpu"] is None
    assert result["errors"] == {
        "gpu": "GPU unavailable"
    }
    assert result["timestamp"] == snapshot.timestamp.isoformat()
    assert monitor.call_count == 1


def test_api_returns_snapshot_as_json():
    snapshot = create_snapshot()
    monitor = FakeSystemMonitor(snapshot)
    api = MonitoringAPI(monitor=monitor)

    result = asyncio.run(api.get_snapshot_json())

    parsed = json.loads(result)

    assert isinstance(result, str)
    assert parsed["resources"] is None
    assert parsed["errors"]["gpu"] == "GPU unavailable"
    assert monitor.call_count == 1


def test_api_supports_compact_json():
    snapshot = create_snapshot()
    monitor = FakeSystemMonitor(snapshot)
    api = MonitoringAPI(monitor=monitor)

    result = asyncio.run(
        api.get_snapshot_json(indent=None)
    )

    assert "\n" not in result
    assert json.loads(result)["errors"]["gpu"] == "GPU unavailable"


def test_each_api_call_collects_a_fresh_snapshot():
    snapshot = create_snapshot()
    monitor = FakeSystemMonitor(snapshot)
    api = MonitoringAPI(monitor=monitor)

    asyncio.run(api.get_snapshot())
    asyncio.run(api.get_snapshot_dict())
    asyncio.run(api.get_snapshot_json())

    assert monitor.call_count == 3


def test_api_creates_default_monitor():
    api = MonitoringAPI()

    assert api.monitor is not None
