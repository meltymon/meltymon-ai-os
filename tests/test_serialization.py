"""Tests for MELTYMON AI OS monitoring serialization."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path

import pytest

from meltymon_ai_os.monitoring.gpu import GPUInfo, GPUSnapshot
from meltymon_ai_os.monitoring.serialization import (
    snapshot_to_dict,
    snapshot_to_json,
    to_primitive,
)
from meltymon_ai_os.monitoring.system import SystemSnapshot


class ExampleStatus(Enum):
    """Example enum for serialization tests."""

    ACTIVE = "active"


@dataclass(frozen=True)
class NestedData:
    """Example nested dataclass."""

    name: str
    value: int


@dataclass(frozen=True)
class ExampleData:
    """Example dataclass containing different data types."""

    name: str
    timestamp: datetime
    status: ExampleStatus
    path: Path
    values: tuple[int, ...]
    nested: NestedData


def test_serialize_dataclass():
    timestamp = datetime(2026, 11, 2, 18, 30, tzinfo=UTC)

    data = ExampleData(
        name="MELTYMON",
        timestamp=timestamp,
        status=ExampleStatus.ACTIVE,
        path=Path("/tmp/meltymon"),
        values=(1, 2, 3),
        nested=NestedData("CPU", 56),
    )

    result = to_primitive(data)

    assert result["name"] == "MELTYMON"
    assert result["timestamp"] == timestamp.isoformat()
    assert result["status"] == "active"
    assert result["path"] == "/tmp/meltymon"
    assert result["values"] == [1, 2, 3]
    assert result["nested"] == {
        "name": "CPU",
        "value": 56,
    }


def test_serialize_date():
    value = date(2026, 11, 2)

    assert to_primitive(value) == "2026-11-02"


def test_serialize_datetime():
    value = datetime(2026, 11, 2, 18, 30, tzinfo=UTC)

    assert to_primitive(value) == value.isoformat()


def test_serialize_mapping_and_nested_collections():
    value = {
        "nodes": (
            {"id": 0, "cpus": [0, 1, 2]},
            {"id": 1, "cpus": [3, 4, 5]},
        )
    }

    result = to_primitive(value)

    assert result == {
        "nodes": [
            {"id": 0, "cpus": [0, 1, 2]},
            {"id": 1, "cpus": [3, 4, 5]},
        ]
    }


def test_serialize_enum():
    assert to_primitive(ExampleStatus.ACTIVE) == "active"


def test_serialize_path():
    assert to_primitive(Path("/tmp/test")) == "/tmp/test"


def test_serialize_primitive_values():
    assert to_primitive(None) is None
    assert to_primitive(True) is True
    assert to_primitive(42) == 42
    assert to_primitive(3.14) == 3.14
    assert to_primitive("MELTYMON") == "MELTYMON"


def test_reject_non_string_mapping_keys():
    with pytest.raises(TypeError, match="keys must be strings"):
        to_primitive({1: "invalid"})


def test_reject_unsupported_types():
    with pytest.raises(TypeError, match="Unsupported serialization type"):
        to_primitive(object())


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_reject_non_finite_float_values(value):
    with pytest.raises(ValueError, match="Non-finite float"):
        to_primitive(value)


def test_snapshot_to_dict():
    timestamp = datetime.now(UTC)

    snapshot = SystemSnapshot(
        timestamp=timestamp,
        resources=None,
        numa=None,
        gpu=None,
        errors={"gpu": "GPU unavailable"},
    )

    result = snapshot_to_dict(snapshot)

    assert result["timestamp"] == timestamp.isoformat()
    assert result["resources"] is None
    assert result["numa"] is None
    assert result["gpu"] is None
    assert result["errors"] == {"gpu": "GPU unavailable"}


def test_snapshot_to_json():
    snapshot = SystemSnapshot(
        timestamp=datetime(2026, 11, 2, tzinfo=UTC),
        resources=None,
        numa=None,
        gpu=None,
        errors={},
    )

    result = snapshot_to_json(snapshot)

    parsed = json.loads(result)

    assert parsed["resources"] is None
    assert parsed["numa"] is None
    assert parsed["gpu"] is None
    assert parsed["errors"] == {}


def test_snapshot_to_json_without_indentation():
    snapshot = SystemSnapshot(
        timestamp=datetime(2026, 11, 2, tzinfo=UTC),
        resources=None,
        numa=None,
        gpu=None,
        errors={},
    )

    result = snapshot_to_json(snapshot, indent=None)

    assert "\n" not in result
    assert json.loads(result)["errors"] == {}


def test_snapshot_to_dict_rejects_non_dictionary_result():
    with pytest.raises(TypeError, match="must serialize to a dictionary"):
        snapshot_to_dict("not a snapshot")


def create_multi_gpu_snapshot():
    """Create a system snapshot containing two different GPUs."""

    timestamp = datetime(2026, 11, 2, 18, 30, tzinfo=UTC)

    intel_gpu = GPUSnapshot(
        timestamp=timestamp,
        gpu=GPUInfo(
            name="Intel Arc A750",
            vendor="Intel",
            driver="i915",
            device_id="8086:56a1",
            backend="intel",
        ),
        utilization_percent=75.5,
        memory_used_bytes=4_000_000_000,
        memory_total_bytes=8_000_000_000,
        temperature_celsius=68.0,
        power_watts=120.5,
        power_limit_watts=225.0,
        energy_joules=15000.0,
        current_frequency_mhz=2200,
        max_frequency_mhz=2400,
        boost_frequency_mhz=2400,
    )

    nvidia_gpu = GPUSnapshot(
        timestamp=timestamp,
        gpu=GPUInfo(
            name="NVIDIA GeForce RTX",
            vendor="NVIDIA",
            driver="nvidia",
            device_id="10de:2684",
            backend="nvidia",
        ),
        utilization_percent=42.0,
        memory_used_bytes=6_000_000_000,
        memory_total_bytes=12_000_000_000,
        temperature_celsius=55.0,
        power_watts=95.0,
        power_limit_watts=200.0,
        energy_joules=9000.0,
        current_frequency_mhz=1800,
        max_frequency_mhz=2500,
        boost_frequency_mhz=2500,
    )

    return SystemSnapshot(
        timestamp=timestamp,
        resources=None,
        numa=None,
        gpu=(intel_gpu, nvidia_gpu),
        errors={},
    )


def test_snapshot_to_dict_serializes_multiple_gpus():
    snapshot = create_multi_gpu_snapshot()

    result = snapshot_to_dict(snapshot)

    assert len(result["gpu"]) == 2

    intel, nvidia = result["gpu"]

    assert intel["gpu"]["name"] == "Intel Arc A750"
    assert intel["gpu"]["vendor"] == "Intel"
    assert intel["gpu"]["device_id"] == "8086:56a1"
    assert intel["gpu"]["backend"] == "intel"

    assert intel["utilization_percent"] == 75.5
    assert intel["memory_used_bytes"] == 4_000_000_000
    assert intel["memory_total_bytes"] == 8_000_000_000
    assert intel["temperature_celsius"] == 68.0
    assert intel["power_watts"] == 120.5
    assert intel["power_limit_watts"] == 225.0
    assert intel["energy_joules"] == 15000.0
    assert intel["current_frequency_mhz"] == 2200
    assert intel["max_frequency_mhz"] == 2400
    assert intel["boost_frequency_mhz"] == 2400

    assert nvidia["gpu"]["name"] == "NVIDIA GeForce RTX"
    assert nvidia["gpu"]["vendor"] == "NVIDIA"
    assert nvidia["gpu"]["device_id"] == "10de:2684"
    assert nvidia["gpu"]["backend"] == "nvidia"

    assert nvidia["utilization_percent"] == 42.0
    assert nvidia["memory_used_bytes"] == 6_000_000_000
    assert nvidia["memory_total_bytes"] == 12_000_000_000
    assert nvidia["temperature_celsius"] == 55.0
    assert nvidia["power_watts"] == 95.0
    assert nvidia["power_limit_watts"] == 200.0
    assert nvidia["energy_joules"] == 9000.0
    assert nvidia["current_frequency_mhz"] == 1800
    assert nvidia["max_frequency_mhz"] == 2500
    assert nvidia["boost_frequency_mhz"] == 2500


def test_snapshot_to_json_serializes_multiple_gpus():
    snapshot = create_multi_gpu_snapshot()

    result = snapshot_to_json(snapshot)
    parsed = json.loads(result)

    assert len(parsed["gpu"]) == 2

    assert parsed["gpu"][0]["gpu"]["device_id"] == "8086:56a1"
    assert parsed["gpu"][0]["gpu"]["name"] == "Intel Arc A750"

    assert parsed["gpu"][1]["gpu"]["device_id"] == "10de:2684"
    assert parsed["gpu"][1]["gpu"]["name"] == "NVIDIA GeForce RTX"

    assert parsed["gpu"][0]["timestamp"] == (snapshot.gpu[0].timestamp.isoformat())
    assert parsed["gpu"][1]["timestamp"] == (snapshot.gpu[1].timestamp.isoformat())


def test_snapshot_to_dict_preserves_empty_gpu_collection():
    snapshot = SystemSnapshot(
        timestamp=datetime(2026, 11, 2, tzinfo=UTC),
        resources=None,
        numa=None,
        gpu=(),
        errors={},
    )

    result = snapshot_to_dict(snapshot)

    assert result["gpu"] == []
    assert result["gpu"] is not None
