from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import load_config
from .mqtt_client import MqttMonitorClient
from .ui import RollMonitorApp


def configure_logging(log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT based roll monitor UI")
    parser.add_argument("--config", help="config ini path")
    args = parser.parse_args()

    config = load_config(args.config)
    configure_logging(config.log_file)
    app = RollMonitorApp(config)
    client = MqttMonitorClient(config, app.enqueue)
    try:
        client.start()
        app.run()
    finally:
        client.stop()


if __name__ == "__main__":
    main()
