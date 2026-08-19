# Condensed Font and Decimal Places Design

## Goal

Use a narrower default UI font and let each monitor object independently control how many fractional digits are displayed without limiting the integer portion.

## Font Behavior

All Tkinter text currently rendered with Arial will use `DejaVu Sans Condensed` instead. The existing bold weight and configured font sizes remain unchanged. This applies to the monitor title, broker warning, object label, measured value, unit, and last-seen warning.

The Docker image must provide the font through the Debian font package used by the runtime image. Tkinter will continue receiving a normal font tuple, so no UI layout API changes are required.

## Per-Object Decimal Configuration

Each `[object.N]` section accepts:

```ini
decimal_places = 2
```

`decimal_places` is an integer greater than or equal to zero. It defaults to `2`, preserving the existing two-decimal display for floating-point readings. Invalid values, including negative integers and non-integers, stop startup with an error naming the object section and setting.

This setting is intentionally object-specific. There is no monitor-wide decimal override because different sensor types may require different precision.

## Formatting Rules

Formatting uses the matched object's `decimal_places` value:

- `None` remains `-`.
- Integer readings remain unchanged regardless of `decimal_places`; for example, `13000` displays as `13000`.
- Floating-point readings are rounded using Python's fixed-point formatting.
- The integer portion is never truncated or padded.
- Floating-point output contains exactly the configured number of fractional digits.

Examples:

| Input | `decimal_places` | Display |
| ---: | ---: | ---: |
| `13000` | `2` | `13000` |
| `13000.123` | `2` | `13000.12` |
| `0.129` | `2` | `0.13` |
| `3.6` | `3` | `3.600` |
| `7.9` | `0` | `8` |

The render path must look up the `MonitorObjectConfig` associated with each object ID before formatting its value. Formatting remains a pure helper so it can be tested without creating a Tk display.

## Configuration and Runtime Structure

`MonitorObjectConfig` gains `decimal_places: int = 2`. The object loader validates the INI value with a non-negative-integer parser. The app stores or derives an object-ID-to-config mapping and passes the configured precision into the value formatter during rendering.

No MQTT payload, state-management, positioning, unit-placement, warning-color, or title behavior changes are included.

## Documentation

`config.example.ini` will include `decimal_places = 2` for every sample object. The README will document the condensed default font, per-object precision, integer preservation, rounding behavior, default, and valid range.

## Testing

Automated tests will cover:

- the new font family for title, object label, value, and unit font specifications;
- the default and independently configured `decimal_places` values;
- rejection of negative and non-integer values;
- formatting of `None`, integers, large integer portions, rounded floats, padded fractional digits, and zero fractional digits;
- the full existing test suite and Python compilation.

The Docker release build must target `linux/arm64` for Raspberry Pi 5. Image versioning and registry publication remain a separate release step after implementation verification.
