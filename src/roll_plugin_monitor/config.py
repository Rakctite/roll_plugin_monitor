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


def _positive_int(value: str | None, default: int, setting: str) -> int:
    raw = str(default) if value is None or not value.strip() else value.strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{setting} must be a positive integer, got {raw!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{setting} must be a positive integer, got {raw!r}")
    return parsed


@dataclass(frozen=True)
class MonitorObjectConfig:
    object_id: str
    label: str
    unit: str
    style: int
    topic: str
    sensor_name: str
    x: int
    y: int
    w: int
    h: int
    label_font_size: int = 20
    value_font_size: int = 64


@dataclass(frozen=True)
class MonitorConfig:
    mqtt_host: str
    title: str = "ROLL MONITOR"
    title_font_size: int = 28
    mqtt_port: int = 1883
    topics: tuple[str, ...] = ("C-S/+/+/+/+/+/+/+/data", "iot/IPR/#")
    grid_columns: int = 16
    grid_rows: int = 9
    objects: tuple[MonitorObjectConfig, ...] = ()
    stale_sec: float = 5.0
    fullscreen: bool = True
    display_interval_ms: int = 200
    client_id: str = "roll-plugin-monitor"
    username: str | None = None
    password: str | None = None
    log_file: str | None = "/app/logs/roll_plugin_monitor.log"


def _load_objects(parser: configparser.ConfigParser, count: int) -> tuple[MonitorObjectConfig, ...]:
    objects: list[MonitorObjectConfig] = []
    for index in range(1, count + 1):
        section_name = f"object.{index}"
        if not parser.has_section(section_name):
            continue
        section = parser[section_name]
        objects.append(
            MonitorObjectConfig(
                object_id=str(index),
                label=section.get("label", f"OBJECT {index}"),
                unit=section.get("unit", ""),
                style=int(section.get("style", "1") or 1),
                topic=section.get("topic", ""),
                sensor_name=section.get("sensor_name", ""),
                x=int(section.get("x", "1") or 1),
                y=int(section.get("y", "1") or 1),
                w=int(section.get("w", "1") or 1),
                h=int(section.get("h", "1") or 1),
                label_font_size=_positive_int(
                    section.get("label_font_size"),
                    20,
                    f"[{section_name}] label_font_size",
                ),
                value_font_size=_positive_int(
                    section.get("value_font_size"),
                    64,
                    f"[{section_name}] value_font_size",
                ),
            )
        )
    return tuple(objects)


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
    object_count = int(get("object_count", "0") or 0)
    return MonitorConfig(
        mqtt_host=host,
        title=get("title", "ROLL MONITOR") or "ROLL MONITOR",
        title_font_size=_positive_int(get("title_font_size"), 28, "[monitor] title_font_size"),
        mqtt_port=int(get("mqtt_port", "1883") or 1883),
        topics=_split_csv(get("topics"), MonitorConfig.topics),
        grid_columns=int(get("grid_columns", "16") or 16),
        grid_rows=int(get("grid_rows", "9") or 9),
        objects=_load_objects(parser, object_count),
        stale_sec=float(get("stale_sec", "5") or 5),
        fullscreen=_to_bool(get("fullscreen"), True),
        display_interval_ms=int(get("display_interval_ms", "200") or 200),
        client_id=get("client_id", "roll-plugin-monitor") or "roll-plugin-monitor",
        username=get("username"),
        password=get("password"),
        log_file=get("log_file", "/app/logs/roll_plugin_monitor.log"),
    )
