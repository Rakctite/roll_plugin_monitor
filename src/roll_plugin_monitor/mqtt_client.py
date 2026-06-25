from __future__ import annotations

import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt

from .config import MonitorConfig
from .payloads import RollReading, extract_reading

Logger = Callable[[str], None]


class MqttMonitorClient:
    def __init__(
        self,
        config: MonitorConfig,
        on_reading: Callable[[RollReading], None],
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._on_reading = on_reading
        self._logger = logger or logging.getLogger(__name__)
        self._client: mqtt.Client | None = None

    def start(self) -> None:
        client = mqtt.Client(client_id=self._config.client_id)
        if self._config.username:
            client.username_pw_set(self._config.username, self._config.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.connect(self._config.mqtt_host, self._config.mqtt_port, keepalive=30)
        client.loop_start()
        self._client = client

    def stop(self) -> None:
        if self._client is None:
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._client = None

    def _on_connect(self, client: mqtt.Client, userdata: object, flags: dict, rc: int) -> None:
        if rc != 0:
            self._logger.error("mqtt connect failed rc=%s", rc)
            return
        for topic in self._config.topics:
            client.subscribe(topic)
            self._logger.info("subscribed mqtt topic %s", topic)

    def _on_disconnect(self, client: mqtt.Client, userdata: object, rc: int) -> None:
        if rc:
            self._logger.warning("mqtt disconnected rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            reading = extract_reading(message.topic, message.payload, self._config)
        except Exception:
            self._logger.exception("failed to parse mqtt payload topic=%s", message.topic)
            return
        self._on_reading(reading)

