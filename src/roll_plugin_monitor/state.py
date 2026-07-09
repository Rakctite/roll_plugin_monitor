from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .payloads import RollReading


@dataclass(frozen=True)
class MonitorSnapshot:
    sensor_values: dict[str, float] = field(default_factory=dict)
    sensor_timestamps: dict[str, datetime] = field(default_factory=dict)
    object_values: dict[str, float] = field(default_factory=dict)
    object_last_seen: dict[str, datetime] = field(default_factory=dict)
    stale_object_ids: set[str] = field(default_factory=set)
    online: bool = False
    topic: str = ""
    error: str | None = None
    last_update: datetime | None = None


class MonitorState:
    def __init__(self) -> None:
        self._snapshot = MonitorSnapshot()

    def update(self, reading: RollReading) -> MonitorSnapshot:
        current = self._snapshot
        sensor_values = dict(current.sensor_values)
        sensor_values.update(reading.sensor_values)
        sensor_timestamps = dict(current.sensor_timestamps)
        sensor_timestamps.update(reading.sensor_timestamps)
        object_values = dict(current.object_values)
        object_values.update(reading.object_values)
        object_last_seen = dict(current.object_last_seen)
        object_last_seen.update(reading.object_timestamps)
        self._snapshot = MonitorSnapshot(
            sensor_values=sensor_values,
            sensor_timestamps=sensor_timestamps,
            object_values=object_values,
            object_last_seen=object_last_seen,
            stale_object_ids=current.stale_object_ids,
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
        stale_object_ids = {
            object_id
            for object_id, last_seen in self._snapshot.object_last_seen.items()
            if (now - last_seen).total_seconds() > stale_sec
        }
        if age <= stale_sec or not self._snapshot.online:
            self._snapshot = MonitorSnapshot(
                sensor_values=self._snapshot.sensor_values,
                sensor_timestamps=self._snapshot.sensor_timestamps,
                object_values=self._snapshot.object_values,
                object_last_seen=self._snapshot.object_last_seen,
                stale_object_ids=stale_object_ids,
                online=self._snapshot.online,
                topic=self._snapshot.topic,
                error=self._snapshot.error,
                last_update=self._snapshot.last_update,
            )
            return self._snapshot
        self._snapshot = MonitorSnapshot(
            sensor_values=self._snapshot.sensor_values,
            sensor_timestamps=self._snapshot.sensor_timestamps,
            object_values=self._snapshot.object_values,
            object_last_seen=self._snapshot.object_last_seen,
            stale_object_ids=stale_object_ids,
            online=False,
            topic=self._snapshot.topic,
            error=f"stale: no mqtt message for {age:.1f}s",
            last_update=self._snapshot.last_update,
        )
        return self._snapshot

    def snapshot(self) -> MonitorSnapshot:
        return self._snapshot
