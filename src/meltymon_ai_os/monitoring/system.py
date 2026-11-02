"""Central system monitoring orchestration for MELTYMON AI OS."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from meltymon_ai_os.monitoring.gpu import GPUMonitor, GPUSnapshot
from meltymon_ai_os.monitoring.numa import NUMAMonitor, NUMASnapshot
from meltymon_ai_os.monitoring.resources import (
    ResourceMonitor,
    ResourceSnapshot,
)


@dataclass(frozen=True)
class SystemSnapshot:
    """Combined snapshot of all monitored system components.

    Individual component snapshots are optional. GPU monitoring uses
    a tuple because multiple devices can be present.

    GPU semantics:
        None: GPU collection failed.
        (): GPU collection succeeded, but no GPUs were detected.
        (snapshot, ...): Successfully collected GPU snapshots.
    """

    timestamp: datetime
    resources: ResourceSnapshot | None
    numa: NUMASnapshot | None
    gpu: tuple[GPUSnapshot, ...] | None
    errors: dict[str, str]

    @property
    def healthy(self) -> bool:
        """Return whether all monitoring components collected successfully."""
        return not self.errors

    @property
    def available_components(self) -> tuple[str, ...]:
        """Return the names of successfully collected components."""
        available: list[str] = []

        if self.resources is not None:
            available.append("resources")

        if self.numa is not None:
            available.append("numa")

        if self.gpu is not None:
            available.append("gpu")

        return tuple(available)


class SystemMonitor:
    """Coordinate CPU, RAM, NUMA and GPU monitoring."""

    def __init__(
        self,
        resource_monitor: ResourceMonitor | None = None,
        numa_monitor: NUMAMonitor | None = None,
        gpu_monitor: GPUMonitor | None = None,
    ) -> None:
        """Initialize the system monitor.

        Custom monitor instances can be injected for testing or
        specialized system configurations.
        """
        self.resource_monitor = (
            resource_monitor
            if resource_monitor is not None
            else ResourceMonitor()
        )

        self.numa_monitor = (
            numa_monitor
            if numa_monitor is not None
            else NUMAMonitor()
        )

        self.gpu_monitor = (
            gpu_monitor
            if gpu_monitor is not None
            else GPUMonitor()
        )

    @staticmethod
    async def _collect_component(
        name: str,
        monitor: object,
    ) -> tuple[str, object | None, str | None]:
        """Collect one component while isolating its errors."""
        try:
            collect = getattr(monitor, "collect")
            result = await collect()

            if result is None:
                return name, None, "No data returned"

            return name, result, None

        except Exception as exc:
            return name, None, f"{type(exc).__name__}: {exc}"

    async def collect(self) -> SystemSnapshot:
        """Collect a combined system snapshot asynchronously.

        All monitoring components run concurrently. A failure in one
        component does not prevent the others from returning data.

        GPU backend and device errors are additionally collected from
        GPUMonitor.errors. This allows successful GPU snapshots to be
        retained even when another GPU fails.
        """
        monitors = (
            ("resources", self.resource_monitor),
            ("numa", self.numa_monitor),
            ("gpu", self.gpu_monitor),
        )

        results = await asyncio.gather(
            *(
                self._collect_component(name, monitor)
                for name, monitor in monitors
            )
        )

        collected: dict[str, object | None] = {}
        errors: dict[str, str] = {}

        for name, result, error in results:
            collected[name] = result

            if error is not None:
                errors[name] = error

        # Preserve individual backend/device errors reported by GPUMonitor.
        gpu_errors = getattr(self.gpu_monitor, "errors", {})

        if isinstance(gpu_errors, dict):
            for component, error in gpu_errors.items():
                errors[component] = str(error)

        return SystemSnapshot(
            timestamp=datetime.now(timezone.utc),
            resources=collected["resources"],  # type: ignore[arg-type]
            numa=collected["numa"],  # type: ignore[arg-type]
            gpu=collected["gpu"],  # type: ignore[arg-type]
            errors=errors,
        )
