
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
            finding.severity is DiagnosticSeverity.CRITICAL
            for finding in self.findings
        ):
            return DiagnosticSeverity.CRITICAL

        if any(
            finding.severity is DiagnosticSeverity.WARNING
            for finding in self.findings
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
            elif check.name.startswith("numa"):
                recommendation = (
                    "Check NUMA topology detection, system permissions "
                    "and the availability of NUMA information."
                )
            elif check.name == "resources":
                recommendation = (
                    "Check the resource monitoring backend and verify "
                    "that CPU and memory information can be read."
                )
            else:
                recommendation = (
                    "Verify the monitoring source and measurement "
                    "validity before drawing conclusions."
                )

            return DiagnosticFinding(
                rule_id="MONITORING_DATA_INVALID",
                component=check.name,
                severity=DiagnosticSeverity.WARNING,
                title=(
                    f"Monitoring data unavailable or invalid: {check.name}"
                ),
                explanation=check.message,
                recommendation=recommendation,
                observed_value=check.value,
                unit=check.unit,
                warning_threshold=check.warning_threshold,
                critical_threshold=check.critical_threshold,
            )

        severity = DiagnosticEngine._severity(check.status)
        critical = severity is DiagnosticSeverity.CRITICAL

        common = {
            "severity": severity,
            "observed_value": check.value,
            "unit": check.unit,
            "warning_threshold": check.warning_threshold,
            "critical_threshold": check.critical_threshold,
        }

        # CPU utilization.
        if check.name == "cpu":
            return DiagnosticFinding(
                rule_id="CPU_PRESSURE",
                component="cpu",
                title=(
                    "Critical CPU utilization"
                    if critical
                    else "High CPU utilization"
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
                **common,
            )

        # System memory.
        if check.name == "memory":
            return DiagnosticFinding(
                rule_id="MEMORY_PRESSURE",
                component="memory",
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
                **common,
            )

        # GPU temperature.
        if check.name == "gpu.temperature":
            return DiagnosticFinding(
                rule_id="GPU_TEMPERATURE",
                component="gpu",
                title=(
                    "Critical GPU temperature"
                    if critical
                    else "High GPU temperature"
                ),
                explanation=(
                    "The GPU temperature has reached a critical threshold."
                    if critical
                    else "The GPU temperature is elevated."
                ),
                recommendation=(
                    "Check GPU cooling, fan operation, airflow and "
                    "dust accumulation. Reduce GPU load if the "
                    "temperature remains critical."
                ),
                **common,
            )

        # GPU memory.
        if check.name == "gpu.memory":
            return DiagnosticFinding(
                rule_id="GPU_MEMORY_PRESSURE",
                component="gpu",
                title=(
                    "Critical GPU memory pressure"
                    if critical
                    else "High GPU memory utilization"
                ),
                explanation=(
                    "GPU memory utilization has reached a critical level."
                    if critical
                    else "GPU memory utilization is elevated."
                ),
                recommendation=(
                    "Inspect GPU workloads and running models. "
                    "Unload unused models or reduce batch size, "
                    "context length or other memory-intensive settings."
                ),
                **common,
            )

        # NUMA node memory.
        if (
            check.name.startswith("numa.node_")
            and check.name.endswith(".memory")
        ):
            node_id = check.name.split(".")[1].removeprefix("node_")

            return DiagnosticFinding(
                rule_id="NUMA_MEMORY_PRESSURE",
                component=f"numa.node_{node_id}",
                title=(
                    f"Critical memory pressure on NUMA node {node_id}"
                    if critical
                    else f"High memory utilization on NUMA node {node_id}"
                ),
                explanation=(
                    f"NUMA node {node_id} has reached a critical "
                    "memory utilization level."
                    if critical
                    else f"NUMA node {node_id} has elevated "
                    "memory utilization."
                ),
                recommendation=(
                    "Inspect process memory allocation and NUMA "
                    "affinity. Check whether workloads are unevenly "
                    "distributed across NUMA nodes."
                ),
                **common,
            )

        # NUMA topology or monitoring.
        if check.name == "numa":
            return DiagnosticFinding(
                rule_id="NUMA_MONITORING",
                component="numa",
                title="NUMA information unavailable",
                explanation=check.message,
                recommendation=(
                    "Check NUMA topology detection and system permissions. "
                    "Verify that the operating system exposes NUMA node "
                    "information."
                ),
                **common,
            )

        # General system resource monitoring.
        if check.name == "resources":
            return DiagnosticFinding(
                rule_id="RESOURCE_MONITORING",
                component="resources",
                title="System resource monitoring unavailable",
                explanation=check.message,
                recommendation=(
                    "Check the resource monitoring backend and verify "
                    "that CPU and memory information can be read."
                ),
                **common,
            )

        # GPU monitoring backend.
        if check.name == "gpu":
            return DiagnosticFinding(
                rule_id="GPU_MONITORING",
                component="gpu",
                title="GPU monitoring unavailable",
                explanation=check.message,
                recommendation=(
                    "Check GPU detection, driver status and monitoring "
                    "backend availability."
                ),
                **common,
            )

        # Unknown or newly introduced health checks.
        return DiagnosticFinding(
            rule_id="UNCLASSIFIED_HEALTH_ISSUE",
            component=check.name,
            title=f"Unclassified issue: {check.name}",
            explanation=check.message,
            recommendation=(
                "Inspect the affected component and its monitoring data. "
                "A dedicated diagnostic rule may be required."
            ),
            **common,
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
