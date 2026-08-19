from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime, timezone

from .config import MonitorConfig, MonitorObjectConfig
from .payloads import RollReading
from .state import MonitorSnapshot, MonitorState


class LatestReadingBuffer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reading: RollReading | None = None

    def put(self, reading: RollReading) -> None:
        with self._lock:
            self._reading = reading

    def take_latest(self) -> RollReading | None:
        with self._lock:
            reading = self._reading
            self._reading = None
            return reading


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
    return ("Arial", config.title_font_size, "bold")


def object_label_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return ("Arial", monitor_object.label_font_size, "bold")


def object_value_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return ("Arial", monitor_object.value_font_size, "bold")


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
        self.broker_status = tk.StringVar(value="Broker Disconnected")
        self._build()

    def enqueue(self, reading: RollReading) -> None:
        self.latest_reading.put(reading)

    def set_broker_connected(self, connected: bool) -> None:
        status = "" if connected else "Broker Disconnected"
        self.root.after(0, lambda: self.broker_status.set(status))

    def run(self) -> None:
        self._poll()
        self.root.mainloop()

    def _build(self) -> None:
        self._build_object_grid()

    def _build_object_grid(self) -> None:
        self.root.configure(bg="#111111")
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        title = tk.Frame(self.root, bg="#111111")
        title.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        tk.Label(title, text=self.config.title, fg="white", bg="#111111", font=title_font(self.config)).pack(side="left")
        tk.Label(
            title,
            textvariable=self.broker_status,
            fg="#ff4d4d",
            bg="#111111",
            font=("Arial", 16, "bold"),
        ).pack(side="right")

        body = tk.Frame(self.root, bg="#111111")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))

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
        if monitor_object.unit:
            tk.Label(
                header,
                text=f" ({monitor_object.unit})",
                fg="#999999",
                bg="#1e1e1e",
                font=("Arial", 12, "bold"),
            ).pack(side="left", padx=(4, 0), pady=(6, 0))
        value_label = tk.Label(panel, textvariable=value, fg="white", bg="#1e1e1e", font=object_value_font(monitor_object))
        value_label.pack(expand=True)
        self.object_value_labels[monitor_object.object_id] = value_label
        tk.Label(panel, textvariable=last_seen, fg="#ff6b6b", bg="#1e1e1e", font=("Arial", 12, "bold")).pack(
            anchor="w"
        )

    def _poll(self) -> None:
        reading = self.latest_reading.take_latest()
        if reading is not None:
            self.state.update(reading)

        snapshot = self.state.mark_stale(self.config.stale_sec, datetime.now(timezone.utc))
        self._render(snapshot)
        self.root.after(self.config.display_interval_ms, self._poll)

    def _render(self, snapshot: MonitorSnapshot) -> None:
        for object_id, value in (snapshot.object_values or {}).items():
            variable = self.object_values.get(object_id)
            if variable is not None:
                variable.set(self._format(value))
        for object_id, variable in self.object_last_seen.items():
            value_label = self.object_value_labels.get(object_id)
            last_seen = snapshot.object_last_seen.get(object_id)
            is_stale = object_id in snapshot.stale_object_ids
            if value_label is not None:
                value_label.configure(fg="#ff4d4d" if is_stale else "white")
            if is_stale and last_seen is not None:
                variable.set(f"Last Seen: {last_seen.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                variable.set("")

    def _format(self, value: float | int | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}" if isinstance(value, float) else str(value)
