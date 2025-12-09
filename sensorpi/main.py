"""SensorPi command-line entry point."""
from __future__ import annotations

import argparse
import sys
import threading

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
    parser.add_argument(
        "--with-api",
        action="store_true",
        help="Run the HTTP API server for remote relay control",
    )
    return parser.parse_args()


def _build_relay_controller(settings: Settings, skip: bool) -> RelayController | None:
    if skip:
        return None
    relay_cfg = settings.relays
    pins = relay_cfg.get("pins")
    if not pins:
        return None
    return RelayController(
        pins=pins,
        fail_safe_state=relay_cfg.get("fail_safe_state", "off"),
        active_low=True,
        dependencies=relay_cfg.get("dependencies", {}),
        nc_wiring=relay_cfg.get("nc_wiring", False),
    )


def _start_api_server(settings: Settings, relay_controller: RelayController | None) -> None:
    """Start the Flask API server in a background thread."""
    from sensorpi.api.rpi_api import run_api
    run_api(settings, relay_controller)


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

    # Start API server in background thread if requested
    if args.with_api:
        api_thread = threading.Thread(
            target=_start_api_server,
            args=(settings, relay_controller),
            daemon=True,
        )
        api_thread.start()

    service.run_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
