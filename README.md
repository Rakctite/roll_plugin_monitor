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
