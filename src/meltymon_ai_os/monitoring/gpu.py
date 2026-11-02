
"""Hardware-independent GPU monitoring interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GPUInfo:
    """Normalized information about a detected GPU."""

    name: str
    vendor: str
    driver: str | None = None
    device_id: str | None = None
    backend: str = "unknown"


@dataclass(frozen=True)
class GPUSnapshot:
    """Snapshot of GPU utilization and hardware telemetry."""

    timestamp: datetime
    gpu: GPUInfo
    utilization_percent: float | None = None
    memory_used_bytes: int | None = None
    memory_total_bytes: int | None = None
    temperature_celsius: float | None = None
    power_watts: float | None = None
    power_limit_watts: float | None = None
    energy_joules: float | None = None
    current_frequency_mhz: int | None = None
    max_frequency_mhz: int | None = None
    boost_frequency_mhz: int | None = None

    @property
    def memory_percent(self) -> float | None:
        """Return GPU memory utilization in percent."""

        if (
            self.memory_used_bytes is None
            or self.memory_total_bytes is None
            or self.memory_total_bytes <= 0
        ):
            return None

        return (
            self.memory_used_bytes
            / self.memory_total_bytes
            * 100.0
        )


class BaseGPUBackend(ABC):
    """Abstract interface for vendor-specific GPU monitoring."""

    @abstractmethod
    async def detect(self) -> list[GPUInfo]:
        """Detect available GPUs."""
        raise NotImplementedError

    @abstractmethod
    async def collect(self, gpu: GPUInfo) -> GPUSnapshot:
        """Collect utilization and hardware information."""
        raise NotImplementedError


class GPUMonitor:
    """Coordinate GPU detection and resource collection."""

    def __init__(
        self,
        backends: list[BaseGPUBackend] | None = None,
    ) -> None:
        self.backends = backends or []
        self.detected_gpus: list[
            tuple[BaseGPUBackend, GPUInfo]
        ] = []

    async def detect(self) -> list[GPUInfo]:
        """Detect GPUs using all registered backends."""

        self.detected_gpus = []

        for backend in self.backends:
            devices = await backend.detect()

            for device in devices:
                self.detected_gpus.append((backend, device))

        return [
            device
            for _, device in self.detected_gpus
        ]

    async def collect(self) -> list[GPUSnapshot]:
        """Collect snapshots from all detected GPUs."""

        snapshots = []

        for backend, gpu in self.detected_gpus:
            snapshot = await backend.collect(gpu)
            snapshots.append(snapshot)

        return snapshots
