from roll_plugin_monitor.config import MonitorConfig
from roll_plugin_monitor.config import MonitorObjectConfig
from roll_plugin_monitor.config import load_config
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


def test_load_config_reads_runtime_log_file_path(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "\n".join(
            [
                "[monitor]",
                "mqtt_host = mqtt",
                "log_file = /app/logs/roll_plugin_monitor.log",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.mqtt_host == "mqtt"
    assert config.log_file == "/app/logs/roll_plugin_monitor.log"


def test_load_config_reads_monitor_objects(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "\n".join(
            [
                "[monitor]",
                "mqtt_host = mqtt",
                "topics = iot/IPR/#",
                "grid_columns = 16",
                "grid_rows = 9",
                "object_count = 2",
                "",
                "[object.1]",
                "label = LEFT",
                "unit = mm",
                "style = 1",
                "topic = iot/IPR/roll",
                "sensor_name = left_thickness",
                "x = 1",
                "y = 1",
                "w = 4",
                "h = 2",
                "",
                "[object.2]",
                "label = TEMP",
                "unit = C",
                "style = 1",
                "topic = iot/IPR/roll",
                "sensor_name = roll_temp",
                "x = 5",
                "y = 1",
                "w = 4",
                "h = 2",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.grid_columns == 16
    assert config.grid_rows == 9
    assert config.objects == (
        MonitorObjectConfig(
            object_id="1",
            label="LEFT",
            unit="mm",
            style=1,
            topic="iot/IPR/roll",
            sensor_name="left_thickness",
            x=1,
            y=1,
            w=4,
            h=2,
        ),
        MonitorObjectConfig(
            object_id="2",
            label="TEMP",
            unit="C",
            style=1,
            topic="iot/IPR/roll",
            sensor_name="roll_temp",
            x=5,
            y=1,
            w=4,
            h=2,
        ),
    )


def test_extracts_object_values_only_when_topic_and_sensor_match():
    config = MonitorConfig(
        mqtt_host="localhost",
        topics=("iot/IPR/#",),
        objects=(
            MonitorObjectConfig(
                object_id="1",
                label="LEFT",
                unit="mm",
                style=1,
                topic="iot/IPR/roll",
                sensor_name="left_thickness",
                x=1,
                y=1,
                w=4,
                h=2,
            ),
            MonitorObjectConfig(
                object_id="2",
                label="OTHER",
                unit="mm",
                style=1,
                topic="iot/IPR/other",
                sensor_name="left_thickness",
                x=5,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )
    payload = {
        "tags": [
            {"name": "left_thickness", "value": 12.3, "quality": "good"},
            {"name": "roll_temp", "value": 50.0, "quality": "good"},
        ]
    }

    reading = extract_reading("iot/IPR/roll", payload, config)

    assert reading.object_values == {"1": 12.3}


def test_monitor_state_merges_object_values():
    state = MonitorState()
    config = MonitorConfig(
        mqtt_host="localhost",
        objects=(
            MonitorObjectConfig(
                object_id="1",
                label="LEFT",
                unit="mm",
                style=1,
                topic="topic",
                sensor_name="left",
                x=1,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )

    state.update(extract_reading("topic", {"tags": [{"name": "left", "value": 1.1}]}, config))
    state.update(extract_reading("topic", {"tags": [{"name": "right", "value": 1.2}]}, config))

    assert state.snapshot().object_values == {"1": 1.1}
