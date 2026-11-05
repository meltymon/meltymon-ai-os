"""Intel GPU monitoring backend using Linux sysfs."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from meltymon_ai_os.monitoring.gpu import (
    BaseGPUBackend,
    GPUInfo,
    GPUSnapshot,
)


class IntelGPUBackend(BaseGPUBackend):
    """Collect Intel GPU telemetry without elevated privileges."""

    INTEL_VENDOR_ID = "0x8086"

    KNOWN_GPUS: ClassVar[dict[str, str]] = {
        "0x56a0": "Intel Arc A770",
        "0x56a1": "Intel Arc A750",
        "0x56a2": "Intel Arc A580",
        "0x56a5": "Intel Arc A380",
    }

    def __init__(
        self,
        drm_root: Path | None = None,
        pci_root: Path = Path("/sys/bus/pci/devices"),
        *,
        sysfs_root: Path | None = None,
    ) -> None:
        """Initialize the backend with configurable sysfs paths."""
        self.sysfs_root = Path(
            sysfs_root
            if sysfs_root is not None
            else drm_root
            if drm_root is not None
            else "/sys/class/drm"
        )
        self.pci_root = Path(pci_root)
        self._device_paths: dict[str, Path] = {}

    @staticmethod
    def _read_text(path: Path) -> str | None:
        """Read a sysfs value safely."""
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None

    @classmethod
    def _read_int(cls, path: Path) -> int | None:
        """Read an integer from sysfs."""
        value = cls._read_text(path)

        if value is None:
            return None

        try:
            return int(value, 0)
        except ValueError:
            try:
                return int(value)
            except ValueError:
                return None

    @staticmethod
    def _resolve_driver(device_path: Path) -> str | None:
        """Resolve the active kernel driver."""
        try:
            return (device_path / "driver").resolve(strict=True).name
        except (OSError, RuntimeError):
            return None

    async def detect(self) -> list[GPUInfo]:
        """Detect Intel GPUs through DRM sysfs."""
        devices: list[GPUInfo] = []
        self._device_paths.clear()

        if not self.sysfs_root.is_dir():
            return devices

        detected_addresses: set[str] = set()

        for card_path in sorted(self.sysfs_root.iterdir()):
            if not re.fullmatch(r"card\d+", card_path.name):
                continue

            try:
                device_path = (card_path / "device").resolve(strict=True)
            except (OSError, RuntimeError):
                continue

            vendor = self._read_text(device_path / "vendor")
            device_id = self._read_text(device_path / "device")

            if vendor != self.INTEL_VENDOR_ID or device_id is None:
                continue

            pci_address = device_path.name

            if pci_address in detected_addresses:
                continue

            detected_addresses.add(pci_address)

            driver = self._resolve_driver(device_path)
            normalized_id = device_id.lower()

            info = GPUInfo(
                name=self.KNOWN_GPUS.get(
                    normalized_id,
                    f"Intel GPU ({device_id})",
                ),
                vendor="Intel",
                driver=driver,
                device_id=pci_address,
                backend=("intel-i915" if driver == "i915" else "intel"),
            )

            self._device_paths[pci_address] = device_path
            devices.append(info)

        return devices

    def _read_hwmon(
        self,
        device_path: Path,
    ) -> dict[str, int | None]:
        """Read telemetry exclusively from the Intel i915 hwmon device."""
        result: dict[str, int | None] = {
            "temperature": None,
            "power": None,
            "power_limit": None,
            "energy": None,
        }

        hwmon_root = device_path / "hwmon"

        if not hwmon_root.is_dir():
            return result

        for hwmon_path in hwmon_root.glob("hwmon*"):
            if self._read_text(hwmon_path / "name") != "i915":
                continue

            result["temperature"] = self._read_int(hwmon_path / "temp1_input")
            result["power"] = self._read_int(hwmon_path / "power1_average")
            result["power_limit"] = self._read_int(hwmon_path / "power1_max")
            result["energy"] = self._read_int(hwmon_path / "energy1_input")
            break

        return result

    def _read_frequency(
        self,
        device_path: Path,
    ) -> dict[str, int | None]:
        """Read GT frequency information."""
        result: dict[str, int | None] = {
            "current": None,
            "maximum": None,
            "boost": None,
        }

        drm_path = device_path / "drm"

        if not drm_path.is_dir():
            return result

        for card_path in sorted(drm_path.iterdir()):
            if not re.fullmatch(r"card\d+", card_path.name):
                continue

            current = self._read_int(card_path / "gt_act_freq_mhz")

            if current is None:
                current = self._read_int(card_path / "gt_cur_freq_mhz")

            maximum = self._read_int(card_path / "gt_max_freq_mhz")

            boost = self._read_int(card_path / "gt_boost_freq_mhz")

            if any(value is not None for value in (current, maximum, boost)):
                result.update(
                    current=current,
                    maximum=maximum,
                    boost=boost,
                )
                break

        return result

    async def collect(self, gpu: GPUInfo) -> GPUSnapshot:
        """Collect a normalized telemetry snapshot."""
        pci_address = gpu.device_id or ""

        device_path = self._device_paths.get(
            pci_address,
            self.pci_root / pci_address,
        )

        hwmon = self._read_hwmon(device_path)
        frequency = self._read_frequency(device_path)

        return GPUSnapshot(
            timestamp=datetime.now(UTC),
            gpu=gpu,
            temperature_celsius=(
                hwmon["temperature"] / 1000
                if hwmon["temperature"] is not None
                else None
            ),
            power_watts=(
                hwmon["power"] / 1_000_000 if hwmon["power"] is not None else None
            ),
            power_limit_watts=(
                hwmon["power_limit"] / 1_000_000
                if hwmon["power_limit"] is not None
                else None
            ),
            energy_joules=(
                hwmon["energy"] / 1_000_000 if hwmon["energy"] is not None else None
            ),
            current_frequency_mhz=frequency["current"],
            max_frequency_mhz=frequency["maximum"],
            boost_frequency_mhz=frequency["boost"],
        )


__all__ = ["IntelGPUBackend"]
