import shutil
from pathlib import Path

import pytest

from meltymon_ai_os.monitoring.gpu_intel import IntelGPUBackend


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


@pytest.mark.asyncio
async def test_missing_sysfs_root_returns_no_devices(tmp_path):
    backend = IntelGPUBackend(drm_root=tmp_path / "missing")

    detected = await backend.detect()

    assert detected == []
    assert backend._device_paths == {}


@pytest.mark.asyncio
async def test_ignore_card_without_device_symlink(tmp_path):
    (tmp_path / "card0").mkdir()

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert detected == []


@pytest.mark.asyncio
async def test_ignore_broken_device_symlink(tmp_path):
    card = tmp_path / "card0"
    card.mkdir()

    (card / "device").symlink_to(tmp_path / "nonexistent")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert detected == []


@pytest.mark.asyncio
async def test_detect_unknown_intel_gpu(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    (device / "device").write_text("0xffff")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert len(detected) == 1
    assert detected[0].name == "Intel GPU (0xffff)"
    assert detected[0].vendor == "Intel"


@pytest.mark.asyncio
async def test_detect_intel_gpu_without_driver(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    (device / "driver").unlink()

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert len(detected) == 1
    assert detected[0].driver is None
    assert detected[0].backend == "intel"


@pytest.mark.asyncio
async def test_missing_hwmon_returns_empty_telemetry(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    shutil.rmtree(device / "hwmon")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.temperature_celsius is None
    assert snapshot.power_watts is None
    assert snapshot.power_limit_watts is None
    assert snapshot.energy_joules is None


@pytest.mark.asyncio
async def test_ignore_non_i915_hwmon(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    (device / "hwmon" / "hwmon0" / "name").write_text("other")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.temperature_celsius is None
    assert snapshot.power_watts is None


@pytest.mark.asyncio
async def test_invalid_hwmon_values_return_none(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    hwmon = device / "hwmon" / "hwmon0"

    (hwmon / "temp1_input").write_text("invalid")
    (hwmon / "power1_average").write_text("invalid")
    (hwmon / "power1_max").write_text("invalid")
    (hwmon / "energy1_input").write_text("invalid")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.temperature_celsius is None
    assert snapshot.power_watts is None
    assert snapshot.power_limit_watts is None
    assert snapshot.energy_joules is None


@pytest.mark.asyncio
async def test_frequency_fallback_to_current_frequency(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    drm = device / "drm" / "card1"

    (drm / "gt_act_freq_mhz").unlink()
    (drm / "gt_cur_freq_mhz").write_text("900")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.current_frequency_mhz == 900


@pytest.mark.asyncio
async def test_missing_frequency_information_returns_none(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    drm = device / "drm" / "card1"

    for filename in (
        "gt_act_freq_mhz",
        "gt_max_freq_mhz",
        "gt_boost_freq_mhz",
    ):
        (drm / filename).unlink()

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.current_frequency_mhz is None
    assert snapshot.max_frequency_mhz is None
    assert snapshot.boost_frequency_mhz is None


@pytest.mark.asyncio
async def test_duplicate_pci_device_is_detected_only_once(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    (tmp_path / "card2").mkdir()

    (tmp_path / "card2" / "device").symlink_to(device)

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert len(detected) == 1
    assert detected[0].name == "Intel Arc A750"


@pytest.mark.asyncio
async def test_ignore_card_without_vendor_information(tmp_path):
    card = tmp_path / "card0"
    device = card / "device"

    device.mkdir(parents=True)

    (device / "device").write_text("0x56a1")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()

    assert detected == []


@pytest.mark.asyncio
async def test_missing_drm_directory_returns_empty_frequency(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    shutil.rmtree(device / "drm")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.current_frequency_mhz is None
    assert snapshot.max_frequency_mhz is None
    assert snapshot.boost_frequency_mhz is None


@pytest.mark.asyncio
async def test_ignore_non_card_entries_in_drm_directory(tmp_path):
    create_fake_gpu(tmp_path)

    device = (tmp_path / "card1" / "device").resolve()
    drm = device / "drm"

    render_node = drm / "renderD128"
    render_node.mkdir()

    (render_node / "gt_act_freq_mhz").write_text("999")

    backend = IntelGPUBackend(drm_root=tmp_path)

    detected = await backend.detect()
    snapshot = await backend.collect(detected[0])

    assert snapshot.current_frequency_mhz == 600
    assert snapshot.max_frequency_mhz == 2400
    assert snapshot.boost_frequency_mhz == 2400
