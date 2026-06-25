from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .payloads import RollReading


@dataclass(frozen=True)
class MonitorSnapshot:
    left: float | None = None
    right: float | None = None
    roll_temp: float | None = None
    din1: int | None = None
    din2: int | None = None
    online: bool = False
    topic: str = ""
    error: str | None = None
    last_update: datetime | None = None


class MonitorState:
    def __init__(self) -> None:
        self._snapshot = MonitorSnapshot()

    def update(self, reading: RollReading) -> MonitorSnapshot:
        current = self._snapshot
        self._snapshot = MonitorSnapshot(
            left=reading.left if reading.left is not None else current.left,
            right=reading.right if reading.right is not None else current.right,
            roll_temp=reading.roll_temp if reading.roll_temp is not None else current.roll_temp,
            din1=reading.din1 if reading.din1 is not None else current.din1,
            din2=reading.din2 if reading.din2 is not None else current.din2,
            online=reading.online,
            topic=reading.topic or current.topic,
            error=reading.error,
            last_update=reading.timestamp,
        )
        return self._snapshot

    def mark_stale(self, stale_sec: float, now: datetime | None = None) -> MonitorSnapshot:
        now = now or datetime.now(timezone.utc)
        last_update = self._snapshot.last_update
        if last_update is None:
            return self._snapshot
        age = (now - last_update).total_seconds()
        if age <= stale_sec or not self._snapshot.online:
            return self._snapshot
        self._snapshot = MonitorSnapshot(
            left=self._snapshot.left,
            right=self._snapshot.right,
            roll_temp=self._snapshot.roll_temp,
            din1=self._snapshot.din1,
            din2=self._snapshot.din2,
            online=False,
            topic=self._snapshot.topic,
            error=f"stale: no mqtt message for {age:.1f}s",
            last_update=self._snapshot.last_update,
        )
        return self._snapshot

    def snapshot(self) -> MonitorSnapshot:
        return self._snapshot

