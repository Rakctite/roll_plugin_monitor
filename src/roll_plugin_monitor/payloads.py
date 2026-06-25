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
    object_values: dict[str, float] = field(default_factory=dict)
    left: float | None = None
    right: float | None = None
    roll_temp: float | None = None
    din1: int | None = None
    din2: int | None = None
    online: bool = True
    error: str | None = None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
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


def _names(values: tuple[str, ...]) -> set[str]:
    return {value.strip().lower() for value in values}


def _extract_tag_payload(
    topic: str, payload: dict[str, Any], config: MonitorConfig
) -> tuple[float | None, float | None, float | None, dict[str, float], str | None]:
    left_names = _names(config.left_tags)
    right_names = _names(config.right_tags)
    temp_names = _names(config.roll_temp_tags)
    left = right = temp = None
    object_values: dict[str, float] = {}
    errors: list[str] = []

    for tag in payload.get("tags", []):
        if not isinstance(tag, dict):
            continue
        name = str(tag.get("name") or tag.get("tag") or "").strip()
        name_key = name.lower()
        quality = str(tag.get("quality", "good")).strip().lower()
        if quality and quality not in {"good", "ok", "true", "1"}:
            reason = tag.get("error") or quality
            errors.append(f"{name}: {reason}")
            continue
        value = _to_float(tag.get("value"))
        if name_key in left_names:
            left = value
        elif name_key in right_names:
            right = value
        elif name_key in temp_names:
            temp = value
        if value is not None:
            for monitor_object in config.objects:
                if topic_matches_name(config_topic=monitor_object.topic, actual_topic=topic):
                    if monitor_object.sensor_name.strip().lower() == name_key:
                        object_values[monitor_object.object_id] = value

    return left, right, temp, object_values, "; ".join(errors) if errors else None


def topic_matches_name(config_topic: str, actual_topic: str) -> bool:
    return bool(config_topic) and config_topic == actual_topic


def extract_reading(topic: str, payload: bytes | str | dict[str, Any], config: MonitorConfig) -> RollReading:
    data = _normalize_payload(payload)
    timestamp = _parse_timestamp(data.get("timestamp") or data.get("time") or data.get("update_time"))

    if isinstance(data.get("tags"), list):
        left, right, temp, object_values, error = _extract_tag_payload(topic, data, config)
    else:
        left = _to_float(data.get("left") or data.get("left_thickness"))
        right = _to_float(data.get("right") or data.get("right_thickness"))
        temp = _to_float(data.get("temperature") or data.get("roll_temp") or data.get("temp"))
        object_values = {}
        error = data.get("error") or data.get("error_msg")
    return RollReading(
        topic=topic,
        timestamp=timestamp,
        object_values=object_values,
        left=left,
        right=right,
        roll_temp=temp,
        din1=_to_int(data.get("din1")),
        din2=_to_int(data.get("din2")),
        online=True,
        error=str(error) if error else None,
    )
