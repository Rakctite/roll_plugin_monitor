from roll_plugin_monitor.config import MonitorConfig
from roll_plugin_monitor.config import MonitorObjectConfig
from roll_plugin_monitor.mqtt_client import MqttMonitorClient
from roll_plugin_monitor.payloads import RollReading
from roll_plugin_monitor.ui import LatestReadingBuffer
from roll_plugin_monitor.ui import object_place_geometry


def test_latest_reading_buffer_keeps_only_latest_value():
    buffer = LatestReadingBuffer()
    first = RollReading(topic="first", sensor_values={"a": 1.0})
    second = RollReading(topic="second", sensor_values={"b": 2.0})

    buffer.put(first)
    buffer.put(second)

    assert buffer.take_latest() == second
    assert buffer.take_latest() is None


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
