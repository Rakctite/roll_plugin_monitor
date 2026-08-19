# Configurable Font Sizes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the monitor title and every object's label and measured-value font sizes configurable through `config.ini`.

**Architecture:** Extend the existing frozen configuration dataclasses and startup parser with positive-integer font settings while retaining the current hard-coded sizes as defaults. Expose small pure font-spec helpers in the UI module so configuration-to-Tkinter mapping can be tested without opening a display, then use those helpers when constructing labels.

**Tech Stack:** Python 3.11, `configparser`, frozen dataclasses, Tkinter, pytest

---

## File Structure

- Modify `src/roll_plugin_monitor/config.py`: define defaults and validate/load the three new configuration fields.
- Modify `src/roll_plugin_monitor/ui.py`: map configuration values to Tkinter font tuples and use them for widget construction.
- Modify `tests/test_payloads.py`: cover configuration loading, defaults, independent object values, and invalid values.
- Modify `tests/test_runtime_behavior.py`: cover the pure UI font mappings without requiring an X display.
- Modify `config.example.ini`: show the new settings in realistic sections.
- Modify `README.md`: document scope, defaults, per-object behavior, and restart semantics.

### Task 1: Load and Validate Font Configuration

**Files:**
- Modify: `tests/test_payloads.py`
- Modify: `src/roll_plugin_monitor/config.py`

- [ ] **Step 1: Write failing configuration tests**

Add tests that write an INI containing `title_font_size = 32`, two objects with different `label_font_size` and `value_font_size` values, and assert the resulting dataclasses retain `32`, `(18, 48)`, and `(24, 72)`. Add a default-value test asserting `28`, `20`, and `64` when the keys are absent. Add parameterized invalid-value tests for `0`, `-1`, and `large` and assert `ValueError` contains the exact setting name.

```python
assert config.title_font_size == 32
assert (config.objects[0].label_font_size, config.objects[0].value_font_size) == (18, 48)
assert (config.objects[1].label_font_size, config.objects[1].value_font_size) == (24, 72)

assert default_config.title_font_size == 28
assert default_config.objects[0].label_font_size == 20
assert default_config.objects[0].value_font_size == 64
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
pytest tests/test_payloads.py -q
```

Expected: FAIL because the font-size dataclass fields do not exist.

- [ ] **Step 3: Implement positive-integer parsing and dataclass fields**

Add a helper with an identifying setting name:

```python
def _positive_int(value: str | None, default: int, setting: str) -> int:
    raw = str(default) if value is None or not value.strip() else value.strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{setting} must be a positive integer, got {raw!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{setting} must be a positive integer, got {raw!r}")
    return parsed
```

Add `title_font_size: int = 28` to `MonitorConfig`, plus `label_font_size: int = 20` and `value_font_size: int = 64` after the existing required fields in `MonitorObjectConfig`. Load monitor size through `get("title_font_size", "28")`, which preserves `ROLL_MONITOR_TITLE_FONT_SIZE`, and object sizes directly from each object section using setting identifiers such as `[object.1] label_font_size`.

- [ ] **Step 4: Run focused and full tests and verify GREEN**

Run:

```bash
pytest tests/test_payloads.py -q
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit configuration support**

```bash
git add src/roll_plugin_monitor/config.py tests/test_payloads.py
git commit -m "feat: load configurable font sizes"
```

### Task 2: Apply Font Sizes to Tkinter Widgets

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Write failing pure UI mapping tests**

Import and test three helpers without constructing `tk.Tk()`:

```python
assert title_font(config) == ("Arial", 34, "bold")
assert object_label_font(monitor_object) == ("Arial", 22, "bold")
assert object_value_font(monitor_object) == ("Arial", 70, "bold")
```

Use a `MonitorConfig(title_font_size=34)` and a `MonitorObjectConfig(label_font_size=22, value_font_size=70)`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pytest tests/test_runtime_behavior.py -q
```

Expected: FAIL because the font helper functions do not exist.

- [ ] **Step 3: Add helpers and replace hard-coded sizes**

Add these pure helpers:

```python
def title_font(config: MonitorConfig) -> tuple[str, int, str]:
    return ("Arial", config.title_font_size, "bold")


def object_label_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return ("Arial", monitor_object.label_font_size, "bold")


def object_value_font(monitor_object: MonitorObjectConfig) -> tuple[str, int, str]:
    return ("Arial", monitor_object.value_font_size, "bold")
```

Use them in `_build_object_grid()` and `_object_style_1()` for the title, label, and measured value respectively. Do not change unit, broker-status, or last-seen fonts.

- [ ] **Step 4: Run focused and full tests and verify GREEN**

Run:

```bash
pytest tests/test_runtime_behavior.py -q
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit UI support**

```bash
git add src/roll_plugin_monitor/ui.py tests/test_runtime_behavior.py
git commit -m "feat: apply configured UI font sizes"
```

### Task 3: Document and Verify the Feature

**Files:**
- Modify: `config.example.ini`
- Modify: `README.md`

- [ ] **Step 1: Update the example configuration**

Add `title_font_size = 28` under `[monitor]` and add the following to every example object:

```ini
label_font_size = 20
value_font_size = 64
```

- [ ] **Step 2: Update README usage documentation**

Document that title size is monitor-wide, label/value sizes are independent per object, omitted keys retain `28`/`20`/`64`, values must be positive integers, and changes take effect after restarting the application container.

- [ ] **Step 3: Run final verification**

Run:

```bash
pytest -q
python -m compileall -q src
git diff --check
```

Expected: all tests PASS, compilation exits `0`, and `git diff --check` reports no whitespace errors.

- [ ] **Step 4: Commit documentation**

```bash
git add config.example.ini README.md
git commit -m "docs: describe configurable font sizes"
```
