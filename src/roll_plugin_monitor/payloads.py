from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import MonitorConfig


@dataclass(frozen=True)
class RollReading:
    topic: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sensor_values: dict[str, float] = field(default_factory=dict)
    sensor_timestamps: dict[str, datetime] = field(default_factory=dict)
    object_values: dict[str, float] = field(default_factory=dict)
    object_timestamps: dict[str, datetime] = field(default_factory=dict)
    online: bool = True
    error: str | None = None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _normalize_payload(payload: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    if isinstance(payload, str):
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError("mqtt payload must be a JSON object")
        return parsed
    return payload


def _extract_tag_payload(payload: dict[str, Any], timestamp: datetime) -> tuple[dict[str, float], dict[str, datetime], str | None]:
    sensor_values: dict[str, float] = {}
    sensor_timestamps: dict[str, datetime] = {}
    errors: list[str] = []

    for tag in payload.get("tags", []):
        if not isinstance(tag, dict):
            continue
        name = str(tag.get("name") or tag.get("tag") or "").strip()
        quality = str(tag.get("quality", "good")).strip().lower()
        if quality and quality not in {"good", "ok", "true", "1"}:
            reason = tag.get("error") or quality
            errors.append(f"{name}: {reason}")
            continue
        value = _to_float(tag.get("value"))
        if value is not None:
            sensor_values[name] = value
            sensor_timestamps[name] = timestamp

    return sensor_values, sensor_timestamps, "; ".join(errors) if errors else None


def topic_matches_name(config_topic: str, actual_topic: str) -> bool:
    return not config_topic or config_topic == actual_topic


def _extract_flat_sensor_values(payload: dict[str, Any], timestamp: datetime) -> tuple[dict[str, float], dict[str, datetime]]:
    metadata_keys = {"timestamp", "time", "update_time", "error", "error_msg"}
    values: dict[str, float] = {}
    timestamps: dict[str, datetime] = {}
    for key, raw_value in payload.items():
        if key in metadata_keys or key == "tags":
            continue
        value = _to_float(raw_value)
        if value is not None:
            values[key] = value
            timestamps[key] = timestamp
    return values, timestamps


def _extract_object_values_from_sensors(
    topic: str, sensor_values: dict[str, float], sensor_timestamps: dict[str, datetime], config: MonitorConfig
) -> tuple[dict[str, float], dict[str, datetime]]:
    sensor_lookup = {name.strip().lower(): value for name, value in sensor_values.items()}
    timestamp_lookup = {name.strip().lower(): value for name, value in sensor_timestamps.items()}
    object_values: dict[str, float] = {}
    object_timestamps: dict[str, datetime] = {}
    for monitor_object in config.objects:
        if not topic_matches_name(config_topic=monitor_object.topic, actual_topic=topic):
            continue
        sensor_name = monitor_object.sensor_name.strip().lower()
        if sensor_name in sensor_lookup:
            object_values[monitor_object.object_id] = sensor_lookup[sensor_name]
            object_timestamps[monitor_object.object_id] = timestamp_lookup[sensor_name]
    return object_values, object_timestamps


def extract_reading(topic: str, payload: bytes | str | dict[str, Any], config: MonitorConfig) -> RollReading:
    data = _normalize_payload(payload)
    timestamp = _parse_timestamp(data.get("timestamp") or data.get("time") or data.get("update_time"))

    if isinstance(data.get("tags"), list):
        sensor_values, sensor_timestamps, error = _extract_tag_payload(data, timestamp)
    else:
        sensor_values, sensor_timestamps = _extract_flat_sensor_values(data, timestamp)
        error = data.get("error") or data.get("error_msg")
    object_values, object_timestamps = _extract_object_values_from_sensors(topic, sensor_values, sensor_timestamps, config)
    return RollReading(
        topic=topic,
        timestamp=timestamp,
        sensor_values=sensor_values,
        sensor_timestamps=sensor_timestamps,
        object_values=object_values,
        object_timestamps=object_timestamps,
        online=True,
        error=str(error) if error else None,
    )
