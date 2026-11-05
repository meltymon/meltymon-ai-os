"""JSON serialization utilities for MELTYMON AI OS monitoring data."""

import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


def to_primitive(value: Any) -> Any:
    """Convert supported Python objects into JSON-compatible values.

    Supported types:
    - Dataclasses
    - Datetime and date objects
    - Enum values
    - Path objects
    - Dictionaries with string keys
    - Lists and tuples
    - JSON-compatible primitive values

    Unsupported types raise TypeError instead of being silently
    converted into potentially misleading data.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Non-finite float values are not valid JSON: {value}")
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Enum):
        return to_primitive(value.value)

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"JSON object keys must be strings; received {type(key).__name__}"
                )

            result[key] = to_primitive(item)

        return result

    if isinstance(value, (list, tuple)):
        return [to_primitive(item) for item in value]

    raise TypeError(f"Unsupported serialization type: {type(value).__name__}")


def snapshot_to_dict(snapshot: Any) -> dict[str, Any]:
    """Convert a system snapshot into a JSON-compatible dictionary.

    The function intentionally accepts the snapshot as an argument
    without importing SystemSnapshot. This avoids unnecessary
    coupling between serialization and monitoring orchestration.
    """
    result = to_primitive(snapshot)

    if not isinstance(result, dict):
        raise TypeError("A system snapshot must serialize to a dictionary")

    return result


def snapshot_to_json(
    snapshot: Any,
    *,
    indent: int | None = 2,
) -> str:
    """Serialize a system snapshot into a JSON string.

    Non-finite numbers are rejected to ensure standards-compliant JSON.
    """
    data = snapshot_to_dict(snapshot)

    return json.dumps(
        data,
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
    )
