"""SensorPi command-line entry point."""
from __future__ import annotations

import argparse
import sys

from sensorpi.config.settings import Settings
from sensorpi.controllers import RelayController
from sensorpi.services.data_collector import DataCollectorService
from sensorpi.services.logger import configure_logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SensorPi greenhouse controller")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to settings JSON file (defaults to config/settings.json)",
    )
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle")
    parser.add_argument("--debug", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--skip-relays",
        action="store_true",
        help="Skip relay initialization/automation (sensor collection only)",
    )
    return parser.parse_args()


def _build_relay_controller(settings: Settings, skip: bool) -> RelayController | None:
    if skip:
        return None
    relay_cfg = settings.relays
    pins = relay_cfg.get("pins")
    if not pins:
        return None
    return RelayController(pins, relay_cfg.get("fail_safe_state", "off"))


def main() -> int:
    args = _parse_args()
    configure_logging(debug=args.debug)
    settings = Settings(config_path=args.config) if args.config else Settings()
    relay_controller = _build_relay_controller(settings, args.skip_relays)
    service = DataCollectorService(settings=settings, relay_controller=relay_controller)

    if args.once:
        count = service.run_once()
        print(f"Captured {count} sensor readings")
        return 0

    service.run_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
