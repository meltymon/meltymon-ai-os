
from pathlib import Path

import pytest

from meltymon_ai_os.monitoring.gpu_intel import (
    IntelGPUBackend,
)


def create_fake_gpu(root: Path) -> Path:
    """Create a simulated Intel GPU sysfs structure."""

    card = root / "card1"
    device = card / "device"

    device.mkdir(parents=True)

    (device / "vendor").write_text("0x8086")
    (device / "device").write_text("0x56a1")

    driver = root / "drivers" / "i915"
    driver.mkdir(parents=True)

    (device / "driver").symlink_to(driver)

    hwmon = device / "hwmon" / "hwmon0"
    hwmon.mkdir(parents=True)

    (hwmon / "name").write_text("i915")
    (hwmon / "temp1_input").write_text("50000")
    (hwmon / "energy1_input").write_text("2000000")
    (hwmon / "power1_max").write_text("180000000")
    (hwmon / "power1_average").write_text("42000000")

    drm = device / "drm" / "card1"
    drm.mkdir(parents=True)

    (drm / "gt_act_freq_mhz").write_text("600")
    (drm / "gt_max_freq_mhz").write_text("2400")
    (drm / "gt_boost_freq_mhz").write_text("2400")

    return root


@pytest.mark.asyncio
async def test_detect_intel_arc_a750(tmp_path):
    create_fake_gpu(tmp_path)

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert len(detected) == 1
    assert detected[0].name == "Intel Arc A750"
    assert detected[0].vendor == "Intel"
    assert detected[0].driver == "i915"
    assert detected[0].backend == "intel-i915"


@pytest.mark.asyncio
async def test_collect_intel_gpu_telemetry(tmp_path):
    create_fake_gpu(tmp_path)

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.temperature_celsius == 50.0
    assert snapshot.energy_joules == 2.0
    assert snapshot.power_watts == 42.0
    assert snapshot.power_limit_watts == 180.0
    assert snapshot.current_frequency_mhz == 600
    assert snapshot.max_frequency_mhz == 2400
    assert snapshot.boost_frequency_mhz == 2400


@pytest.mark.asyncio
async def test_ignore_non_intel_devices(tmp_path):
    card = tmp_path / "card0"
    device = card / "device"

    device.mkdir(parents=True)

    (device / "vendor").write_text("0x10de")
    (device / "device").write_text("0x1234")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert detected == []


@pytest.mark.asyncio
async def test_missing_optional_telemetry(tmp_path):
    create_fake_gpu(tmp_path)

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.utilization_percent is None
    assert snapshot.memory_used_bytes is None
    assert snapshot.memory_total_bytes is None
