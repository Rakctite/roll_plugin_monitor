from roll_plugin_monitor.config import MonitorConfig
from roll_plugin_monitor.payloads import extract_reading
from roll_plugin_monitor.state import MonitorState


def test_extracts_iot_gathering_tags_by_configured_names():
    config = MonitorConfig(
        mqtt_host="localhost",
        topics=("C-S/+/+/+/+/+/+/+/data",),
        left_tags=("left_thickness",),
        right_tags=("right_thickness",),
        roll_temp_tags=("roll_temp",),
    )
    payload = {
        "timestamp": "2026-06-25T01:02:03.000+00:00",
        "tags": [
            {"name": "left_thickness", "value": 12.3, "quality": "good"},
            {"name": "right_thickness", "value": 12.8, "quality": "good"},
            {"name": "roll_temp", "value": 51.2, "quality": "good"},
            {"name": "ignored", "value": 999, "quality": "good"},
        ],
    }

    reading = extract_reading("C-S/site/factory/process/LO001/PH01/-/roll/data", payload, config)

    assert reading.left == 12.3
    assert reading.right == 12.8
    assert reading.roll_temp == 51.2
    assert reading.topic == "C-S/site/factory/process/LO001/PH01/-/roll/data"
    assert reading.online is True


def test_ignores_bad_quality_iot_gathering_tags():
    config = MonitorConfig(
        mqtt_host="localhost",
        topics=("C-S/+/+/+/+/+/+/+/data",),
        left_tags=("left",),
        right_tags=("right",),
        roll_temp_tags=("temp",),
    )
    payload = {
        "tags": [
            {"name": "left", "value": 12.3, "quality": "bad", "error": "timeout"},
            {"name": "right", "value": 12.8, "quality": "good"},
        ],
    }

    reading = extract_reading("topic", payload, config)

    assert reading.left is None
    assert reading.right == 12.8
    assert reading.error == "left: timeout"


def test_extracts_legacy_roll_payload():
    config = MonitorConfig(mqtt_host="localhost", topics=("iot/IPR/#",))
    payload = {"temperature": "52.4", "left": "1.2", "right": "1.5", "din1": "1", "din2": "0"}

    reading = extract_reading("iot/IPR/AA:BB", payload, config)

    assert reading.roll_temp == 52.4
    assert reading.left == 1.2
    assert reading.right == 1.5
    assert reading.din1 == 1
    assert reading.din2 == 0


def test_monitor_state_merges_partial_readings():
    state = MonitorState()

    state.update(extract_reading("topic", {"left": 1.1}, MonitorConfig(mqtt_host="localhost")))
    state.update(extract_reading("topic", {"right": 1.2, "temperature": 55.0}, MonitorConfig(mqtt_host="localhost")))

    snapshot = state.snapshot()
    assert snapshot.left == 1.1
    assert snapshot.right == 1.2
    assert snapshot.roll_temp == 55.0
    assert snapshot.online is True
