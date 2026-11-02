
"""System health evaluation for MELTYMON AI OS."""

import math

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from meltymon_ai_os.monitoring.system import SystemSnapshot


class HealthStatus(str, Enum):
    """Possible system health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass(frozen=True)
class HealthThresholds:
    """Configurable thresholds for system health evaluation."""

    cpu_warning: float = 80.0
    cpu_critical: float = 95.0

    memory_warning: float = 85.0
    memory_critical: float = 95.0

    gpu_temperature_warning: float = 80.0
    gpu_temperature_critical: float = 90.0

    gpu_memory_warning: float = 90.0
    gpu_memory_critical: float = 97.0

    def __post_init__(self) -> None:
        """Validate all warning and critical threshold pairs."""
        pairs = (
            ("CPU", self.cpu_warning, self.cpu_critical),
            ("Memory", self.memory_warning, self.memory_critical),
            (
                "GPU temperature",
                self.gpu_temperature_warning,
                self.gpu_temperature_critical,
            ),
            (
                "GPU memory",
                self.gpu_memory_warning,
                self.gpu_memory_critical,
            ),
        )

        for name, warning, critical in pairs:
            if not math.isfinite(warning) or not math.isfinite(critical):
                raise ValueError(
                    f"{name} thresholds must be finite"
                )

            if warning < 0 or critical > 100:
                raise ValueError(
                    f"{name} thresholds must be between 0 and 100"
                )

            if warning >= critical:
                raise ValueError(
                    f"{name} warning threshold must be lower "
                    "than its critical threshold"
                )


@dataclass(frozen=True)
class HealthCheck:
    """Result of one individual health check."""

    name: str
    status: HealthStatus
    message: str
    value: float | int | str | None = None
    unit: str | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None


@dataclass(frozen=True)
class HealthReport:
    """Overall health assessment of a system snapshot."""

    timestamp: datetime
    status: HealthStatus
    checks: tuple[HealthCheck, ...]

    @property
    def healthy(self) -> bool:
        """Return whether the overall system is healthy."""
        return self.status is HealthStatus.HEALTHY

    @property
    def degraded_checks(self) -> tuple[HealthCheck, ...]:
        """Return all checks with degraded status."""
        return tuple(
            check
            for check in self.checks
            if check.status is HealthStatus.DEGRADED
        )

    @property
    def critical_checks(self) -> tuple[HealthCheck, ...]:
        """Return all checks with critical status."""
        return tuple(
            check
            for check in self.checks
            if check.status is HealthStatus.CRITICAL
        )


class HealthEvaluator:
    """Evaluate system snapshots and produce health reports."""

    def __init__(
        self,
        thresholds: HealthThresholds | None = None,
    ) -> None:
        """Initialize the evaluator with configurable thresholds."""
        self.thresholds = (
            thresholds
            if thresholds is not None
            else HealthThresholds()
        )

    @staticmethod
    def _missing_check(
        name: str,
        message: str,
    ) -> HealthCheck:
        """Create a degraded check for unavailable monitoring data."""
        return HealthCheck(
            name=name,
            status=HealthStatus.DEGRADED,
            message=message,
        )

    @staticmethod
    def _evaluate_range(
        name: str,
        value: float | int,
        unit: str,
        warning: float,
        critical: float,
        *,
        minimum: float = 0.0,
        maximum: float = 100.0,
    ) -> HealthCheck:
        """Evaluate a numeric measurement against its thresholds."""

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return HealthCheck(
                name=name,
                status=HealthStatus.DEGRADED,
                message="Invalid measurement type",
                value=str(value),
                unit=unit,
                warning_threshold=warning,
                critical_threshold=critical,
            )

        if (
            not math.isfinite(value)
            or not minimum <= value <= maximum
        ):
            return HealthCheck(
                name=name,
                status=HealthStatus.DEGRADED,
                message="Measurement is outside the valid range",
                value=value,
                unit=unit,
                warning_threshold=warning,
                critical_threshold=critical,
            )

        if value >= critical:
            status = HealthStatus.CRITICAL
            message = "Critical threshold exceeded"

        elif value >= warning:
            status = HealthStatus.DEGRADED
            message = "Warning threshold exceeded"

        else:
            status = HealthStatus.HEALTHY
            message = "Within normal range"

        return HealthCheck(
            name=name,
            status=status,
            message=message,
            value=value,
            unit=unit,
            warning_threshold=warning,
            critical_threshold=critical,
        )

    def evaluate(
        self,
        snapshot: SystemSnapshot,
    ) -> HealthReport:
        """Evaluate all available system monitoring components."""

        checks: list[HealthCheck] = []
        thresholds = self.thresholds

        # Report errors from individual monitoring components.
        for component, error in snapshot.errors.items():
            checks.append(
                self._missing_check(
                    component,
                    f"Monitoring error: {error}",
                )
            )

        # CPU and system memory.
        if snapshot.resources is None:
            if "resources" not in snapshot.errors:
                checks.append(
                    self._missing_check(
                        "resources",
                        "Resource monitoring data unavailable",
                    )
                )

        else:
            resources = snapshot.resources

            checks.append(
                self._evaluate_range(
                    "cpu",
                    resources.cpu_percent,
                    "%",
                    thresholds.cpu_warning,
                    thresholds.cpu_critical,
                )
            )

            checks.append(
                self._evaluate_range(
                    "memory",
                    resources.memory_percent,
                    "%",
                    thresholds.memory_warning,
                    thresholds.memory_critical,
                )
            )

        # NUMA topology and per-node memory.
        if snapshot.numa is None:
            if "numa" not in snapshot.errors:
                checks.append(
                    self._missing_check(
                        "numa",
                        "NUMA monitoring data unavailable",
                    )
                )

        elif snapshot.numa.node_count == 0:
            checks.append(
                self._missing_check(
                    "numa",
                    "No NUMA nodes detected",
                )
            )

        else:
            checks.append(
                HealthCheck(
                    name="numa",
                    status=HealthStatus.HEALTHY,
                    message=(
                        f"{snapshot.numa.node_count} NUMA node(s) detected"
                    ),
                    value=snapshot.numa.node_count,
                    unit="nodes",
                )
            )

            for node in snapshot.numa.nodes:
                if node.memory.total_bytes <= 0:
                    checks.append(
                        self._missing_check(
                            f"numa.node_{node.node_id}.memory",
                            "NUMA memory capacity unavailable",
                        )
                    )

                else:
                    checks.append(
                        self._evaluate_range(
                            f"numa.node_{node.node_id}.memory",
                            node.memory.memory_percent,
                            "%",
                            thresholds.memory_warning,
                            thresholds.memory_critical,
                        )
                    )

        # GPU temperature and memory usage.
        if snapshot.gpu is None:
            if "gpu" not in snapshot.errors:
                checks.append(
                    self._missing_check(
                        "gpu",
                        "GPU monitoring data unavailable",
                    )
                )

        else:
            gpu = snapshot.gpu

            if gpu.temperature_celsius is None:
                checks.append(
                    self._missing_check(
                        "gpu.temperature",
                        "GPU temperature measurement unavailable",
                    )
                )

            else:
                checks.append(
                    self._evaluate_range(
                        "gpu.temperature",
                        gpu.temperature_celsius,
                        "°C",
                        thresholds.gpu_temperature_warning,
                        thresholds.gpu_temperature_critical,
                        maximum=float("inf"),
                    )
                )

            gpu_memory_percent = gpu.memory_percent

            if gpu_memory_percent is None:
                checks.append(
                    self._missing_check(
                        "gpu.memory",
                        "GPU memory usage measurement unavailable",
                    )
                )

            else:
                checks.append(
                    self._evaluate_range(
                        "gpu.memory",
                        gpu_memory_percent,
                        "%",
                        thresholds.gpu_memory_warning,
                        thresholds.gpu_memory_critical,
                    )
                )

        # Determine the overall system health.
        if any(
            check.status is HealthStatus.CRITICAL
            for check in checks
        ):
            overall_status = HealthStatus.CRITICAL

        elif any(
            check.status is HealthStatus.DEGRADED
            for check in checks
        ):
            overall_status = HealthStatus.DEGRADED

        else:
            overall_status = HealthStatus.HEALTHY

        return HealthReport(
            timestamp=snapshot.timestamp,
            status=overall_status,
            checks=tuple(checks),
        )
