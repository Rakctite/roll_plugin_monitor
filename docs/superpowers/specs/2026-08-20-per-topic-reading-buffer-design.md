# Per-Topic Reading Buffer Design

## Goal

Prevent readings from different MQTT topics from overwriting each other before the Tkinter display poll processes them, while retaining only the newest reading for each individual topic.

## Confirmed Failure

The current `LatestReadingBuffer` stores one `RollReading`. On the deployed monitor, `C-S/Temp/CKP/data` arrives about one millisecond before `C-S/Gap/Gap/data`. The Gap reading replaces the Temp reading before the 200 ms UI poll, so the temperature updates only when the poll happens inside that narrow interval.

The MQTT subscriptions, topic names, payload keys, and object configuration are correct. The loss occurs between the MQTT callback and `MonitorState.update()`.

## Buffer Behavior

`LatestReadingBuffer` will store one reading per MQTT topic. Its internal collection is keyed by `RollReading.topic` and protected by the existing lock.

- A reading from a new topic is appended to the pending topic set.
- A newer reading from an already-pending topic replaces that topic's reading without changing the topic's original position in the batch.
- Readings from different topics never replace one another.
- Draining returns every pending reading in topic arrival order and atomically clears the buffer.
- Draining an empty buffer returns an empty tuple.

Python dictionaries preserve insertion order, so a locked `dict[str, RollReading]` provides the required behavior without an unbounded message queue.

## Display Poll

Each UI poll drains the buffer once and calls `MonitorState.update()` for every returned reading before stale-state calculation and rendering. `MonitorState` already merges object values and timestamps, so no state or payload changes are required.

For the observed sequence:

```text
Temp(topic A) -> Gap(topic B) -> UI poll
```

both readings reach `MonitorState`, and the rendered snapshot contains Temp, Gap1, and Gap2.

For repeated readings from one topic:

```text
Temp=36.9(topic A) -> Temp=37.0(topic A) -> UI poll
```

only `Temp=37.0` is processed.

## Concurrency

MQTT callbacks call `put()` from the Paho network thread while Tkinter calls the drain method from the UI thread. Both mutation and drain remain under one `threading.Lock`. The drain copies pending values and clears the dictionary while holding the lock, preventing lost or partially observed batches.

## Compatibility

No INI options, MQTT payload formats, topic matching, object layout, font behavior, warning behavior, or Docker runtime settings change. Existing single-topic behavior remains equivalent: only that topic's newest pending reading is processed.

## Testing

Automated regression tests will verify:

- different topics are retained and returned in arrival order;
- repeated readings for one topic retain only the newest reading;
- replacing one topic does not reorder it relative to other topics;
- drain clears the buffer and a second drain returns an empty tuple;
- applying a drained Temp and Gap batch to `MonitorState` retains all three configured object values;
- the complete existing test suite passes.
