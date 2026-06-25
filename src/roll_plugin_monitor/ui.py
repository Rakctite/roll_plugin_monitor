from __future__ import annotations

import queue
import tkinter as tk
from datetime import datetime, timezone

from .config import MonitorConfig
from .payloads import RollReading
from .state import MonitorSnapshot, MonitorState


class RollMonitorApp:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.state = MonitorState()
        self.queue: queue.Queue[RollReading] = queue.Queue()
        self.root = tk.Tk()
        self.root.title("Roll Plugin Monitor")
        if config.fullscreen:
            self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self._build()

    def enqueue(self, reading: RollReading) -> None:
        self.queue.put(reading)

    def run(self) -> None:
        self._poll()
        self.root.mainloop()

    def _build(self) -> None:
        self.root.configure(bg="#111111")
        self.status = tk.StringVar(value="WAITING")
        self.left = tk.StringVar(value="-")
        self.right = tk.StringVar(value="-")
        self.temp = tk.StringVar(value="-")
        self.topic = tk.StringVar(value="-")
        self.error = tk.StringVar(value="")

        top = tk.Frame(self.root, bg="#111111")
        top.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(top, text="ROLL MONITOR", fg="white", bg="#111111", font=("Arial", 28, "bold")).pack(side="left")
        tk.Label(top, textvariable=self.status, fg="#00d084", bg="#111111", font=("Arial", 18, "bold")).pack(side="right")

        body = tk.Frame(self.root, bg="#111111")
        body.pack(fill="both", expand=True, padx=24, pady=10)
        self._metric(body, "LEFT", self.left, 0)
        self._metric(body, "RIGHT", self.right, 1)
        self._metric(body, "ROLL TEMP", self.temp, 2)

        bottom = tk.Frame(self.root, bg="#111111")
        bottom.pack(fill="x", padx=24, pady=(8, 20))
        tk.Label(bottom, textvariable=self.topic, fg="#999999", bg="#111111", font=("Arial", 12)).pack(anchor="w")
        tk.Label(bottom, textvariable=self.error, fg="#ff6b6b", bg="#111111", font=("Arial", 14)).pack(anchor="w")

    def _metric(self, parent: tk.Frame, label: str, value: tk.StringVar, column: int) -> None:
        panel = tk.Frame(parent, bg="#1e1e1e", padx=24, pady=20)
        panel.grid(row=0, column=column, sticky="nsew", padx=8)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(panel, text=label, fg="#bbbbbb", bg="#1e1e1e", font=("Arial", 20, "bold")).pack(anchor="w")
        tk.Label(panel, textvariable=value, fg="white", bg="#1e1e1e", font=("Arial", 64, "bold")).pack(expand=True)

    def _poll(self) -> None:
        while True:
            try:
                self.state.update(self.queue.get_nowait())
            except queue.Empty:
                break

        snapshot = self.state.mark_stale(self.config.stale_sec, datetime.now(timezone.utc))
        self._render(snapshot)
        self.root.after(self.config.display_interval_ms, self._poll)

    def _render(self, snapshot: MonitorSnapshot) -> None:
        self.status.set("ONLINE" if snapshot.online else "OFFLINE")
        self.left.set(self._format(snapshot.left))
        self.right.set(self._format(snapshot.right))
        self.temp.set(self._format(snapshot.roll_temp))
        self.topic.set(snapshot.topic or "-")
        self.error.set(snapshot.error or "")

    def _format(self, value: float | int | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}" if isinstance(value, float) else str(value)

