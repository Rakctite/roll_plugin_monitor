# Per-Topic Reading Buffer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the newest pending MQTT reading for every topic so near-simultaneous Temp and Gap messages both reach monitor state.

**Architecture:** Replace the single reading slot with an insertion-ordered dictionary keyed by topic. Each Tk poll atomically drains the pending topic batch and applies every reading to the existing merging `MonitorState` before rendering.

**Tech Stack:** Python 3.11, threading, dataclasses, pytest, Tkinter

---

### Task 1: Per-Topic Buffer Regression and Implementation

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Replace the old single-reading test with a failing regression**

```python
def test_latest_reading_buffer_keeps_latest_reading_per_topic_in_arrival_order():
    buffer = LatestReadingBuffer()
    temp_first = RollReading(topic="temp", object_values={"3": 36.9})
    gap = RollReading(topic="gap", object_values={"1": 3.99, "2": 4.0})
    temp_latest = RollReading(topic="temp", object_values={"3": 37.0})

    buffer.put(temp_first)
    buffer.put(gap)
    buffer.put(temp_latest)

    assert buffer.take_pending() == (temp_latest, gap)
    assert buffer.take_pending() == ()
```

This proves different topics are retained, the same topic keeps only its newest reading, replacement does not reorder the topic, and drain clears the buffer.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py::test_latest_reading_buffer_keeps_latest_reading_per_topic_in_arrival_order -q`

Expected: FAIL because `take_pending()` does not exist.

- [ ] **Step 3: Implement the minimal buffer**

```python
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
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py::test_latest_reading_buffer_keeps_latest_reading_per_topic_in_arrival_order -q`

Expected: PASS.

- [ ] **Step 5: Commit the isolated buffer behavior**

```powershell
git add tests/test_runtime_behavior.py src/roll_plugin_monitor/ui.py
git commit -m "fix: retain latest reading per mqtt topic"
```

### Task 2: Drain Every Topic into Monitor State

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Write a Temp-and-Gap state regression test**

```python
from roll_plugin_monitor.state import MonitorState


def test_pending_topic_batch_merges_temp_and_gap_values_into_state():
    buffer = LatestReadingBuffer()
    buffer.put(RollReading(topic="temp", object_values={"3": 37.0}))
    buffer.put(RollReading(topic="gap", object_values={"1": 3.99, "2": 4.0}))
    state = MonitorState()

    ui.apply_pending_readings(buffer, state)

    assert state.snapshot().object_values == {"3": 37.0, "1": 3.99, "2": 4.0}
```

- [ ] **Step 2: Run the state regression and verify RED**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py::test_pending_topic_batch_merges_temp_and_gap_values_into_state -q`

Expected: FAIL because `apply_pending_readings()` does not exist.

- [ ] **Step 3: Add the batch helper and use it from `_poll()`**

```python
def apply_pending_readings(buffer: LatestReadingBuffer, state: MonitorState) -> None:
    for reading in buffer.take_pending():
        state.update(reading)


def _poll(self) -> None:
    apply_pending_readings(self.latest_reading, self.state)

    snapshot = self.state.mark_stale(self.config.stale_sec, datetime.now(timezone.utc))
    self._render(snapshot)
    self.root.after(self.config.display_interval_ms, self._poll)
```

- [ ] **Step 4: Verify focused and full behavior**

```powershell
$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q
$env:PYTHONPATH='src'; pytest -q
python -m compileall -q src
git diff --check
```

Then run `rg -n "take_latest" src tests` and expect no matches.

- [ ] **Step 5: Commit the poll integration**

```powershell
git add tests/test_runtime_behavior.py src/roll_plugin_monitor/ui.py
git commit -m "fix: apply every pending mqtt topic"
```

- [ ] **Step 6: Run fresh committed-tree verification**

```powershell
$env:PYTHONPATH='src'; pytest -q
python -m compileall -q src
git diff --check
git status --short
```

Expected: all commands succeed and the isolated worktree is clean.

### Task 3: Normalize Rounded Zero Display

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Extend the existing formatter test with zero-boundary cases**

Add these cases to `test_format_value_preserves_integers_and_controls_fraction`:

```python
(-0.04, 1, "0"),
(0.04, 1, "0"),
(0.0, 2, "0"),
(-0.004, 2, "0"),
(3.0, 1, "3.0"),
(-0.06, 1, "-0.1"),
```

- [ ] **Step 2: Run the formatter test and verify RED**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py::test_format_value_preserves_integers_and_controls_fraction -q`

Expected: zero cases fail with fixed-point strings such as `-0.0`, `0.0`, and `-0.00`.

- [ ] **Step 3: Normalize only formatted zero results**

Replace the floating-point return in `format_value()` with:

```python
formatted = f"{value:.{decimal_places}f}"
return "0" if float(formatted) == 0 else formatted
```

- [ ] **Step 4: Run focused and full tests and verify GREEN**

```powershell
$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py::test_format_value_preserves_integers_and_controls_fraction -q
$env:PYTHONPATH='src'; pytest -q
```

Expected: all formatter cases and the complete suite pass.

- [ ] **Step 5: Commit the formatting fix**

```powershell
git add tests/test_runtime_behavior.py src/roll_plugin_monitor/ui.py
git commit -m "fix: normalize rounded zero values"
```

### Task 4: Integration and ARM64 Release Decision

**Files:**
- Modify only when releasing: `README.md`, `docker-compose.example.yml`

- [ ] **Step 1: Use `superpowers:finishing-a-development-branch`**

Present merge, PR, keep, and discard options after fresh verification. Do not publish without the user's choice.

- [ ] **Step 2: If release is requested, prepare version `1.0.5`**

Update README and Compose to `203.228.107.184:5000/btx/roll_plugin_monitor:1.0.5`, commit the release metadata, and push the selected Git branch.

- [ ] **Step 3: Build, push, and verify the Raspberry Pi image**

```powershell
docker buildx build --platform linux/arm64 -t 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.5 --push .
docker pull --platform linux/arm64 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.5
docker image inspect 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.5 --format 'Architecture={{.Architecture}} OS={{.Os}} RepoDigests={{json .RepoDigests}}'
```

Expected: `Architecture=arm64`, `OS=linux`, and a registry digest.
