# Roll Plugin Monitor

Raspberry Pi Docker app that subscribes to MQTT messages and displays configured sensor values with Tkinter.

## Docker Layout

Runtime files live beside the compose file under `./roll_plugin_monitor/`.

```text
roll_plugin_monitor/
  config.ini
  logs/
```

`config.ini` is mounted read-only into `/app/config/config.ini`.
Logs are written to `/app/logs/roll_plugin_monitor.log`.

## Raspberry Pi Docker Run

Prepare runtime config:

```bash
mkdir -p roll_plugin_monitor/logs
cp config.example.ini roll_plugin_monitor/config.ini
```

Run with compose:

```bash
docker compose -f docker-compose.example.yml up -d
```

The compose file passes `DISPLAY` and mounts `/tmp/.X11-unix`, so the Raspberry Pi desktop session must be running.

The published image is:

```text
203.228.107.184:5000/btx/roll_plugin_monitor:1.0.1
```

## Object Layout

The UI can be configured from `config.ini` with monitor objects. The screen is split into a coordinate grid, normally `16 x 9`. Coordinates are 1-based, so `x = 1` and `y = 1` is the top-left grid cell. Each object's `w` and `h` control only that object's width and height.

Each object updates only when both the MQTT topic and the configured `sensor_name` match a payload field or tag name:

```ini
[monitor]
title = ROLL MONITOR
title_font_size = 28
topics = iot/IPR/#
grid_columns = 16
grid_rows = 9
object_count = 1
stale_sec = 5

[object.1]
label = R GAP LEFT
label_font_size = 20
value_font_size = 64
unit = mm
style = 1
topic = C-S/3210/IP/ROLL/C/RollC/-/Gap
sensor_name = R_Gap_left
x = 1
y = 1
w = 5
h = 3
```

`style = 1` displays the current dark metric card with the unit shown beside the label.

The title text is controlled by `[monitor] title`, and its size is controlled by `[monitor] title_font_size`. Each `[object.N]` section independently controls its label and measured-value sizes with `label_font_size` and `value_font_size`. If omitted, the existing sizes are retained: `28` for the title, `20` for an object label, and `64` for a measured value. Font sizes must be positive integers. Changes take effect after restarting or recreating the application container.

If a configured sensor does not update for more than `stale_sec`, its value turns red and the card shows `Last Seen: ...` under the label. Broker status is hidden while connected; when disconnected, the title bar shows `Broker Disconnected` in red.

The monitor keeps only the latest MQTT reading in memory for display. Historical storage should be handled by the collection service.

## Local Python Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m roll_plugin_monitor.app --config config.example.ini
```

## Payload

Flat JSON payload:

```json
{"timestamp":"2026-07-08 00:40:38.336+00","R_Gap_left":0.044,"R_Gap_right":-0.078,"R_Temp":49.1}
```

Tag-array payload:

```json
{"timestamp":"2026-06-25T01:02:03+00:00","tags":[{"name":"R_Gap_left","value":12.3,"quality":"good"}]}
```
