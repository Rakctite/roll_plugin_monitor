# Roll Plugin Monitor

MQTT 메시지를 구독해서 롤 좌/우 값과 롤 온도를 표시하는 Raspberry Pi용 UI 앱입니다.

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\src"
python -m roll_plugin_monitor.app --config config.example.ini
```

Linux/Raspberry Pi:

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

