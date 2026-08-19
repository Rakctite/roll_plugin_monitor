# Configurable Font Sizes Design

## Goal

Allow operators to change the monitor title font size and each object's label and measured-value font sizes through `config.ini`, without rebuilding the image.

## Configuration Interface

The monitor title uses one setting in `[monitor]`:

```ini
[monitor]
title_font_size = 28
```

Each object controls its own label and measured-value sizes:

```ini
[object.1]
label_font_size = 20
value_font_size = 64
```

The settings are independent for every `[object.N]` section. The unit and stale-status text sizes remain unchanged because they are outside this request.

## Compatibility and Validation

- `title_font_size` defaults to `28` when omitted.
- `label_font_size` defaults to `20` when omitted.
- `value_font_size` defaults to `64` when omitted.
- These defaults preserve the existing display for current `config.ini` files.
- Values must be positive integers. Invalid values cause configuration loading to fail with an error that identifies the affected setting.
- Environment override support follows the existing monitor convention: `ROLL_MONITOR_TITLE_FONT_SIZE` can override `[monitor] title_font_size`. Per-object sizes are read only from their object sections, consistent with the existing object fields.

## Code Changes

- Add `title_font_size` to `MonitorConfig`.
- Add `label_font_size` and `value_font_size` to `MonitorObjectConfig`.
- Parse and validate the new settings in `config.py`.
- Replace the title, object-label, and measured-value hard-coded Tkinter sizes in `ui.py` with the parsed settings.
- Add the settings to `config.example.ini` and document them in `README.md`.

## Data Flow

`config.ini` is loaded into the frozen configuration dataclasses at startup. `RollMonitorApp` then uses `MonitorConfig.title_font_size` when constructing the title label and the matching `MonitorObjectConfig` sizes when constructing each object card. As with the current configuration, changes take effect after restarting or recreating the application container.

## Testing

- Verify explicit font sizes load into the correct monitor and object fields.
- Verify omitted settings retain defaults `28`, `20`, and `64`.
- Verify different objects retain different label and value sizes.
- Verify zero, negative, and non-integer values are rejected with a clear configuration error.
- Isolate Tkinter font tuple construction in a small testable helper or verify widget construction using the least coupled existing pattern, avoiding a real display requirement in unit tests.

## Out of Scope

- Runtime hot reload of `config.ini`.
- Font family, weight, or color configuration.
- Unit-label, broker-status, and last-seen font sizes.
