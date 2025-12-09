"""Lightweight HTTP API for Raspberry Pi relay control.

This runs on the RPi alongside the data collector, providing
remote relay control endpoints for the server dashboard.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, jsonify, request

from sensorpi.config.settings import Settings
from sensorpi.controllers import RelayController

LOGGER = logging.getLogger(__name__)

app = Flask(__name__)

# Global relay controller - initialized on startup
_relay_controller: RelayController | None = None
_settings: Settings | None = None


def init_app(settings: Settings, relay_controller: RelayController | None) -> None:
    """Initialize the API with settings and relay controller."""
    global _relay_controller, _settings
    _relay_controller = relay_controller
    _settings = settings


@app.route("/health", methods=["GET"])
def health() -> tuple[Dict[str, Any], int]:
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "relay_controller": _relay_controller is not None,
    }), 200


@app.route("/relays", methods=["GET"])
def get_relays() -> tuple[Dict[str, Any], int]:
    """Get all relay states and configuration."""
    if _relay_controller is None:
        return jsonify({"error": "Relay controller not initialized"}), 503

    if _settings is None:
        return jsonify({"error": "Settings not loaded"}), 503

    relay_cfg = _settings.relays
    states = _relay_controller.get_all_states()
    names = relay_cfg.get("names", {})

    relays = []
    for device_id, state in states.items():
        relays.append({
            "id": device_id,
            "name": names.get(device_id, device_id),
            "state": state.name.lower(),
            "pin": relay_cfg.get("pins", {}).get(device_id),
        })

    return jsonify({
        "relays": relays,
        "dependencies": relay_cfg.get("dependencies", {}),
        "nc_wiring": relay_cfg.get("nc_wiring", False),
    }), 200


@app.route("/relays/<device_id>", methods=["GET"])
def get_relay(device_id: str) -> tuple[Dict[str, Any], int]:
    """Get single relay state."""
    if _relay_controller is None:
        return jsonify({"error": "Relay controller not initialized"}), 503

    try:
        state = _relay_controller.get_state(device_id)
        return jsonify({
            "id": device_id,
            "state": state.name.lower(),
        }), 200
    except KeyError:
        return jsonify({"error": f"Unknown relay: {device_id}"}), 404


@app.route("/relays/<device_id>", methods=["POST"])
def set_relay(device_id: str) -> tuple[Dict[str, Any], int]:
    """Set relay state. Body: {"state": "on"|"off"}"""
    if _relay_controller is None:
        return jsonify({"error": "Relay controller not initialized"}), 503

    data = request.get_json()
    if not data or "state" not in data:
        return jsonify({"error": "Missing 'state' in request body"}), 400

    state_str = data["state"].lower()
    if state_str not in ("on", "off"):
        return jsonify({"error": "State must be 'on' or 'off'"}), 400

    try:
        from sensorpi.controllers.relay_controller import RelayState
        new_state = RelayState.ON if state_str == "on" else RelayState.OFF
        _relay_controller.set(device_id, new_state)

        LOGGER.info("Relay %s set to %s via API", device_id, state_str)

        return jsonify({
            "id": device_id,
            "state": state_str,
            "message": f"Relay {device_id} set to {state_str}",
        }), 200
    except KeyError:
        return jsonify({"error": f"Unknown relay: {device_id}"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/relays/all-off", methods=["POST"])
def all_relays_off() -> tuple[Dict[str, Any], int]:
    """Turn off all relays (emergency stop)."""
    if _relay_controller is None:
        return jsonify({"error": "Relay controller not initialized"}), 503

    _relay_controller.all_off()
    LOGGER.warning("All relays turned OFF via API emergency stop")

    return jsonify({
        "message": "All relays turned off",
        "states": {
            k: v.name.lower()
            for k, v in _relay_controller.get_all_states().items()
        },
    }), 200


def run_api(settings: Settings, relay_controller: RelayController | None) -> None:
    """Run the Flask API server."""
    init_app(settings, relay_controller)
    api_cfg = settings.api
    host = api_cfg.get("rpi_host", "0.0.0.0")
    port = api_cfg.get("rpi_port", 5000)

    LOGGER.info("Starting RPi API on %s:%d", host, port)
    # use_reloader=False required when running in background thread
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


__all__ = ["app", "init_app", "run_api"]
