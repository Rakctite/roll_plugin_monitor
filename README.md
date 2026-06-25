# Roll Plugin Monitor

Raspberry Pi Docker app that subscribes to MQTT messages and displays roll left/right values and roll temperature with Tkinter.

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
203.228.107.184:5000/btx/roll_plugin_monitor:1.0.0
```

## Object Layout

The UI can be configured from `config.ini` with monitor objects. The screen is split into a grid, normally `16 x 9`. Coordinates are 1-based, so `x = 1` and `y = 1` is the top-left grid cell.

Each object updates only when both the MQTT topic and the payload tag name match:

```ini
[monitor]
topics = iot/IPR/#
grid_columns = 16
grid_rows = 9
object_count = 1

[object.1]
label = LEFT
unit = mm
style = 1
topic = iot/IPR/roll
sensor_name = left_thickness
x = 1
y = 1
w = 5
h = 3
```

`style = 1` displays the current dark metric card with the unit shown beside the label.

## Local Python Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m roll_plugin_monitor.app --config config.example.ini
```

## Payload

`iot_gathering` measurement payload:

```json
{"timestamp":"2026-06-25T01:02:03+00:00","tags":[{"name":"left_thickness","value":12.3,"quality":"good"}]}
```

Legacy payload:

```json
{"temperature":"52.4","left":"1.2","right":"1.5","din1":"1","din2":"0"}
```
