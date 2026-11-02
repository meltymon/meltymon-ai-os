
"""System resource monitoring for MELTYMON AI OS."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil


@dataclass(frozen=True)
class ResourceSnapshot:
    """A snapshot of the current system resource usage."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_total_bytes: int
    memory_available_bytes: int
    memory_used_bytes: int
    cpu_count: int

    @property
    def memory_used_gb(self) -> float:
        """Return used memory in GiB."""
        return self.memory_used_bytes / (1024 ** 3)

    @property
    def memory_total_gb(self) -> float:
        """Return total memory in GiB."""
        return self.memory_total_bytes / (1024 ** 3)


class ResourceMonitor:
    """Monitor CPU and RAM usage asynchronously."""

    def __init__(self) -> None:
        """Initialize the resource monitor."""
        self._cpu_count = psutil.cpu_count(logical=True) or 1

    async def collect(self) -> ResourceSnapshot:
        """Collect a snapshot of current system resources.

        CPU measurement runs in a worker thread so that the
        asyncio event loop is not blocked.
        """

        cpu_percent = await asyncio.to_thread(
            psutil.cpu_percent,
            interval=0.1,
        )

        memory = psutil.virtual_memory()

        return ResourceSnapshot(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_total_bytes=memory.total,
            memory_available_bytes=memory.available,
            memory_used_bytes=memory.used,
            cpu_count=self._cpu_count,
        )
