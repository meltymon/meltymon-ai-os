
"""Tests for MELTYMON AI OS diagnostic engine."""

from datetime import datetime, timezone

import pytest

from meltymon_ai_os.monitoring.diagnostics import (
    DiagnosticEngine,
    DiagnosticSeverity,
)
from meltymon_ai_os.monitoring.health import (
    HealthCheck,
    HealthReport,
    HealthStatus,
)


_TIMESTAMP = datetime(2026, 11, 2, tzinfo=timezone.utc)


def create_check(
    name: str,
    status: HealthStatus,
    *,
    message: str = "Test measurement",
    value: float | int | str | None = 50.0,
    unit: str | None = "%",
    warning: float | None = 80.0,
    critical: float | None = 95.0,
) -> HealthCheck:
    return HealthCheck(
        name=name,
        status=status,
        message=message,
        value=value,
        unit=unit,
        warning_threshold=warning,
        critical_threshold=critical,
    )


def create_report(*checks: HealthCheck) -> HealthReport:
    return HealthReport(
        timestamp=_TIMESTAMP,
        status=(
            HealthStatus.CRITICAL
            if any(
                check.status is HealthStatus.CRITICAL
                for check in checks
            )
            else (
                HealthStatus.DEGRADED
                if any(
                    check.status is HealthStatus.DEGRADED
                    for check in checks
                )
                else HealthStatus.HEALTHY
            )
        ),
        checks=tuple(checks),
    )


def test_healthy_report_has_no_findings():
    report = create_report(
        create_check("cpu", HealthStatus.HEALTHY),
        create_check("memory", HealthStatus.HEALTHY),
    )

    result = DiagnosticEngine().diagnose(report)

    assert result.findings == ()
    assert result.healthy is True
    assert result.severity is DiagnosticSeverity.INFO


def test_cpu_warning_creates_warning_finding():
    report = create_report(
        create_check(
            "cpu",
            HealthStatus.DEGRADED,
            value=85.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.rule_id == "CPU_PRESSURE"
    assert finding.component == "cpu"
    assert finding.severity is DiagnosticSeverity.WARNING
    assert finding.observed_value == 85.0
    assert "CPU" in finding.title
    assert finding.recommendation


def test_cpu_critical_creates_critical_finding():
    report = create_report(
        create_check(
            "cpu",
            HealthStatus.CRITICAL,
            value=97.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "CPU_PRESSURE"
    assert finding.severity is DiagnosticSeverity.CRITICAL
    assert result.severity is DiagnosticSeverity.CRITICAL


def test_memory_pressure_creates_memory_finding():
    report = create_report(
        create_check(
            "memory",
            HealthStatus.DEGRADED,
            value=90.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "MEMORY_PRESSURE"
    assert finding.component == "memory"
    assert "memory" in finding.title.lower()


def test_gpu_temperature_creates_temperature_finding():
    report = create_report(
        create_check(
            "gpu.temperature",
            HealthStatus.CRITICAL,
            value=95.0,
            unit="°C",
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "GPU_TEMPERATURE"
    assert finding.component == "gpu"
    assert finding.severity is DiagnosticSeverity.CRITICAL
    assert finding.unit == "°C"
    assert "cooling" in finding.recommendation.lower()


def test_gpu_memory_creates_memory_finding():
    report = create_report(
        create_check(
            "gpu.memory",
            HealthStatus.DEGRADED,
            value=92.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "GPU_MEMORY_PRESSURE"
    assert finding.component == "gpu"
    assert finding.severity is DiagnosticSeverity.WARNING
    assert "models" in finding.recommendation.lower()


def test_numa_node_memory_creates_node_specific_finding():
    report = create_report(
        create_check(
            "numa.node_1.memory",
            HealthStatus.CRITICAL,
            value=98.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "NUMA_MEMORY_PRESSURE"
    assert finding.component == "numa.node_1"
    assert finding.severity is DiagnosticSeverity.CRITICAL
    assert "NUMA node 1" in finding.title


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("gpu.temperature", "GPU temperature measurement unavailable"),
        ("gpu.memory", "GPU memory usage measurement unavailable"),
        ("numa.node_0.memory", "NUMA memory capacity unavailable"),
        ("resources", "Resource monitoring data unavailable"),
        ("gpu", "Monitoring error: GPU unavailable"),
        ("numa", "No NUMA nodes detected"),
    ],
)
def test_missing_measurement_creates_data_finding(name, message):
    report = create_report(
        create_check(
            name,
            HealthStatus.DEGRADED,
            message=message,
            value=None,
            unit=None,
            warning=None,
            critical=None,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.rule_id == "MONITORING_DATA_INVALID"
    assert finding.severity is DiagnosticSeverity.WARNING
    assert finding.observed_value is None
    assert "unavailable" in finding.title.lower()


def test_invalid_measurement_creates_data_finding():
    report = create_report(
        create_check(
            "cpu",
            HealthStatus.DEGRADED,
            message="Invalid measurement type",
            value="invalid",
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "MONITORING_DATA_INVALID"
    assert finding.component == "cpu"


def test_unknown_check_gets_fallback_diagnosis():
    report = create_report(
        create_check(
            "custom.sensor",
            HealthStatus.DEGRADED,
            message="Unexpected sensor condition",
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.rule_id == "UNCLASSIFIED_HEALTH_ISSUE"
    assert finding.component == "custom.sensor"
    assert finding.recommendation


def test_critical_finding_takes_precedence():
    report = create_report(
        create_check("cpu", HealthStatus.DEGRADED, value=85.0),
        create_check("memory", HealthStatus.CRITICAL, value=98.0),
    )

    result = DiagnosticEngine().diagnose(report)

    assert len(result.warning_findings) == 1
    assert len(result.critical_findings) == 1
    assert result.severity is DiagnosticSeverity.CRITICAL
    assert result.healthy is False


def test_report_preserves_timestamp():
    report = create_report(
        create_check("cpu", HealthStatus.DEGRADED),
    )

    result = DiagnosticEngine().diagnose(report)

    assert result.timestamp == _TIMESTAMP


def test_thresholds_are_preserved():
    report = create_report(
        create_check(
            "cpu",
            HealthStatus.DEGRADED,
            value=85.0,
            warning=80.0,
            critical=95.0,
        )
    )

    result = DiagnosticEngine().diagnose(report)

    finding = result.findings[0]

    assert finding.warning_threshold == 80.0
    assert finding.critical_threshold == 95.0
