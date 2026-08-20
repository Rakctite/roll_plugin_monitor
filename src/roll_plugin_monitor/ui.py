from __future__ import annotations

import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import MonitorConfig, MonitorObjectConfig
from .payloads import RollReading
from .state import MonitorSnapshot, MonitorState


DEFAULT_FONT_FAMILY = "DejaVu Sans Condensed"


class LatestReadingBuffer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._readings_by_topic: dict[str, RollReading] = {}

    def put(self, reading: RollReading) -> None:
        with self._lock:
            self._readings_by_topic[reading.topic] = reading

    def take_pending(self) -> tuple[RollReading, ...]:
        with self._lock:
            readings = tuple(self._readings_by_topic.values())
            self._readings_by_topic.clear()
            return readings


def object_place_geometry(monitor_object: MonitorObjectConfig, config: MonitorConfig) -> dict[str, float]:
    columns = max(config.grid_columns, 1)
    rows = max(config.grid_rows, 1)
    x = min(max(monitor_object.x, 1), columns)
    y = min(max(monitor_object.y, 1), rows)
    w = min(max(monitor_object.w, 1), columns - x + 1)
    h = min(max(monitor_object.h, 1), rows - y + 1)
    return {
        "relx": (x - 1) / columns,
        "rely": (y - 1) / rows,
        "relwidth": w / columns,
        "relheight": h / rows,
    }


def title_font(config: MonitorConfig) -> tuple[str, int, str]:
    return (DEFAULT_FONT_FAMILY, config.title_font_size, "bold")


def object_label_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return (DEFAULT_FONT_FAMILY, monitor_object.label_font_size, "bold")


def object_value_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return (DEFAULT_FONT_FAMILY, monitor_object.value_font_size, "bold")


def object_unit_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return (DEFAULT_FONT_FAMILY, monitor_object.unit_font_size, "bold")


def body_grid_options(config: MonitorConfig) -> dict[str, int | tuple[int, int]]:
    return {"row": 1, "pady": (0, 24)} if config.title_use else {"row": 0, "pady": (24, 24)}


@dataclass(frozen=True)
class WarningPresentation:
    show_messages: bool
    broker_color: str
    last_seen_color: str
    stale_value_color: str


def warning_presentation(mode: int) -> WarningPresentation:
    if mode == 0:
        return WarningPresentation(False, "#bbbbbb", "#bbbbbb", "white")
    if mode == 1:
        return WarningPresentation(True, "#bbbbbb", "#bbbbbb", "white")
    return WarningPresentation(True, "#ff4d4d", "#ff6b6b", "#ff4d4d")


def broker_status_text(connected: bool, warning_mode: int) -> str:
    return "" if connected or warning_mode == 0 else "Broker Disconnected"


def last_seen_text(is_stale: bool, last_seen: datetime | None, warning_mode: int) -> str:
    if not is_stale or last_seen is None or warning_mode == 0:
        return ""
    return f"Last Seen: {last_seen.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"


def unit_text(unit: str, location: str) -> str:
    if not unit:
        return ""
    return f" ({unit})" if location == "label" else f" {unit}"


def format_value(value: float | int | None, decimal_places: int) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    formatted = f"{value:.{decimal_places}f}"
    return "0" if float(formatted) == 0 else formatted


def apply_pending_readings(buffer: LatestReadingBuffer, state: MonitorState) -> None:
    for reading in buffer.take_pending():
        state.update(reading)


class RollMonitorApp:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.state = MonitorState()
        self.latest_reading = LatestReadingBuffer()
        self.root = tk.Tk()
        self.root.title("Roll Plugin Monitor")
        if config.fullscreen:
            self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.object_values: dict[str, tk.StringVar] = {}
        self.object_last_seen: dict[str, tk.StringVar] = {}
        self.object_value_labels: dict[str, tk.Label] = {}
        self.objects_by_id = {item.object_id: item for item in config.objects}
        self.warning = warning_presentation(config.warning_color_use)
        self.broker_status = tk.StringVar(value=broker_status_text(False, config.warning_color_use))
        self._build()

    def enqueue(self, reading: RollReading) -> None:
        self.latest_reading.put(reading)

    def set_broker_connected(self, connected: bool) -> None:
        status = broker_status_text(connected, self.config.warning_color_use)
        self.root.after(0, lambda: self.broker_status.set(status))

    def run(self) -> None:
        self._poll()
        self.root.mainloop()

    def _build(self) -> None:
        self._build_object_grid()

    def _build_object_grid(self) -> None:
        self.root.configure(bg="#111111")
        self.root.grid_columnconfigure(0, weight=1)

        if self.config.title_use:
            self.root.grid_rowconfigure(0, weight=0)
            self.root.grid_rowconfigure(1, weight=1)
            title = tk.Frame(self.root, bg="#111111")
            title.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
            tk.Label(title, text=self.config.title, fg="white", bg="#111111", font=title_font(self.config)).pack(
                side="left"
            )
            tk.Label(
                title,
                textvariable=self.broker_status,
                fg=self.warning.broker_color,
                bg="#111111",
                font=(DEFAULT_FONT_FAMILY, 16, "bold"),
            ).pack(side="right")
        else:
            self.root.grid_rowconfigure(0, weight=1)

        body = tk.Frame(self.root, bg="#111111")
        layout = body_grid_options(self.config)
        body.grid(row=layout["row"], column=0, sticky="nsew", padx=24, pady=layout["pady"])

        for monitor_object in self.config.objects:
            self._build_object_style(body, monitor_object)

    def _build_object_style(self, parent: tk.Frame, monitor_object: MonitorObjectConfig) -> None:
        if monitor_object.style == 1:
            self._object_style_1(parent, monitor_object)
            return
        self._object_style_1(parent, monitor_object)

    def _object_style_1(self, parent: tk.Frame, monitor_object: MonitorObjectConfig) -> None:
        value = tk.StringVar(value="-")
        last_seen = tk.StringVar(value="")
        self.object_values[monitor_object.object_id] = value
        self.object_last_seen[monitor_object.object_id] = last_seen

        panel = tk.Frame(parent, bg="#1e1e1e", padx=24, pady=20)
        geometry = object_place_geometry(monitor_object, self.config)
        panel.place(
            relx=geometry["relx"],
            rely=geometry["rely"],
            relwidth=geometry["relwidth"],
            relheight=geometry["relheight"],
            x=8,
            y=8,
            width=-16,
            height=-16,
        )

        header = tk.Frame(panel, bg="#1e1e1e")
        header.pack(anchor="w", fill="x")
        tk.Label(header, text=monitor_object.label, fg="#bbbbbb", bg="#1e1e1e", font=object_label_font(monitor_object)).pack(
            side="left"
        )
        rendered_unit = unit_text(monitor_object.unit, self.config.unit_location)
        if rendered_unit and self.config.unit_location == "label":
            tk.Label(
                header,
                text=rendered_unit,
                fg="#999999",
                bg="#1e1e1e",
                font=object_unit_font(monitor_object),
            ).pack(side="left", padx=(4, 0), pady=(6, 0))

        value_row = tk.Frame(panel, bg="#1e1e1e")
        value_row.pack(expand=True)
        value_label = tk.Label(
            value_row,
            textvariable=value,
            fg="white",
            bg="#1e1e1e",
            font=object_value_font(monitor_object),
        )
        value_label.pack(side="left")
        if rendered_unit and self.config.unit_location == "value":
            tk.Label(
                value_row,
                text=rendered_unit,
                fg="#999999",
                bg="#1e1e1e",
                font=object_unit_font(monitor_object),
            ).pack(side="left")
        self.object_value_labels[monitor_object.object_id] = value_label
        tk.Label(
            panel,
            textvariable=last_seen,
            fg=self.warning.last_seen_color,
            bg="#1e1e1e",
            font=(DEFAULT_FONT_FAMILY, 12, "bold"),
        ).pack(anchor="w")

    def _poll(self) -> None:
        apply_pending_readings(self.latest_reading, self.state)

        snapshot = self.state.mark_stale(self.config.stale_sec, datetime.now(timezone.utc))
        self._render(snapshot)
        self.root.after(self.config.display_interval_ms, self._poll)

    def _render(self, snapshot: MonitorSnapshot) -> None:
        for object_id, value in (snapshot.object_values or {}).items():
            variable = self.object_values.get(object_id)
            monitor_object = self.objects_by_id.get(object_id)
            if variable is not None and monitor_object is not None:
                variable.set(format_value(value, monitor_object.decimal_places))
        for object_id, variable in self.object_last_seen.items():
            value_label = self.object_value_labels.get(object_id)
            last_seen = snapshot.object_last_seen.get(object_id)
            is_stale = object_id in snapshot.stale_object_ids
            if value_label is not None:
                value_label.configure(fg=self.warning.stale_value_color if is_stale else "white")
            variable.set(last_seen_text(is_stale, last_seen, self.config.warning_color_use))

