# Title and Warning Display Controls Design

## Goal

Allow operators to remove the title row so monitor objects use the full screen height, and independently control whether connection/stale warnings are hidden, shown neutrally, or shown in red.

## Configuration Interface

Add two settings to `[monitor]`:

```ini
[monitor]
title_use = 1
warning_color_use = 2
```

`title_use` accepts:

- `0`: do not construct the title row or broker-status widget; place the object body across the full root height.
- `1`: retain the current title row and broker-status widget.

`warning_color_use` accepts:

- `0`: hide `Broker Disconnected` and `Last Seen`; never change a stale measured value to red.
- `1`: show `Broker Disconnected` and `Last Seen` using neutral colors; never change a stale measured value to red.
- `2`: retain the current warning behavior: show warning text in red and change stale measured values to red.

## Layout Behavior

When `title_use = 1`, the existing layout remains unchanged: root row 0 contains the title and broker status, and root row 1 contains the object body.

When `title_use = 0`, no title frame or labels are created. The object body occupies root row 0 with weight 1, so each object's relative `x`, `y`, `w`, and `h` placement is calculated against the full available screen height. The existing 24-pixel outer margin is retained.

The title flag only controls the top row. Object-level `Last Seen` behavior continues to follow `warning_color_use` even when the title row is disabled.

## Warning Presentation

Warning presentation is selected at render time from one validated mode:

| Mode | Broker text | Last Seen text | Stale value color |
| --- | --- | --- | --- |
| `0` | hidden | hidden | white |
| `1` | neutral gray | neutral gray | white |
| `2` | red | red | red |

The connected broker state continues to use an empty status string in every mode. Mode `0` suppresses warning strings at their source rather than merely painting them the background color.

## Compatibility and Validation

- Omitted `title_use` defaults to `1`.
- Omitted `warning_color_use` defaults to `2`.
- These defaults preserve the existing UI exactly.
- `title_use` must be `0` or `1`.
- `warning_color_use` must be `0`, `1`, or `2`.
- Invalid values fail during startup with an error identifying the affected `[monitor]` setting.
- `ROLL_MONITOR_TITLE_USE` and `ROLL_MONITOR_WARNING_COLOR_USE` override their INI counterparts through the existing environment-variable convention.

## Code Changes

- Add `title_use: bool = True` and `warning_color_use: int = 2` to `MonitorConfig`.
- Add strict parsers for the binary title flag and three-state warning mode in `config.py`.
- Extract small pure UI helpers that describe body placement and warning presentation without requiring `tk.Tk()`.
- Build the title frame conditionally and place the body according to the title flag.
- Apply the warning presentation consistently in broker status updates and stale-object rendering.
- Update `config.example.ini` and `README.md`.

## Testing

- Verify defaults preserve `title_use = True` and `warning_color_use = 2`.
- Verify INI and environment overrides load valid values.
- Verify invalid values are rejected with setting-specific errors.
- Verify title-on and title-off body layout specifications.
- Verify the complete warning presentation matrix for modes 0, 1, and 2.
- Verify broker status strings and stale Last Seen strings respect the selected mode without opening a real display.
- Run the full pytest suite and Python byte-compilation check.

## Out of Scope

- Runtime hot reload; changing either setting requires restarting or recreating the application container.
- Separate modes for broker and stale-data warnings.
- Configurable warning colors.
- Removing the existing outer screen margin.
