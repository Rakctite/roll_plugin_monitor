# Display Controls and Unit Placement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable title visibility, three-state warning presentation, monitor-wide unit placement, and per-object unit font sizes.

**Architecture:** Extend startup configuration with strictly validated display controls while retaining defaults that reproduce the existing UI. Model layout, warning presentation, and unit text as pure helpers so behavior is testable without an X display, then have Tkinter widget construction consume those helpers.

**Tech Stack:** Python 3.11, `configparser`, frozen dataclasses, Tkinter, pytest

---

## File Structure

- Modify `src/roll_plugin_monitor/config.py`: define and validate the new monitor and object settings.
- Modify `src/roll_plugin_monitor/ui.py`: implement pure display-policy helpers and apply them during widget construction and rendering.
- Modify `tests/test_payloads.py`: cover configuration defaults, valid overrides, environment overrides, and invalid values.
- Modify `tests/test_runtime_behavior.py`: cover title layout, warning modes, warning strings, unit placement text, and unit font mapping without creating `tk.Tk()`.
- Modify `config.example.ini`: expose the new settings with backward-compatible defaults.
- Modify `README.md`: document the configuration matrix and restart requirement.

### Task 1: Parse and Validate Display Settings

**Files:**
- Modify: `tests/test_payloads.py`
- Modify: `src/roll_plugin_monitor/config.py`

- [ ] **Step 1: Write failing configuration tests**

Add tests that load this configuration and assert all values remain independent:

```ini
[monitor]
mqtt_host = mqtt
object_count = 2
title_use = 0
warning_color_use = 1
unit_location = value

[object.1]
unit_font_size = 16

[object.2]
unit_font_size = 22
```

The assertions are:

```python
assert config.title_use is False
assert config.warning_color_use == 1
assert config.unit_location == "value"
assert config.objects[0].unit_font_size == 16
assert config.objects[1].unit_font_size == 22
```

Add a default test asserting `True`, `2`, `"label"`, and `12`. Add an environment test for `ROLL_MONITOR_TITLE_USE=0`, `ROLL_MONITOR_WARNING_COLOR_USE=0`, and `ROLL_MONITOR_UNIT_LOCATION=value`. Add parameterized rejection tests for title values `2` and `yes`, warning values `-1` and `3`, unit location `side`, and object unit font values `0`, `-1`, and `large`. Error assertions must identify `[monitor] title_use`, `[monitor] warning_color_use`, `[monitor] unit_location`, or `[object.1] unit_font_size`.

- [ ] **Step 2: Run configuration tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; pytest tests/test_payloads.py -q
```

Expected: FAIL because the dataclass fields and strict parsers do not exist.

- [ ] **Step 3: Implement strict parsing and dataclass fields**

Add reusable choice parsing:

```python
def _choice(value: str | None, default: str, setting: str, allowed: tuple[str, ...]) -> str:
    parsed = default if value is None or not value.strip() else value.strip().lower()
    if parsed not in allowed:
        choices = ", ".join(allowed)
        raise ValueError(f"{setting} must be one of {choices}, got {parsed!r}")
    return parsed
```

Parse title visibility from `("0", "1")` and convert the selected string to `bool(int(value))`. Parse warning mode from `("0", "1", "2")` and convert it to `int`. Parse unit location from `("label", "value")`. Reuse `_positive_int` for the per-object unit font size.

Add these fields:

```python
class MonitorObjectConfig:
    unit_font_size: int = 12

class MonitorConfig:
    title_use: bool = True
    warning_color_use: int = 2
    unit_location: str = "label"
```

Load monitor fields through the existing `get()` function so environment overrides work, and load `unit_font_size` from every object section with the identifier `f"[{section_name}] unit_font_size"`.

- [ ] **Step 4: Run focused and full tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; pytest tests/test_payloads.py -q
$env:PYTHONPATH='src'; pytest -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit configuration support**

```powershell
git add src/roll_plugin_monitor/config.py tests/test_payloads.py
git commit -m "feat: load display control settings"
```

### Task 2: Apply Layout, Warning, and Unit Policies

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Write failing pure UI policy tests**

Define expected layout behavior without creating a Tk root:

```python
assert body_grid_options(MonitorConfig(mqtt_host="mqtt", title_use=True)) == {
    "row": 1,
    "pady": (0, 24),
}
assert body_grid_options(MonitorConfig(mqtt_host="mqtt", title_use=False)) == {
    "row": 0,
    "pady": (24, 24),
}
```

Test the warning matrix using a frozen `WarningPresentation` value:

```python
assert warning_presentation(0) == WarningPresentation(False, "#bbbbbb", "#bbbbbb", "white")
assert warning_presentation(1) == WarningPresentation(True, "#bbbbbb", "#bbbbbb", "white")
assert warning_presentation(2) == WarningPresentation(True, "#ff4d4d", "#ff6b6b", "#ff4d4d")
```

Test `broker_status_text(False, mode)` returns `""`, `"Broker Disconnected"`, and `"Broker Disconnected"` for modes 0, 1, and 2, while connected always returns `""`. Test `last_seen_text()` likewise hides mode 0 and returns a `Last Seen:` string for modes 1 and 2 only when stale.

Test unit helpers:

```python
assert unit_text("bar", "label") == " (bar)"
assert unit_text("bar", "value") == " bar"
assert unit_text("", "value") == ""
assert object_unit_font(monitor_object) == ("Arial", 18, "bold")
```

- [ ] **Step 2: Run UI behavior tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q
```

Expected: FAIL because the policy helpers do not exist.

- [ ] **Step 3: Implement pure UI policies**

Add:

```python
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
```

Add the remaining pure helpers. `last_seen_text` keeps the existing local-time format `%Y-%m-%d %H:%M:%S`.

```python
def body_grid_options(config: MonitorConfig) -> dict[str, int | tuple[int, int]]:
    return {"row": 1, "pady": (0, 24)} if config.title_use else {"row": 0, "pady": (24, 24)}


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


def object_unit_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return ("Arial", monitor_object.unit_font_size, "bold")
```

- [ ] **Step 4: Apply title and warning policies to widgets**

In `_build_object_grid`, configure root row 0 with weight 0 and row 1 with weight 1 when `title_use` is true. Construct the title frame only in that branch. When false, configure row 0 with weight 1 and do not construct title or broker labels. Use `body_grid_options` for body row and vertical padding.

Initialize and update `broker_status` through `broker_status_text`. Use `warning_presentation` for broker label color, Last Seen label color, and stale measured-value color. Use `last_seen_text` in `_render`; mode 0 therefore clears Last Seen at its source.

- [ ] **Step 5: Apply unit placement to object widgets**

Keep the header unit label only when `unit_location == "label"` and `unit_text()` is non-empty. Replace the standalone measured-value packing with a centered `value_row` frame containing the measured-value label. When `unit_location == "value"`, add the separate unit label after the value with `object_unit_font`; its text comes from `unit_text()` and therefore has no parentheses. Preserve `self.object_value_labels` so stale rendering still updates the numeric label color.

- [ ] **Step 6: Run focused and full tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q
$env:PYTHONPATH='src'; pytest -q
```

Expected: all tests PASS.

- [ ] **Step 7: Commit UI behavior**

```powershell
git add src/roll_plugin_monitor/ui.py tests/test_runtime_behavior.py
git commit -m "feat: control title warnings and unit placement"
```

### Task 3: Document and Verify the Combined Feature

**Files:**
- Modify: `config.example.ini`
- Modify: `README.md`

- [ ] **Step 1: Update the example configuration**

Add backward-compatible monitor defaults:

```ini
title_use = 1
warning_color_use = 2
unit_location = label
```

Add `unit_font_size = 12` beside `unit` in every example object.

- [ ] **Step 2: Document behavior and examples**

Add a README table for warning modes 0, 1, and 2. Document title removal and full-height object layout. Show both `unit_location = label` producing `LABEL (sec)` and `unit_location = value` producing `12.3 sec`, state that `unit_font_size` is per object, and state that container restart/recreation is required.

- [ ] **Step 3: Run final verification**

Run:

```powershell
$env:PYTHONPATH='src'; pytest -q
python -m compileall -q src
git diff --check
```

Expected: all tests PASS, compilation exits 0, and no whitespace errors are reported.

- [ ] **Step 4: Commit documentation**

```powershell
git add config.example.ini README.md
git commit -m "docs: describe display and unit controls"
```
