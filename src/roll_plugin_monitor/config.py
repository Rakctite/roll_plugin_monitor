from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items or default


def _to_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class MonitorConfig:
    mqtt_host: str
    mqtt_port: int = 1883
    topics: tuple[str, ...] = ("C-S/+/+/+/+/+/+/+/data", "iot/IPR/#")
    left_tags: tuple[str, ...] = ("left", "left_thickness", "LEFT", "Roll_Left")
    right_tags: tuple[str, ...] = ("right", "right_thickness", "RIGHT", "Roll_Right")
    roll_temp_tags: tuple[str, ...] = ("temperature", "roll_temp", "temp", "TEMP", "Roll_Temp")
    min_thickness: float | None = None
    max_thickness: float | None = None
    stale_sec: float = 5.0
    fullscreen: bool = True
    display_interval_ms: int = 200
    client_id: str = "roll-plugin-monitor"
    username: str | None = None
    password: str | None = None


def load_config(path: str | Path | None = None) -> MonitorConfig:
    parser = configparser.ConfigParser()
    config_path = Path(path or os.getenv("ROLL_MONITOR_CONFIG", "config.ini"))
    if config_path.exists():
        parser.read(config_path, encoding="utf-8")

    section = parser["monitor"] if parser.has_section("monitor") else {}

    def get(name: str, default: str | None = None) -> str | None:
        env_name = f"ROLL_MONITOR_{name.upper()}"
        return os.getenv(env_name) or section.get(name.lower(), default)

    host = get("mqtt_host") or get("mqtt_broker") or "localhost"
    min_value = get("min_thickness")
    max_value = get("max_thickness")

    return MonitorConfig(
        mqtt_host=host,
        mqtt_port=int(get("mqtt_port", "1883") or 1883),
        topics=_split_csv(get("topics"), MonitorConfig.topics),
        left_tags=_split_csv(get("left_tags"), MonitorConfig.left_tags),
        right_tags=_split_csv(get("right_tags"), MonitorConfig.right_tags),
        roll_temp_tags=_split_csv(get("roll_temp_tags"), MonitorConfig.roll_temp_tags),
        min_thickness=float(min_value) if min_value not in {None, ""} else None,
        max_thickness=float(max_value) if max_value not in {None, ""} else None,
        stale_sec=float(get("stale_sec", "5") or 5),
        fullscreen=_to_bool(get("fullscreen"), True),
        display_interval_ms=int(get("display_interval_ms", "200") or 200),
        client_id=get("client_id", "roll-plugin-monitor") or "roll-plugin-monitor",
        username=get("username"),
        password=get("password"),
    )

