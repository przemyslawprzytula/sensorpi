"""Relay control utilities for ventilation fans and LEDs."""
from __future__ import annotations

from enum import Enum
from typing import Dict
import logging

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - hardware import
    import RPi.GPIO as _RPiGPIO
except Exception:  # pragma: no cover - hardware import
    _RPiGPIO = None


class RelayState(Enum):
    OFF = 0
    ON = 1

    @classmethod
    def from_bool(cls, value: bool) -> "RelayState":
        return cls.ON if value else cls.OFF


class _MockGPIO:  # pragma: no cover - development helper
    BCM = "BCM"
    OUT = "OUT"
    LOW = 0
    HIGH = 1

    def __init__(self) -> None:
        self._pins: Dict[int, int] = {}

    def setwarnings(self, _: bool) -> None:  # noqa: D401 - compatibility
        """Ignore warnings."""

    def setmode(self, _: str) -> None:
        return None

    def setup(self, pin: int, _: str) -> None:
        self._pins.setdefault(pin, self.LOW)

    def output(self, pin: int, value: int) -> None:
        self._pins[pin] = value

    def input(self, pin: int) -> int:
        return self._pins.get(pin, self.LOW)

    def cleanup(self) -> None:
        self._pins.clear()


def _resolve_gpio():
    if _RPiGPIO is None:
        LOGGER.warning(
            "RPi.GPIO library not available; using mock GPIO implementation for development"
        )
        return _MockGPIO()
    return _RPiGPIO


class RelayController:
    def __init__(self, pins: Dict[str, int], fail_safe_state: str = "off") -> None:
        self._gpio = _resolve_gpio()
        self._pins = pins
        self._fail_safe = RelayState.ON if fail_safe_state.lower() == "on" else RelayState.OFF
        self._setup()

    def _setup(self) -> None:
        self._gpio.setwarnings(False)
        self._gpio.setmode(self._gpio.BCM)
        for pin in self._pins.values():
            self._gpio.setup(pin, self._gpio.OUT)
            self._gpio.output(pin, RelayState.OFF.value)

    def set_state(self, device_id: str, state: RelayState) -> None:
        pin = self._pins.get(device_id)
        if pin is None:
            raise KeyError(f"Unknown relay device_id '{device_id}'")
        LOGGER.info("Setting relay %s to %s", device_id, state.name)
        self._gpio.output(pin, state.value)

    def get_state(self, device_id: str) -> RelayState:
        pin = self._pins.get(device_id)
        if pin is None:
            raise KeyError(f"Unknown relay device_id '{device_id}'")
        value = self._gpio.input(pin)
        return RelayState(value)

    def fail_safe(self) -> None:
        LOGGER.warning("Activating relay fail-safe state (%s)", self._fail_safe.name)
        for device_id in self._pins:
            self.set_state(device_id, self._fail_safe)

    def cleanup(self) -> None:
        LOGGER.info("Cleaning up relay controller")
        self._gpio.cleanup()
