# Condensed Font and Decimal Places Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use DejaVu Sans Condensed throughout the UI and let every object independently control its displayed fractional digits.

**Architecture:** Extend `MonitorObjectConfig` with validated precision, then pass that precision to a pure value-formatting helper during rendering. Centralize the Tk font family in one constant and install the matching Debian font package in the runtime image.

**Tech Stack:** Python 3.11, configparser, dataclasses, Tkinter, pytest, Docker Buildx

---

### Task 1: Per-Object Decimal Configuration

**Files:**
- Modify: `tests/test_payloads.py`
- Modify: `src/roll_plugin_monitor/config.py`

- [ ] **Step 1: Write failing configuration tests**

Add tests proving independent values, the default, and validation:

```python
def test_load_config_reads_independent_decimal_places(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host=mqtt\nobject_count=2\n"
        "\n[object.1]\ndecimal_places=1\n"
        "\n[object.2]\ndecimal_places=4\n",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert [item.decimal_places for item in config.objects] == [1, 4]


def test_load_config_defaults_decimal_places_to_two(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host=mqtt\nobject_count=1\n\n[object.1]\n",
        encoding="utf-8",
    )
    assert load_config(config_file).objects[0].decimal_places == 2


@pytest.mark.parametrize("invalid_value", ["-1", "1.5", "many"])
def test_load_config_rejects_invalid_decimal_places(tmp_path, invalid_value):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[monitor]\nmqtt_host=mqtt\nobject_count=1\n"
        f"\n[object.1]\ndecimal_places={invalid_value}\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ValueError,
        match=re.escape("[object.1] decimal_places must be a non-negative integer"),
    ):
        load_config(config_file)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `$env:PYTHONPATH='src'; pytest tests/test_payloads.py -q`

Expected: missing `decimal_places` and missing validation failures.

- [ ] **Step 3: Implement minimal configuration support**

Add this parser beside `_positive_int`:

```python
def _non_negative_int(value: str | None, default: int, setting: str) -> int:
    raw = str(default) if value is None or not value.strip() else value.strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{setting} must be a non-negative integer, got {raw!r}") from exc
    if parsed < 0:
        raise ValueError(f"{setting} must be a non-negative integer, got {raw!r}")
    return parsed
```

Add `decimal_places: int = 2` to `MonitorObjectConfig`, then load it with:

```python
decimal_places=_non_negative_int(
    section.get("decimal_places"), 2, f"[{section_name}] decimal_places"
),
```

- [ ] **Step 4: Verify GREEN and commit**

Run: `$env:PYTHONPATH='src'; pytest tests/test_payloads.py -q`

Commit:

```powershell
git add tests/test_payloads.py src/roll_plugin_monitor/config.py
git commit -m "feat: configure object decimal precision"
```

### Task 2: Object-Aware Value Formatting

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`

- [ ] **Step 1: Write the failing formatter test**

```python
@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        (None, 2, "-"),
        (13000, 2, "13000"),
        (13000.123, 2, "13000.12"),
        (0.129, 2, "0.13"),
        (3.6, 3, "3.600"),
        (7.9, 0, "8"),
    ],
)
def test_format_value_preserves_integers_and_controls_fraction(value, places, expected):
    assert ui.format_value(value, places) == expected
```

- [ ] **Step 2: Run the test and verify RED**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q`

Expected: `format_value` is missing.

- [ ] **Step 3: Implement the formatter and render lookup**

```python
def format_value(value: float | int | None, decimal_places: int) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{decimal_places}f}"
```

In `RollMonitorApp.__init__`, create:

```python
self.objects_by_id = {item.object_id: item for item in config.objects}
```

In `_render`, replace the global two-place formatter call with:

```python
monitor_object = self.objects_by_id.get(object_id)
if variable is not None and monitor_object is not None:
    variable.set(format_value(value, monitor_object.decimal_places))
```

Remove the obsolete `_format` method.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```powershell
$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q
$env:PYTHONPATH='src'; pytest -q
```

Commit:

```powershell
git add tests/test_runtime_behavior.py src/roll_plugin_monitor/ui.py
git commit -m "feat: format values with object precision"
```

### Task 3: Condensed UI Font and Docker Dependency

**Files:**
- Modify: `tests/test_runtime_behavior.py`
- Modify: `src/roll_plugin_monitor/ui.py`
- Modify: `Dockerfile`

- [ ] **Step 1: Change font expectations and verify RED**

Expect `("DejaVu Sans Condensed", size, "bold")` from `title_font`, `object_label_font`, `object_value_font`, and `object_unit_font`.

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q`

Expected: assertions show the existing Arial family.

- [ ] **Step 2: Centralize and apply the font family**

Add:

```python
DEFAULT_FONT_FAMILY = "DejaVu Sans Condensed"
```

Use it in all four font helpers and the direct broker/last-seen warning font tuples.

- [ ] **Step 3: Add the runtime font package**

Update the Docker install line to include `fonts-dejavu-core`:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-tk tk libx11-6 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 4: Verify GREEN and commit**

Run: `$env:PYTHONPATH='src'; pytest tests/test_runtime_behavior.py -q`

Commit:

```powershell
git add tests/test_runtime_behavior.py src/roll_plugin_monitor/ui.py Dockerfile
git commit -m "feat: use condensed monitor font"
```

### Task 4: Examples, Documentation, and Final Verification

**Files:**
- Modify: `config.example.ini`
- Modify: `README.md`

- [ ] **Step 1: Update configuration examples**

Add `decimal_places = 2` to every sample `[object.N]` and the README sample.

- [ ] **Step 2: Document the behavior**

Document `DejaVu Sans Condensed` as the default family. Explain that `decimal_places` is per object, defaults to `2`, accepts zero or greater, preserves integer inputs, pads and rounds float fractional digits, and rejects invalid values.

- [ ] **Step 3: Run fresh final verification**

```powershell
$env:PYTHONPATH='src'; pytest -q
python -m compileall -q src
git diff --check
git status --short
```

Expected: all tests and compilation pass; diff check is clean; only intended documentation changes remain.

- [ ] **Step 4: Commit documentation and reverify**

```powershell
git add config.example.ini README.md
git commit -m "docs: describe object decimal precision"
$env:PYTHONPATH='src'; pytest -q
python -m compileall -q src
git diff --check
git status --short
```

Expected: all commands succeed and the worktree is clean.

### Task 5: Integration and ARM64 Release Decision

**Files:**
- Modify only when releasing: `README.md`, `docker-compose.example.yml`

- [ ] **Step 1: Use `superpowers:finishing-a-development-branch`**

Present merge, PR, keep, and discard options after verification. Do not publish without the user's choice.

- [ ] **Step 2: If requested, update image version `1.0.4` and push Git**

Commit the image tag in README and Compose, then push the selected branch.

- [ ] **Step 3: Build, push, and verify Raspberry Pi image**

```powershell
docker buildx build --platform linux/arm64 -t 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.4 --push .
docker pull --platform linux/arm64 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.4
docker image inspect 203.228.107.184:5000/btx/roll_plugin_monitor:1.0.4 --format 'Architecture={{.Architecture}} OS={{.Os}} RepoDigests={{json .RepoDigests}}'
```

Expected: `Architecture=arm64`, `OS=linux`, and a registry digest.
