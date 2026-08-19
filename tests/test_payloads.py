from roll_plugin_monitor.config import MonitorConfig
from roll_plugin_monitor.config import MonitorObjectConfig
from roll_plugin_monitor.config import load_config
from roll_plugin_monitor.payloads import extract_reading
from roll_plugin_monitor.state import MonitorState
from datetime import datetime, timezone
import pytest
import re


def test_extracts_tag_payload_sensor_values_and_configured_object_values():
    config = MonitorConfig(
        mqtt_host="localhost",
        topics=("C-S/+/+/+/+/+/+/+/data",),
        objects=(
            MonitorObjectConfig(
                object_id="1",
                label="LEFT",
                unit="mm",
                style=1,
                topic="C-S/site/factory/process/LO001/PH01/-/roll/data",
                sensor_name="R_Gap_left",
                x=1,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )
    payload = {
        "timestamp": "2026-06-25T01:02:03.000+00:00",
        "tags": [
            {"name": "R_Gap_left", "value": 12.3, "quality": "good"},
            {"name": "R_Gap_right", "value": 12.8, "quality": "good"},
            {"name": "R_Temp", "value": 51.2, "quality": "good"},
            {"name": "ignored", "value": 999, "quality": "good"},
        ],
    }

    reading = extract_reading("C-S/site/factory/process/LO001/PH01/-/roll/data", payload, config)

    assert reading.sensor_values == {
        "R_Gap_left": 12.3,
        "R_Gap_right": 12.8,
        "R_Temp": 51.2,
        "ignored": 999.0,
    }
    assert reading.object_values == {"1": 12.3}
    assert reading.sensor_timestamps == {
        "R_Gap_left": datetime(2026, 6, 25, 1, 2, 3, tzinfo=timezone.utc),
        "R_Gap_right": datetime(2026, 6, 25, 1, 2, 3, tzinfo=timezone.utc),
        "R_Temp": datetime(2026, 6, 25, 1, 2, 3, tzinfo=timezone.utc),
        "ignored": datetime(2026, 6, 25, 1, 2, 3, tzinfo=timezone.utc),
    }
    assert reading.object_timestamps == {"1": datetime(2026, 6, 25, 1, 2, 3, tzinfo=timezone.utc)}
    assert reading.topic == "C-S/site/factory/process/LO001/PH01/-/roll/data"
    assert reading.online is True


def test_ignores_bad_quality_iot_gathering_tags():
    config = MonitorConfig(mqtt_host="localhost", topics=("C-S/+/+/+/+/+/+/+/data",))
    payload = {
        "tags": [
            {"name": "R_Gap_left", "value": 12.3, "quality": "bad", "error": "timeout"},
            {"name": "R_Gap_right", "value": 12.8, "quality": "good"},
        ],
    }

    reading = extract_reading("topic", payload, config)

    assert reading.sensor_values == {"R_Gap_right": 12.8}
    assert reading.error == "R_Gap_left: timeout"


def test_flat_payload_uses_generic_sensor_values_without_fixed_fields():
    config = MonitorConfig(mqtt_host="localhost", topics=("iot/IPR/#",))
    payload = {"R_Temp": "52.4", "R_Gap_left": "1.2", "R_Gap_right": "1.5", "R_din1": "1", "R_din2": "0"}

    reading = extract_reading("iot/IPR/AA:BB", payload, config)

    assert reading.sensor_values == {
        "R_Temp": 52.4,
        "R_Gap_left": 1.2,
        "R_Gap_right": 1.5,
        "R_din1": 1.0,
        "R_din2": 0.0,
    }
    assert not hasattr(reading, "left")
    assert not hasattr(reading, "right")
    assert not hasattr(reading, "roll_temp")
    assert not hasattr(reading, "din1")
    assert not hasattr(reading, "din2")


def test_extracts_flat_payload_sensor_values_and_configured_object_values():
    config = MonitorConfig(
        mqtt_host="localhost",
        objects=(
            MonitorObjectConfig(
                object_id="1",
                label="R GAP LEFT",
                unit="mm",
                style=1,
                topic="C-S/3210/IP/ROLL/C/RollC/-/Gap",
                sensor_name="R_Gap_left",
                x=1,
                y=1,
                w=5,
                h=3,
            ),
            MonitorObjectConfig(
                object_id="2",
                label="R TEMP",
                unit="C",
                style=1,
                topic="C-S/3210/IP/ROLL/C/RollC/-/Gap",
                sensor_name="R_Temp",
                x=6,
                y=1,
                w=5,
                h=3,
            ),
        ),
    )
    payload = {
        "timestamp": "2026-07-08 00:40:38.336+00",
        "R_Gap_left": 0.044774999999999565,
        "R_Gap_right": -0.07894999999999808,
        "R_Temp": 49.1,
        "R_din1": 0,
        "R_din2": 0,
    }

    reading = extract_reading("C-S/3210/IP/ROLL/C/RollC/-/Gap", payload, config)

    assert reading.sensor_values == {
        "R_Gap_left": 0.044774999999999565,
        "R_Gap_right": -0.07894999999999808,
        "R_Temp": 49.1,
        "R_din1": 0.0,
        "R_din2": 0.0,
    }
    assert reading.object_values == {"1": 0.044774999999999565, "2": 49.1}
    assert reading.object_timestamps == {
        "1": datetime(2026, 7, 8, 0, 40, 38, 336000, tzinfo=timezone.utc),
        "2": datetime(2026, 7, 8, 0, 40, 38, 336000, tzinfo=timezone.utc),
    }


def test_monitor_state_merges_partial_sensor_readings():
    state = MonitorState()

    state.update(extract_reading("topic", {"R_Gap_left": 1.1}, MonitorConfig(mqtt_host="localhost")))
    state.update(extract_reading("topic", {"R_Gap_right": 1.2, "R_Temp": 55.0}, MonitorConfig(mqtt_host="localhost")))

    snapshot = state.snapshot()
    assert snapshot.sensor_values == {"R_Gap_left": 1.1, "R_Gap_right": 1.2, "R_Temp": 55.0}
    assert not hasattr(snapshot, "left")
    assert not hasattr(snapshot, "right")
    assert not hasattr(snapshot, "roll_temp")
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
                "title = Custom Monitor",
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
                "sensor_name = R_Gap_left",
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
                "sensor_name = R_Temp",
                "x = 5",
                "y = 1",
                "w = 4",
                "h = 2",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.title == "Custom Monitor"
    assert config.grid_columns == 16
    assert config.grid_rows == 9
    assert config.objects == (
        MonitorObjectConfig(
            object_id="1",
            label="LEFT",
            unit="mm",
            style=1,
            topic="iot/IPR/roll",
            sensor_name="R_Gap_left",
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
            sensor_name="R_Temp",
            x=5,
            y=1,
            w=4,
            h=2,
        ),
    )
    assert not hasattr(config, "left_tags")
    assert not hasattr(config, "right_tags")
    assert not hasattr(config, "roll_temp_tags")


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
                sensor_name="R_Gap_left",
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
                sensor_name="R_Gap_left",
                x=5,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )
    payload = {
        "tags": [
            {"name": "R_Gap_left", "value": 12.3, "quality": "good"},
            {"name": "R_Temp", "value": 50.0, "quality": "good"},
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
                sensor_name="R_Gap_left",
                x=1,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )

    state.update(extract_reading("topic", {"tags": [{"name": "R_Gap_left", "value": 1.1}]}, config))
    state.update(extract_reading("topic", {"tags": [{"name": "R_Gap_right", "value": 1.2}]}, config))

    assert state.snapshot().object_values == {"1": 1.1}


def test_monitor_state_tracks_object_last_seen_and_stale_objects():
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
                sensor_name="R_Gap_left",
                x=1,
                y=1,
                w=4,
                h=2,
            ),
        ),
    )
    state.update(
        extract_reading(
            "topic",
            {"timestamp": "2026-07-08T00:40:38+00:00", "R_Gap_left": 1.1},
            config,
        )
    )

    fresh = state.mark_stale(5, datetime(2026, 7, 8, 0, 40, 42, tzinfo=timezone.utc))
    stale = state.mark_stale(5, datetime(2026, 7, 8, 0, 40, 44, tzinfo=timezone.utc))

    assert fresh.object_last_seen == {"1": datetime(2026, 7, 8, 0, 40, 38, tzinfo=timezone.utc)}
    assert fresh.stale_object_ids == set()
    assert stale.object_last_seen == {"1": datetime(2026, 7, 8, 0, 40, 38, tzinfo=timezone.utc)}
    assert stale.stale_object_ids == {"1"}


def test_monitor_state_merges_sensor_values_from_all_messages():
    state = MonitorState()
    config = MonitorConfig(mqtt_host="localhost")

    state.update(extract_reading("topic/a", {"R_Current_R": 1.42}, config))
    state.update(extract_reading("topic/b", {"R_Gap_left": 0.044, "R_Temp": 49.1}, config))

    assert state.snapshot().sensor_values == {
        "R_Current_R": 1.42,
        "R_Gap_left": 0.044,
        "R_Temp": 49.1,
    }


def test_load_config_reads_independent_monitor_and_object_font_sizes(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "\n".join(
            [
                "[monitor]",
                "mqtt_host = mqtt",
                "title_font_size = 32",
                "object_count = 2",
                "",
                "[object.1]",
                "label_font_size = 18",
                "value_font_size = 48",
                "",
                "[object.2]",
                "label_font_size = 24",
                "value_font_size = 72",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.title_font_size == 32
    assert (config.objects[0].label_font_size, config.objects[0].value_font_size) == (18, 48)
    assert (config.objects[1].label_font_size, config.objects[1].value_font_size) == (24, 72)


def test_load_config_uses_existing_font_sizes_as_defaults(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host = mqtt\nobject_count = 1\n\n[object.1]\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.title_font_size == 28
    assert config.objects[0].label_font_size == 20
    assert config.objects[0].value_font_size == 64


def test_title_font_size_can_be_overridden_by_environment(tmp_path, monkeypatch):
    config_file = tmp_path / "config.ini"
    config_file.write_text("[monitor]\nmqtt_host = mqtt\ntitle_font_size = 28\n", encoding="utf-8")
    monkeypatch.setenv("ROLL_MONITOR_TITLE_FONT_SIZE", "36")

    config = load_config(config_file)

    assert config.title_font_size == 36


@pytest.mark.parametrize("invalid_value", ["0", "-1", "large"])
@pytest.mark.parametrize(
    ("setting_line", "expected_setting"),
    [
        ("title_font_size", "[monitor] title_font_size"),
        ("label_font_size", "[object.1] label_font_size"),
        ("value_font_size", "[object.1] value_font_size"),
    ],
)
def test_load_config_rejects_invalid_font_sizes(tmp_path, setting_line, expected_setting, invalid_value):
    title_line = f"{setting_line} = {invalid_value}" if setting_line == "title_font_size" else ""
    object_line = f"{setting_line} = {invalid_value}" if setting_line != "title_font_size" else ""
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[monitor]\nmqtt_host = mqtt\nobject_count = 1\n{title_line}\n\n[object.1]\n{object_line}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=re.escape(f"{expected_setting} must be a positive integer")):
        load_config(config_file)


def test_load_config_reads_display_controls_and_independent_unit_font_sizes(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "\n".join(
            [
                "[monitor]",
                "mqtt_host = mqtt",
                "object_count = 2",
                "title_use = 0",
                "warning_color_use = 1",
                "unit_location = value",
                "",
                "[object.1]",
                "unit_font_size = 16",
                "",
                "[object.2]",
                "unit_font_size = 22",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.title_use is False
    assert config.warning_color_use == 1
    assert config.unit_location == "value"
    assert config.objects[0].unit_font_size == 16
    assert config.objects[1].unit_font_size == 22


def test_load_config_uses_existing_display_behavior_as_defaults(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host = mqtt\nobject_count = 1\n\n[object.1]\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.title_use is True
    assert config.warning_color_use == 2
    assert config.unit_location == "label"
    assert config.objects[0].unit_font_size == 12


def test_display_controls_can_be_overridden_by_environment(tmp_path, monkeypatch):
    config_file = tmp_path / "config.ini"
    config_file.write_text("[monitor]\nmqtt_host = mqtt\n", encoding="utf-8")
    monkeypatch.setenv("ROLL_MONITOR_TITLE_USE", "0")
    monkeypatch.setenv("ROLL_MONITOR_WARNING_COLOR_USE", "0")
    monkeypatch.setenv("ROLL_MONITOR_UNIT_LOCATION", "value")

    config = load_config(config_file)

    assert config.title_use is False
    assert config.warning_color_use == 0
    assert config.unit_location == "value"


@pytest.mark.parametrize(
    ("setting", "invalid_value"),
    [
        ("title_use", "2"),
        ("title_use", "yes"),
        ("warning_color_use", "-1"),
        ("warning_color_use", "3"),
        ("unit_location", "side"),
    ],
)
def test_load_config_rejects_invalid_display_controls(tmp_path, setting, invalid_value):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[monitor]\nmqtt_host = mqtt\n{setting} = {invalid_value}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=re.escape(f"[monitor] {setting} must be one of")):
        load_config(config_file)


@pytest.mark.parametrize("invalid_value", ["0", "-1", "large"])
def test_load_config_rejects_invalid_unit_font_size(tmp_path, invalid_value):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[monitor]\nmqtt_host = mqtt\nobject_count = 1\n\n[object.1]\nunit_font_size = {invalid_value}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=re.escape("[object.1] unit_font_size must be a positive integer")):
        load_config(config_file)


def test_load_config_reads_independent_decimal_places(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host=mqtt\nobject_count=2\n"
        "\n[object.1]\ndecimal_places=1\n"
        "\n[object.2]\ndecimal_places=4\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert [item.decimal_places for item in config.objects] == [1, 4]


def test_load_config_defaults_decimal_places_to_two(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[monitor]\nmqtt_host=mqtt\nobject_count=1\n\n[object.1]\n",
        encoding="utf-8",
    )

    assert load_config(config_file).objects[0].decimal_places == 2


@pytest.mark.parametrize("invalid_value", ["-1", "1.5", "many"])
def test_load_config_rejects_invalid_decimal_places(tmp_path, invalid_value):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[monitor]\nmqtt_host=mqtt\nobject_count=1\n"
        f"\n[object.1]\ndecimal_places={invalid_value}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=re.escape("[object.1] decimal_places must be a non-negative integer"),
    ):
        load_config(config_file)
