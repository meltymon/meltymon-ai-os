"""Hardware-independent GPU monitoring interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


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
        """Return GPU memory utilization as a percentage."""
        if (
            self.memory_used_bytes is None
            or self.memory_total_bytes is None
            or self.memory_total_bytes <= 0
        ):
            return None

        return self.memory_used_bytes / self.memory_total_bytes * 100.0


class BaseGPUBackend(ABC):
    """Abstract interface for vendor-specific GPU backends."""

    @abstractmethod
    async def detect(self) -> list[GPUInfo]:
        """Detect GPUs supported by this backend."""
        raise NotImplementedError

    @abstractmethod
    async def collect(self, gpu: GPUInfo) -> GPUSnapshot:
        """Collect telemetry for one GPU."""
        raise NotImplementedError


class GPUMonitor:
    """Discover GPUs and collect telemetry through independent backends.

    When no backend list is supplied, the Intel sysfs backend is enabled
    by default. Passing an explicit empty list disables GPU backends.

    Detection runs on every collection cycle so that newly added or
    removed devices are reflected in the next snapshot.
    """

    def __init__(
        self,
        backends: list[BaseGPUBackend] | None = None,
    ) -> None:
        """Initialize GPU monitoring.

        Args:
            backends: Explicit backend instances. If omitted, the Intel
                backend is registered automatically. An empty list
                explicitly disables GPU monitoring.
        """
        if backends is None:
            from meltymon_ai_os.monitoring.gpu_intel import (
                IntelGPUBackend,
            )

            self.backends: list[BaseGPUBackend] = [IntelGPUBackend()]
        else:
            self.backends = list(backends)

        self.detected_gpus: list[tuple[BaseGPUBackend, GPUInfo]] = []

        self.errors: dict[str, str] = {}

    @staticmethod
    def _backend_key(backend: BaseGPUBackend) -> str:
        """Create a stable, readable key for a backend."""
        name = type(backend).__name__

        name = name.removesuffix("GPUBackend")

        return name.lower() or "unknown"

    @staticmethod
    def _device_key(gpu: GPUInfo) -> str:
        """Create a readable key for an individual GPU."""
        identifier = gpu.device_id or gpu.name
        return f"gpu.{identifier}"

    async def detect(self) -> list[GPUInfo]:
        """Detect all GPUs while isolating backend failures.

        A failed backend does not prevent other backends from detecting
        their devices.
        """
        self.detected_gpus = []
        self.errors = {}

        detected: list[GPUInfo] = []

        for backend in self.backends:
            backend_key = self._backend_key(backend)

            try:
                devices = await backend.detect()

                if devices is None:
                    raise RuntimeError("Backend returned no detection result")

                for device in devices:
                    self.detected_gpus.append((backend, device))
                    detected.append(device)

            except Exception as exc:  # noqa: BLE001
                # Backend boundary: isolate failures per GPU backend.
                self.errors[f"gpu.backend.{backend_key}"] = (
                    f"{type(exc).__name__}: {exc}"
                )

        return detected

    async def collect(self) -> tuple[GPUSnapshot, ...]:
        """Detect GPUs and collect all available telemetry.

        Collection errors are recorded per device. Successful snapshots
        from other devices are preserved.
        """
        await self.detect()

        snapshots: list[GPUSnapshot] = []

        for backend, gpu in self.detected_gpus:
            device_key = self._device_key(gpu)

            try:
                snapshot = await backend.collect(gpu)

                if snapshot is None:
                    raise RuntimeError("Backend returned no telemetry snapshot")

                snapshots.append(snapshot)

            except Exception as exc:  # noqa: BLE001
                # Device boundary: preserve snapshots from other GPUs.
                self.errors[device_key] = f"{type(exc).__name__}: {exc}"

        return tuple(snapshots)


__all__ = [
    "BaseGPUBackend",
    "GPUInfo",
    "GPUMonitor",
    "GPUSnapshot",
]
