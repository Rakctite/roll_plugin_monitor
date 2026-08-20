# Rounded Zero Normalization Design

## Goal

Display every floating-point value that rounds to zero as `0`, eliminating output such as `-0.0`, `0.0`, `-0.00`, and `0.00` while preserving existing fixed-decimal formatting for nonzero values.

## Formatting Rule

`format_value()` continues to format floating-point readings with the object's configured `decimal_places`. After formatting, the result is tested for numeric equality with zero.

- If the rounded formatted result equals zero, return `"0"`.
- If it is nonzero, return the existing fixed-point string unchanged.
- Integer readings remain unchanged.
- `None` remains `"-"`.

Examples:

| Input | Decimal places | Display |
| ---: | ---: | ---: |
| `-0.04` | `1` | `0` |
| `0.04` | `1` | `0` |
| `0.0` | `2` | `0` |
| `-0.004` | `2` | `0` |
| `3.0` | `1` | `3.0` |
| `-0.06` | `1` | `-0.1` |

Checking the formatted result, rather than comparing the original input against a manually calculated threshold, ensures the zero decision uses exactly the same rounding behavior as the displayed value.

## Scope

This change affects display text only. MQTT payload extraction, stored numeric values, stale detection, topic buffering, units, and configuration validation remain unchanged.

## Testing

The existing parameterized `format_value` test will gain positive zero, negative zero, and values that cross the configured rounding boundary. It will also retain a nonzero integral float case to prove that fixed fractional digits are not removed generally.
