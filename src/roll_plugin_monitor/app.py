from __future__ import annotations

import argparse
import logging

from .config import load_config
from .mqtt_client import MqttMonitorClient
from .ui import RollMonitorApp


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT based roll monitor UI")
    parser.add_argument("--config", help="config ini path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config = load_config(args.config)
    app = RollMonitorApp(config)
    client = MqttMonitorClient(config, app.enqueue)
    try:
        client.start()
        app.run()
    finally:
        client.stop()


if __name__ == "__main__":
    main()

