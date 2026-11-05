"""Public monitoring API for MELTYMON AI OS."""

from meltymon_ai_os.monitoring.serialization import (
    snapshot_to_dict,
    snapshot_to_json,
)
from meltymon_ai_os.monitoring.system import (
    SystemMonitor,
    SystemSnapshot,
)


class MonitoringAPI:
    """Provide a unified interface to system monitoring data.

    This class acts as a public access layer. It delegates hardware
    collection to SystemMonitor and data conversion to serialization.

    No hardware monitoring or serialization logic is duplicated here.
    """

    def __init__(
        self,
        monitor: SystemMonitor | None = None,
    ) -> None:
        """Initialize the monitoring API.

        A custom SystemMonitor can be injected for testing or for
        specialized monitoring configurations.
        """
        self.monitor = monitor if monitor is not None else SystemMonitor()

    async def get_snapshot(self) -> SystemSnapshot:
        """Collect and return a complete system snapshot."""
        return await self.monitor.collect()

    async def get_snapshot_dict(self) -> dict:
        """Collect a snapshot and return it as a dictionary."""
        snapshot = await self.get_snapshot()
        return snapshot_to_dict(snapshot)

    async def get_snapshot_json(
        self,
        *,
        indent: int | None = 2,
    ) -> str:
        """Collect a snapshot and return it as a JSON string."""
        snapshot = await self.get_snapshot()

        return snapshot_to_json(
            snapshot,
            indent=indent,
        )
