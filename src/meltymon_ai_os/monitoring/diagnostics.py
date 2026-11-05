"""Rule-based system diagnostics for MELTYMON AI OS."""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from meltymon_ai_os.monitoring.health import (
    HealthCheck,
    HealthReport,
    HealthStatus,
)


class DiagnosticSeverity(IntEnum):
    """Severity levels for diagnostic findings."""

    INFO = 0
    WARNING = 1
    CRITICAL = 2


@dataclass(frozen=True)
class DiagnosticFinding:
    """One diagnostic finding with an explanation and recommendation."""

    rule_id: str
    component: str
    severity: DiagnosticSeverity
    title: str
    explanation: str
    recommendation: str
    observed_value: float | int | str | None = None
    unit: str | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None


@dataclass(frozen=True)
class DiagnosticReport:
    """Collection of diagnostic findings for one system snapshot."""

    timestamp: datetime
    findings: tuple[DiagnosticFinding, ...]

    @property
    def severity(self) -> DiagnosticSeverity:
        """Return the highest severity found in this report."""
        if any(
            finding.severity is DiagnosticSeverity.CRITICAL for finding in self.findings
        ):
            return DiagnosticSeverity.CRITICAL

        if any(
            finding.severity is DiagnosticSeverity.WARNING for finding in self.findings
        ):
            return DiagnosticSeverity.WARNING

        return DiagnosticSeverity.INFO

    @property
    def healthy(self) -> bool:
        """Return whether no diagnostic findings were reported."""
        return not self.findings

    @property
    def critical_findings(self) -> tuple[DiagnosticFinding, ...]:
        """Return all critical findings."""
        return tuple(
            finding
            for finding in self.findings
            if finding.severity is DiagnosticSeverity.CRITICAL
        )

    @property
    def warning_findings(self) -> tuple[DiagnosticFinding, ...]:
        """Return all warning findings."""
        return tuple(
            finding
            for finding in self.findings
            if finding.severity is DiagnosticSeverity.WARNING
        )


class DiagnosticEngine:
    """Translate health checks into actionable diagnostic findings."""

    @staticmethod
    def _severity(status: HealthStatus) -> DiagnosticSeverity:
        """Map health status to diagnostic severity."""
        if status is HealthStatus.CRITICAL:
            return DiagnosticSeverity.CRITICAL

        if status is HealthStatus.DEGRADED:
            return DiagnosticSeverity.WARNING

        return DiagnosticSeverity.INFO

    @staticmethod
    def _gpu_component(check_name: str) -> str:
        """Return the GPU component associated with a health check."""
        if not check_name.startswith("gpu."):
            return "gpu"

        parts = check_name.split(".")

        # Per-device checks use:
        # gpu.<device_id>.temperature
        # gpu.<device_id>.memory
        if len(parts) >= 3 and parts[-1] in {"temperature", "memory"}:
            return ".".join(parts[:-1])

        # Preserve backend/device-specific monitoring error identifiers.
        return check_name

    @staticmethod
    def _gpu_metric(check_name: str) -> tuple[str, str] | None:
        """Extract the GPU device identifier and metric from a check name."""

        # Legacy compatibility: single-GPU check names.
        if check_name == "gpu.temperature":
            return "", "temperature"

        if check_name == "gpu.memory":
            return "", "memory"

        if not check_name.startswith("gpu."):
            return None

        # Multi-GPU check names:
        # gpu.<device_id>.temperature
        # gpu.<device_id>.memory
        for metric in ("temperature", "memory"):
            suffix = f".{metric}"

            if check_name.endswith(suffix):
                device_id = check_name[len("gpu.") : -len(suffix)]

                if device_id:
                    return device_id, metric

        return None

    @staticmethod
    def _diagnose_check(
        check: HealthCheck,
    ) -> DiagnosticFinding | None:
        """Create a finding for one health check."""

        if check.status is HealthStatus.HEALTHY:
            return None

        # Missing or invalid measurements are not hardware pressure.
        message_lower = check.message.lower()

        data_problem = (
            check.value is None
            or "invalid measurement" in message_lower
            or "outside the valid range" in message_lower
            or "monitoring error" in message_lower
        )

        if data_problem:
            if check.name.startswith("gpu"):
                recommendation = (
                    "Check GPU detection, driver status, sensor access "
                    "and monitoring backend availability."
                )
                component = DiagnosticEngine._gpu_component(check.name)

            elif check.name.startswith("numa"):
                recommendation = (
                    "Check NUMA topology detection, system permissions "
                    "and the availability of NUMA information."
                )
                component = check.name

            elif check.name == "resources":
                recommendation = (
                    "Check the resource monitoring backend and verify "
                    "that CPU and memory information can be read."
                )
                component = check.name

            else:
                recommendation = (
                    "Verify the monitoring source and measurement "
                    "validity before drawing conclusions."
                )
                component = check.name

            return DiagnosticFinding(
                rule_id="MONITORING_DATA_INVALID",
                component=component,
                severity=DiagnosticSeverity.WARNING,
                title=f"Monitoring data unavailable or invalid: {check.name}",
                explanation=check.message,
                recommendation=recommendation,
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        severity = DiagnosticEngine._severity(check.status)
        critical = severity is DiagnosticSeverity.CRITICAL

        # CPU utilization.
        if check.name == "cpu":
            return DiagnosticFinding(
                rule_id="CPU_PRESSURE",
                component="cpu",
                severity=severity,
                title=(
                    "Critical CPU utilization" if critical else "High CPU utilization"
                ),
                explanation=(
                    "CPU utilization has reached a critical level."
                    if critical
                    else "CPU utilization is elevated and may affect "
                    "system responsiveness."
                ),
                recommendation=(
                    "Inspect running processes and workloads. "
                    "Reduce unnecessary CPU-intensive tasks and check "
                    "for runaway processes."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # System memory.
        if check.name == "memory":
            return DiagnosticFinding(
                rule_id="MEMORY_PRESSURE",
                component="memory",
                severity=severity,
                title=(
                    "Critical memory pressure"
                    if critical
                    else "High memory utilization"
                ),
                explanation=(
                    "System memory utilization has reached a critical level."
                    if critical
                    else "System memory utilization is elevated."
                ),
                recommendation=(
                    "Identify memory-intensive processes, check for "
                    "memory leaks and reduce unnecessary workloads. "
                    "Consider whether additional RAM is required."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # Per-device GPU temperature and memory.
        gpu_metric = DiagnosticEngine._gpu_metric(check.name)

        if gpu_metric is not None:
            device_id, metric = gpu_metric

            component = f"gpu.{device_id}" if device_id else "gpu"

            if metric == "temperature":
                explanation = (
                    f"{check.message} (device {device_id})."
                    if device_id
                    else (
                        "GPU temperature has reached a critical threshold."
                        if critical
                        else "GPU temperature is elevated."
                    )
                )

                return DiagnosticFinding(
                    rule_id="GPU_TEMPERATURE",
                    component=component,
                    severity=severity,
                    title=(
                        f"Critical GPU temperature: {device_id}"
                        if critical and device_id
                        else (
                            "Critical GPU temperature"
                            if critical
                            else (
                                f"High GPU temperature: {device_id}"
                                if device_id
                                else "High GPU temperature"
                            )
                        )
                    ),
                    explanation=explanation,
                    recommendation=(
                        "Check GPU cooling, fan operation, airflow and "
                        "dust accumulation. Reduce GPU load if the "
                        "temperature remains critical."
                    ),
                    observed_value=check.value,
                    unit=check.unit,
                    warning_threshold=check.warning_threshold,
                    critical_threshold=check.critical_threshold,
                )

            explanation = (
                f"{check.message} (device {device_id})."
                if device_id
                else (
                    "GPU memory utilization has reached a critical level."
                    if critical
                    else "GPU memory utilization is elevated."
                )
            )

            return DiagnosticFinding(
                rule_id="GPU_MEMORY_PRESSURE",
                component=component,
                severity=severity,
                title=(
                    f"Critical GPU memory pressure: {device_id}"
                    if critical and device_id
                    else (
                        "Critical GPU memory pressure"
                        if critical
                        else (
                            f"High GPU memory utilization: {device_id}"
                            if device_id
                            else "High GPU memory utilization"
                        )
                    )
                ),
                explanation=explanation,
                recommendation=(
                    "Inspect GPU workloads and running models. "
                    "Unload unused models or reduce batch size, "
                    "context length or other memory-intensive settings."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # NUMA node memory.
        if check.name.startswith("numa.node_") and check.name.endswith(".memory"):
            node_id = check.name.split(".")[1].removeprefix("node_")

            return DiagnosticFinding(
                rule_id="NUMA_MEMORY_PRESSURE",
                component=f"numa.node_{node_id}",
                severity=severity,
                title=(
                    f"Critical memory pressure on NUMA node {node_id}"
                    if critical
                    else f"High memory utilization on NUMA node {node_id}"
                ),
                explanation=(
                    f"NUMA node {node_id} has reached a critical "
                    "memory utilization level."
                    if critical
                    else f"NUMA node {node_id} has elevated memory utilization."
                ),
                recommendation=(
                    "Inspect process memory allocation and NUMA "
                    "affinity. Check whether workloads are unevenly "
                    "distributed across NUMA nodes."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # NUMA topology or monitoring.
        if check.name == "numa":
            return DiagnosticFinding(
                rule_id="NUMA_MONITORING",
                component="numa",
                severity=severity,
                title="NUMA information unavailable",
                explanation=check.message,
                recommendation=(
                    "Check NUMA topology detection and system permissions. "
                    "Verify that the operating system exposes NUMA node "
                    "information."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # General system resource monitoring.
        if check.name == "resources":
            return DiagnosticFinding(
                rule_id="RESOURCE_MONITORING",
                component="resources",
                severity=severity,
                title="System resource monitoring unavailable",
                explanation=check.message,
                recommendation=(
                    "Check the resource monitoring backend and verify "
                    "that CPU and memory information can be read."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # GPU monitoring backend or device detection.
        if check.name == "gpu" or check.name.startswith("gpu."):
            return DiagnosticFinding(
                rule_id="GPU_MONITORING",
                component=DiagnosticEngine._gpu_component(check.name),
                severity=severity,
                title=f"GPU monitoring unavailable: {check.name}",
                explanation=check.message,
                recommendation=(
                    "Check GPU detection, driver status and monitoring "
                    "backend availability."
                ),
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        # Unknown or newly introduced health checks.
        return DiagnosticFinding(
            rule_id="UNCLASSIFIED_HEALTH_ISSUE",
            component=check.name,
            severity=severity,
            title=f"Unclassified issue: {check.name}",
            explanation=check.message,
            recommendation=(
                "Inspect the affected component and its monitoring data. "
                "A dedicated diagnostic rule may be required."
            ),
            observed_value=check.value,
            unit=check.unit,
            warning_threshold=check.warning_threshold,
            critical_threshold=check.critical_threshold,
        )

    def diagnose(self, report: HealthReport) -> DiagnosticReport:
        """Evaluate a health report and return actionable findings."""

        findings: list[DiagnosticFinding] = []

        for check in report.checks:
            finding = self._diagnose_check(check)

            if finding is not None:
                findings.append(finding)

        return DiagnosticReport(
            timestamp=report.timestamp,
            findings=tuple(findings),
        )
