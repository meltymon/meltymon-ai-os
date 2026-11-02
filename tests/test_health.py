"""Tests for MELTYMON AI OS health evaluation."""

from datetime import datetime, timezone

import pytest

from meltymon_ai_os.monitoring.gpu import GPUInfo, GPUSnapshot
from meltymon_ai_os.monitoring.health import (
    HealthEvaluator,
    HealthStatus,
    HealthThresholds,
)
from meltymon_ai_os.monitoring.numa import (
    NUMAMemoryStats,
    NUMANode,
    NUMASnapshot,
)
from meltymon_ai_os.monitoring.resources import ResourceSnapshot
from meltymon_ai_os.monitoring.system import SystemSnapshot


_DEFAULT_GPU = object()


def create_gpu_snapshot(
    *,
    name: str = "Intel Arc A750",
    device_id: str = "8086:56a1",
    temperature: float | None = 50.0,
    memory_used: int | None = 40,
    memory_total: int | None = 100,
) -> GPUSnapshot:
    """Create a representative GPU snapshot."""

    return GPUSnapshot(
        timestamp=datetime(2026, 11, 2, tzinfo=timezone.utc),
        gpu=GPUInfo(
            name=name,
            vendor="Intel",
            driver="i915",
            device_id=device_id,
            backend="intel",
        ),
        temperature_celsius=temperature,
        memory_used_bytes=memory_used,
        memory_total_bytes=memory_total,
    )


def create_snapshot(
    *,
    cpu_percent: float = 20.0,
    memory_percent: float = 40.0,
    gpu_temperature: float | None = 50.0,
    gpu_memory_used: int | None = 40,
    gpu_memory_total: int | None = 100,
    numa_memory_used: int = 40,
    numa_memory_total: int = 100,
    gpu=_DEFAULT_GPU,
    numa_nodes=None,
    errors=None,
) -> SystemSnapshot:
    """Create a representative system snapshot."""

    timestamp = datetime(
        2026,
        11,
        2,
        tzinfo=timezone.utc,
    )

    resources = ResourceSnapshot(
        timestamp=timestamp,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        memory_total_bytes=100,
        memory_available_bytes=100 - int(memory_percent),
        memory_used_bytes=int(memory_percent),
        cpu_count=56,
    )

    if numa_nodes is None:
        numa_memory = NUMAMemoryStats(
            total_bytes=numa_memory_total,
            free_bytes=numa_memory_total - numa_memory_used,
            used_bytes=numa_memory_used,
            statistics={},
        )

        numa_nodes = (
            NUMANode(
                node_id=0,
                cpus=(0, 1, 2, 3),
                memory=numa_memory,
                distances=(10,),
            ),
        )

    numa_snapshot = NUMASnapshot(
        timestamp=timestamp,
        nodes=tuple(numa_nodes),
    )

    if gpu is _DEFAULT_GPU:
        gpu = (
            create_gpu_snapshot(
                temperature=gpu_temperature,
                memory_used=gpu_memory_used,
                memory_total=gpu_memory_total,
            ),
        )

    return SystemSnapshot(
        timestamp=timestamp,
        resources=resources,
        numa=numa_snapshot,
        gpu=gpu,
        errors=errors or {},
    )


def get_check(report, name):
    """Return one health check by its exact name."""
    return next(
        check for check in report.checks if check.name == name
    )


def test_healthy_system():
    snapshot = create_snapshot()

    report = HealthEvaluator().evaluate(snapshot)

    assert report.status is HealthStatus.HEALTHY
    assert report.healthy is True
    assert report.degraded_checks == ()
    assert report.critical_checks == ()


def test_cpu_warning_threshold():
    snapshot = create_snapshot(cpu_percent=85.0)

    report = HealthEvaluator().evaluate(snapshot)
    cpu_check = get_check(report, "cpu")

    assert cpu_check.status is HealthStatus.DEGRADED
    assert cpu_check.value == 85.0
    assert report.status is HealthStatus.DEGRADED


def test_cpu_critical_threshold():
    snapshot = create_snapshot(cpu_percent=96.0)

    report = HealthEvaluator().evaluate(snapshot)
    cpu_check = get_check(report, "cpu")

    assert cpu_check.status is HealthStatus.CRITICAL
    assert report.status is HealthStatus.CRITICAL


def test_memory_warning_threshold():
    snapshot = create_snapshot(memory_percent=90.0)

    report = HealthEvaluator().evaluate(snapshot)
    memory_check = get_check(report, "memory")

    assert memory_check.status is HealthStatus.DEGRADED


def test_memory_critical_threshold():
    snapshot = create_snapshot(memory_percent=97.0)

    report = HealthEvaluator().evaluate(snapshot)
    memory_check = get_check(report, "memory")

    assert memory_check.status is HealthStatus.CRITICAL


def test_gpu_temperature_warning_threshold():
    snapshot = create_snapshot(gpu_temperature=85.0)

    report = HealthEvaluator().evaluate(snapshot)
    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert temperature_check.status is HealthStatus.DEGRADED


def test_gpu_temperature_critical_threshold():
    snapshot = create_snapshot(gpu_temperature=95.0)

    report = HealthEvaluator().evaluate(snapshot)
    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert temperature_check.status is HealthStatus.CRITICAL


def test_gpu_memory_warning_threshold():
    snapshot = create_snapshot(
        gpu_memory_used=92,
        gpu_memory_total=100,
    )

    report = HealthEvaluator().evaluate(snapshot)
    memory_check = get_check(
        report,
        "gpu.8086:56a1.memory",
    )

    assert memory_check.status is HealthStatus.DEGRADED


def test_gpu_memory_critical_threshold():
    snapshot = create_snapshot(
        gpu_memory_used=98,
        gpu_memory_total=100,
    )

    report = HealthEvaluator().evaluate(snapshot)
    memory_check = get_check(
        report,
        "gpu.8086:56a1.memory",
    )

    assert memory_check.status is HealthStatus.CRITICAL


def test_missing_gpu_temperature_is_degraded():
    snapshot = create_snapshot(gpu_temperature=None)

    report = HealthEvaluator().evaluate(snapshot)
    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert temperature_check.status is HealthStatus.DEGRADED
    assert "unavailable" in temperature_check.message.lower()
    assert report.status is HealthStatus.DEGRADED


def test_missing_gpu_memory_is_degraded():
    snapshot = create_snapshot(
        gpu_memory_used=None,
        gpu_memory_total=None,
    )

    report = HealthEvaluator().evaluate(snapshot)
    memory_check = get_check(
        report,
        "gpu.8086:56a1.memory",
    )

    assert memory_check.status is HealthStatus.DEGRADED


def test_monitoring_error_is_degraded():
    snapshot = create_snapshot(
        gpu=None,
        errors={"gpu": "GPU unavailable"},
    )

    report = HealthEvaluator().evaluate(snapshot)
    gpu_check = get_check(report, "gpu")

    assert gpu_check.status is HealthStatus.DEGRADED
    assert "GPU unavailable" in gpu_check.message
    assert report.status is HealthStatus.DEGRADED


def test_missing_resources_are_degraded():
    snapshot = create_snapshot()

    snapshot = SystemSnapshot(
        timestamp=snapshot.timestamp,
        resources=None,
        numa=snapshot.numa,
        gpu=snapshot.gpu,
        errors={},
    )

    report = HealthEvaluator().evaluate(snapshot)

    assert any(
        check.name == "resources"
        and check.status is HealthStatus.DEGRADED
        for check in report.checks
    )

    assert report.status is HealthStatus.DEGRADED


def test_numa_node_memory_is_evaluated():
    snapshot = create_snapshot(numa_memory_used=96)

    report = HealthEvaluator().evaluate(snapshot)
    numa_check = get_check(
        report,
        "numa.node_0.memory",
    )

    assert numa_check.status is HealthStatus.CRITICAL
    assert report.status is HealthStatus.CRITICAL


def test_no_numa_nodes_is_degraded():
    snapshot = create_snapshot(numa_nodes=())

    report = HealthEvaluator().evaluate(snapshot)
    numa_check = get_check(report, "numa")

    assert numa_check.status is HealthStatus.DEGRADED


def test_critical_status_takes_precedence():
    snapshot = create_snapshot(
        cpu_percent=96.0,
        memory_percent=90.0,
    )

    report = HealthEvaluator().evaluate(snapshot)

    assert report.status is HealthStatus.CRITICAL
    assert len(report.critical_checks) >= 1
    assert len(report.degraded_checks) >= 1


def test_report_uses_snapshot_timestamp():
    snapshot = create_snapshot()

    report = HealthEvaluator().evaluate(snapshot)

    assert report.timestamp == snapshot.timestamp


def test_custom_thresholds():
    thresholds = HealthThresholds(
        cpu_warning=60.0,
        cpu_critical=80.0,
    )

    snapshot = create_snapshot(cpu_percent=70.0)

    report = HealthEvaluator(thresholds).evaluate(snapshot)
    cpu_check = get_check(report, "cpu")

    assert cpu_check.status is HealthStatus.DEGRADED
    assert cpu_check.warning_threshold == 60.0
    assert cpu_check.critical_threshold == 80.0


def test_reject_invalid_threshold_order():
    with pytest.raises(ValueError, match="must be lower"):
        HealthThresholds(
            cpu_warning=95.0,
            cpu_critical=80.0,
        )


def test_reject_percentage_threshold_above_100():
    with pytest.raises(ValueError, match="between 0 and 100"):
        HealthThresholds(
            memory_warning=90.0,
            memory_critical=110.0,
        )


def test_reject_non_finite_threshold():
    with pytest.raises(ValueError, match="must be finite"):
        HealthThresholds(
            cpu_warning=float("nan"),
        )


def test_zero_numa_memory_capacity_is_degraded():
    snapshot = create_snapshot(
        numa_memory_used=0,
        numa_memory_total=0,
    )

    report = HealthEvaluator().evaluate(snapshot)
    numa_check = get_check(
        report,
        "numa.node_0.memory",
    )

    assert numa_check.status is HealthStatus.DEGRADED
    assert report.status is HealthStatus.DEGRADED


def test_no_detected_gpu_is_not_an_error():
    snapshot = create_snapshot(gpu=())

    report = HealthEvaluator().evaluate(snapshot)

    assert report.status is HealthStatus.HEALTHY
    assert not any(
        check.name.startswith("gpu.")
        for check in report.checks
    )


def test_multiple_gpus_are_evaluated_independently():
    first_gpu = create_gpu_snapshot(
        name="Intel Arc A750",
        device_id="0000:01:00.0",
        temperature=50.0,
        memory_used=40,
        memory_total=100,
    )

    second_gpu = create_gpu_snapshot(
        name="Intel Arc A770",
        device_id="0000:02:00.0",
        temperature=95.0,
        memory_used=98,
        memory_total=100,
    )

    snapshot = create_snapshot(
        gpu=(first_gpu, second_gpu),
    )

    report = HealthEvaluator().evaluate(snapshot)

    first_temperature = get_check(
        report,
        "gpu.0000:01:00.0.temperature",
    )
    second_temperature = get_check(
        report,
        "gpu.0000:02:00.0.temperature",
    )
    first_memory = get_check(
        report,
        "gpu.0000:01:00.0.memory",
    )
    second_memory = get_check(
        report,
        "gpu.0000:02:00.0.memory",
    )

    assert first_temperature.status is HealthStatus.HEALTHY
    assert first_memory.status is HealthStatus.HEALTHY

    assert second_temperature.status is HealthStatus.CRITICAL
    assert second_memory.status is HealthStatus.CRITICAL

    assert report.status is HealthStatus.CRITICAL


def test_missing_measurement_on_one_gpu_does_not_hide_another():
    first_gpu = create_gpu_snapshot(
        name="Intel Arc A750",
        device_id="0000:01:00.0",
        temperature=None,
        memory_used=40,
        memory_total=100,
    )

    second_gpu = create_gpu_snapshot(
        name="Intel Arc A770",
        device_id="0000:02:00.0",
        temperature=50.0,
        memory_used=40,
        memory_total=100,
    )

    snapshot = create_snapshot(
        gpu=(first_gpu, second_gpu),
    )

    report = HealthEvaluator().evaluate(snapshot)

    assert get_check(
        report,
        "gpu.0000:01:00.0.temperature",
    ).status is HealthStatus.DEGRADED

    assert get_check(
        report,
        "gpu.0000:01:00.0.memory",
    ).status is HealthStatus.HEALTHY

    assert get_check(
        report,
        "gpu.0000:02:00.0.temperature",
    ).status is HealthStatus.HEALTHY

    assert get_check(
        report,
        "gpu.0000:02:00.0.memory",
    ).status is HealthStatus.HEALTHY


def test_gpu_temperature_thresholds_can_exceed_100_degrees():
    thresholds = HealthThresholds(
        gpu_temperature_warning=110.0,
        gpu_temperature_critical=120.0,
    )

    snapshot = create_snapshot(gpu_temperature=115.0)

    report = HealthEvaluator(thresholds).evaluate(snapshot)

    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert temperature_check.status is HealthStatus.DEGRADED
    assert temperature_check.value == 115.0


def test_gpu_temperature_above_100_is_valid_measurement():
    snapshot = create_snapshot(gpu_temperature=105.0)

    report = HealthEvaluator().evaluate(snapshot)

    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert temperature_check.status is HealthStatus.CRITICAL
    assert temperature_check.value == 105.0


def test_reject_negative_gpu_temperature_threshold():
    with pytest.raises(ValueError, match="at least 0"):
        HealthThresholds(
            gpu_temperature_warning=-1.0,
            gpu_temperature_critical=90.0,
        )


def test_gpu_check_message_contains_device_identity():
    snapshot = create_snapshot(gpu_temperature=85.0)

    report = HealthEvaluator().evaluate(snapshot)

    temperature_check = get_check(
        report,
        "gpu.8086:56a1.temperature",
    )

    assert "Intel Arc A750" in temperature_check.message
    assert "8086:56a1" in temperature_check.message
