from roll_plugin_monitor.config import MonitorConfig
from roll_plugin_monitor.config import MonitorObjectConfig
from roll_plugin_monitor.mqtt_client import MqttMonitorClient
from roll_plugin_monitor.payloads import RollReading
from roll_plugin_monitor.state import MonitorState
from roll_plugin_monitor.ui import LatestReadingBuffer
from roll_plugin_monitor.ui import object_place_geometry
import roll_plugin_monitor.ui as ui
from datetime import datetime, timezone

import pytest


def test_latest_reading_buffer_keeps_latest_reading_per_topic_in_arrival_order():
    buffer = LatestReadingBuffer()
    temp_first = RollReading(topic="temp", object_values={"3": 36.9})
    gap = RollReading(topic="gap", object_values={"1": 3.99, "2": 4.0})
    temp_latest = RollReading(topic="temp", object_values={"3": 37.0})

    buffer.put(temp_first)
    buffer.put(gap)
    buffer.put(temp_latest)

    assert buffer.take_pending() == (temp_latest, gap)
    assert buffer.take_pending() == ()


def test_pending_topic_batch_merges_temp_and_gap_values_into_state():
    buffer = LatestReadingBuffer()
    buffer.put(RollReading(topic="temp", object_values={"3": 37.0}))
    buffer.put(RollReading(topic="gap", object_values={"1": 3.99, "2": 4.0}))
    state = MonitorState()

    ui.apply_pending_readings(buffer, state)

    assert state.snapshot().object_values == {"3": 37.0, "1": 3.99, "2": 4.0}


class _FakeClient:
    def __init__(self) -> None:
        self.subscriptions: list[str] = []

    def subscribe(self, topic: str) -> None:
        self.subscriptions.append(topic)


def test_mqtt_client_reports_connection_status_changes():
    statuses: list[bool] = []
    client = MqttMonitorClient(
        MonitorConfig(mqtt_host="localhost", topics=("topic/a",)),
        lambda reading: None,
        on_connection_change=statuses.append,
    )
    fake_client = _FakeClient()

    client._on_connect(fake_client, None, {}, 0)
    client._on_disconnect(fake_client, None, 1)

    assert statuses == [True, False]
    assert fake_client.subscriptions == ["topic/a"]


def test_object_place_geometry_is_independent_per_object_width():
    config = MonitorConfig(mqtt_host="localhost", grid_columns=16, grid_rows=9)
    first = MonitorObjectConfig(
        object_id="1",
        label="First",
        unit="",
        style=1,
        topic="topic",
        sensor_name="a",
        x=1,
        y=1,
        w=4,
        h=2,
    )
    third_wide = MonitorObjectConfig(
        object_id="3",
        label="Third",
        unit="",
        style=1,
        topic="topic",
        sensor_name="c",
        x=6,
        y=5,
        w=8,
        h=2,
    )
    third_narrow = MonitorObjectConfig(
        object_id="3",
        label="Third",
        unit="",
        style=1,
        topic="topic",
        sensor_name="c",
        x=6,
        y=5,
        w=3,
        h=2,
    )

    assert object_place_geometry(first, config) == object_place_geometry(first, config)
    assert object_place_geometry(third_wide, config)["relwidth"] == 8 / 16
    assert object_place_geometry(third_narrow, config)["relwidth"] == 3 / 16
    assert object_place_geometry(first, config)["relwidth"] == 4 / 16


def test_object_place_geometry_clamps_objects_to_grid_bounds():
    config = MonitorConfig(mqtt_host="localhost", grid_columns=16, grid_rows=9)
    monitor_object = MonitorObjectConfig(
        object_id="5",
        label="Overflow",
        unit="",
        style=1,
        topic="topic",
        sensor_name="x",
        x=13,
        y=7,
        w=6,
        h=2,
    )

    geometry = object_place_geometry(monitor_object, config)

    assert geometry["relx"] == 12 / 16
    assert geometry["relwidth"] == 4 / 16


def test_ui_font_specs_use_monitor_and_object_font_sizes():
    config = MonitorConfig(mqtt_host="localhost", title_font_size=34)
    monitor_object = MonitorObjectConfig(
        object_id="1",
        label="PRESSURE",
        unit="bar",
        style=1,
        topic="topic",
        sensor_name="pressure",
        x=1,
        y=1,
        w=4,
        h=2,
        label_font_size=22,
        value_font_size=70,
    )

    assert ui.title_font(config) == ("DejaVu Sans Condensed", 34, "bold")
    assert ui.object_label_font(monitor_object) == ("DejaVu Sans Condensed", 22, "bold")
    assert ui.object_value_font(monitor_object) == ("DejaVu Sans Condensed", 70, "bold")


def test_body_grid_options_use_full_height_when_title_is_disabled():
    assert ui.body_grid_options(MonitorConfig(mqtt_host="mqtt", title_use=True)) == {
        "row": 1,
        "pady": (0, 24),
    }
    assert ui.body_grid_options(MonitorConfig(mqtt_host="mqtt", title_use=False)) == {
        "row": 0,
        "pady": (24, 24),
    }


def test_warning_presentation_supports_hidden_neutral_and_red_modes():
    assert ui.warning_presentation(0) == ui.WarningPresentation(False, "#bbbbbb", "#bbbbbb", "white")
    assert ui.warning_presentation(1) == ui.WarningPresentation(True, "#bbbbbb", "#bbbbbb", "white")
    assert ui.warning_presentation(2) == ui.WarningPresentation(True, "#ff4d4d", "#ff6b6b", "#ff4d4d")


def test_warning_text_respects_warning_mode():
    last_seen = datetime(2026, 8, 19, 1, 2, 3, tzinfo=timezone.utc)

    assert ui.broker_status_text(False, 0) == ""
    assert ui.broker_status_text(False, 1) == "Broker Disconnected"
    assert ui.broker_status_text(False, 2) == "Broker Disconnected"
    assert ui.broker_status_text(True, 2) == ""
    assert ui.last_seen_text(True, last_seen, 0) == ""
    assert ui.last_seen_text(True, last_seen, 1).startswith("Last Seen: ")
    assert ui.last_seen_text(True, last_seen, 2).startswith("Last Seen: ")
    assert ui.last_seen_text(False, last_seen, 2) == ""
    assert ui.last_seen_text(True, None, 2) == ""


def test_unit_text_and_font_follow_location_and_object_size():
    monitor_object = MonitorObjectConfig(
        object_id="1",
        label="PRESSURE",
        unit="bar",
        style=1,
        topic="topic",
        sensor_name="pressure",
        x=1,
        y=1,
        w=4,
        h=2,
        unit_font_size=18,
    )

    assert ui.unit_text("bar", "label") == " (bar)"
    assert ui.unit_text("bar", "value") == " bar"
    assert ui.unit_text("", "value") == ""
    assert ui.object_unit_font(monitor_object) == ("DejaVu Sans Condensed", 18, "bold")


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        (None, 2, "-"),
        (13000, 2, "13000"),
        (13000.123, 2, "13000.12"),
        (0.129, 2, "0.13"),
        (3.6, 3, "3.600"),
        (7.9, 0, "8"),
    ],
)
def test_format_value_preserves_integers_and_controls_fraction(value, places, expected):
    assert ui.format_value(value, places) == expected
