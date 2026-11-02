
"""Tests for MELTYMON AI OS monitoring serialization."""

import json

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

import pytest

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
    timestamp = datetime(
        2026, 11, 2, 18, 30, tzinfo=timezone.utc
    )

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
    value = datetime(
        2026, 11, 2, 18, 30, tzinfo=timezone.utc
    )

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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_reject_non_finite_float_values(value):
    with pytest.raises(ValueError, match="Non-finite float"):
        to_primitive(value)


def test_snapshot_to_dict():
    timestamp = datetime.now(timezone.utc)

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
        timestamp=datetime(2026, 11, 2, tzinfo=timezone.utc),
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
        timestamp=datetime(2026, 11, 2, tzinfo=timezone.utc),
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
