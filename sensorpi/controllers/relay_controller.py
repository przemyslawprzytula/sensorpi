"""Relay control utilities for ventilation fans and LEDs."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
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

    def to_gpio(self, active_low: bool = True) -> int:
        """Convert state to GPIO value, accounting for active-low relays."""
        if active_low:
            # Active-LOW: GPIO LOW = relay ON, GPIO HIGH = relay OFF
            return 0 if self == RelayState.ON else 1
        else:
            # Active-HIGH: GPIO HIGH = relay ON, GPIO LOW = relay OFF
            return 1 if self == RelayState.ON else 0


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
    """Controller for relay module with dependency management.

    Dependencies:
    - pwr_12v must be ON when water_valve, grow_led_1, or grow_led_2 is ON
    - ground_exchanger_high requires ground_exchanger_low to be ON first
    """

    def __init__(
        self,
        pins: Dict[str, int],
        fail_safe_state: str = "off",
        active_low: bool = True,
        dependencies: Optional[Dict[str, Any]] = None,
        nc_wiring: bool = False,
    ) -> None:
        self._gpio = _resolve_gpio()
        self._pins = pins
        self._active_low = active_low
        self._fail_safe = RelayState.ON if fail_safe_state.lower() == "on" else RelayState.OFF
        self._states: Dict[str, RelayState] = {}
        self._dependencies = dependencies or {}
        # NC wiring: devices wired to Normally Closed contacts
        # When relay is de-energized (RPi off), NC is closed = device ON (fail-safe)
        # To turn device OFF, we energize the relay (opens NC contact)
        self._nc_wiring = nc_wiring
        self._setup()

    def _setup(self) -> None:
        self._gpio.setwarnings(False)
        self._gpio.setmode(self._gpio.BCM)
        for device_id, pin in self._pins.items():
            self._gpio.setup(pin, self._gpio.OUT)
            # Initialize: de-energize all relays (GPIO HIGH for active-low module)
            # With NC wiring, this means all devices start ON (fail-safe default)
            self._gpio.output(pin, RelayState.OFF.to_gpio(self._active_low))
            # Logical state tracks device state, not relay coil state
            # With NC wiring: relay de-energized = device ON
            self._states[device_id] = RelayState.ON if self._nc_wiring else RelayState.OFF

    def _set_raw(self, device_id: str, state: RelayState) -> None:
        """Set relay state without dependency checks.

        With NC wiring:
        - Device ON  = relay de-energized (GPIO HIGH for active-low) = NC closed
        - Device OFF = relay energized (GPIO LOW for active-low) = NC open
        """
        pin = self._pins.get(device_id)
        if pin is None:
            raise KeyError(f"Unknown relay device_id '{device_id}'")
        LOGGER.info("Setting device %s to %s", device_id, state.name)

        # Determine relay coil state based on wiring
        if self._nc_wiring:
            # NC wiring: invert - to turn device OFF, energize relay (ON)
            coil_state = RelayState.OFF if state == RelayState.ON else RelayState.ON
        else:
            # NO wiring: direct - to turn device ON, energize relay (ON)
            coil_state = state

        self._gpio.output(pin, coil_state.to_gpio(self._active_low))
        self._states[device_id] = state

    def _get_dependents(self, device_id: str) -> List[str]:
        """Get list of devices that require this device to be ON."""
        dep_config = self._dependencies.get(device_id, {})
        return dep_config.get("required_by", [])

    def _get_requirements(self, device_id: str) -> List[str]:
        """Get list of devices that must be ON before this device."""
        dep_config = self._dependencies.get(device_id, {})
        return dep_config.get("requires", [])

    def _should_auto_on(self, device_id: str) -> bool:
        """Check if device should auto-turn-on when dependents need it."""
        dep_config = self._dependencies.get(device_id, {})
        return dep_config.get("auto_on", False)

    def _should_auto_off(self, device_id: str) -> bool:
        """Check if device should auto-turn-off when no dependents need it."""
        dep_config = self._dependencies.get(device_id, {})
        return dep_config.get("auto_off", False)

    def _any_dependent_on(self, device_id: str) -> bool:
        """Check if any dependent device is currently ON."""
        dependents = self._get_dependents(device_id)
        return any(self._states.get(d) == RelayState.ON for d in dependents)

    def set_state(self, device_id: str, state: RelayState) -> None:
        """Set relay state with automatic dependency management."""
        if device_id not in self._pins:
            raise KeyError(f"Unknown relay device_id '{device_id}'")

        if state == RelayState.ON:
            # Check if this device requires others to be ON first
            requirements = self._get_requirements(device_id)
            for req in requirements:
                if self._states.get(req) != RelayState.ON:
                    LOGGER.info("Auto-enabling required relay %s for %s", req, device_id)
                    self._set_raw(req, RelayState.ON)

            # Check if this device needs a power supply relay
            for power_relay, dep_config in self._dependencies.items():
                if device_id in dep_config.get("required_by", []):
                    if dep_config.get("auto_on") and self._states.get(power_relay) != RelayState.ON:
                        LOGGER.info("Auto-enabling power relay %s for %s", power_relay, device_id)
                        self._set_raw(power_relay, RelayState.ON)

            self._set_raw(device_id, state)

        else:  # state == RelayState.OFF
            # First turn off the device
            self._set_raw(device_id, state)

            # Check if we should turn off any device that required this one
            for other_device in self._pins:
                if device_id in self._get_requirements(other_device):
                    if self._states.get(other_device) == RelayState.ON:
                        LOGGER.info("Auto-disabling %s because required %s is OFF", other_device, device_id)
                        self._set_raw(other_device, RelayState.OFF)

            # Check if any power relay should auto-turn-off
            for power_relay, dep_config in self._dependencies.items():
                if dep_config.get("auto_off") and not self._any_dependent_on(power_relay):
                    if self._states.get(power_relay) == RelayState.ON:
                        LOGGER.info("Auto-disabling power relay %s (no dependents active)", power_relay)
                        self._set_raw(power_relay, RelayState.OFF)

    def get_state(self, device_id: str) -> RelayState:
        if device_id not in self._pins:
            raise KeyError(f"Unknown relay device_id '{device_id}'")
        return self._states.get(device_id, RelayState.OFF)

    def get_all_states(self) -> Dict[str, RelayState]:
        """Return current state of all relays."""
        return dict(self._states)

    def fail_safe(self) -> None:
        LOGGER.warning("Activating relay fail-safe state (%s)", self._fail_safe.name)
        for device_id in self._pins:
            self._set_raw(device_id, self._fail_safe)

    def cleanup(self) -> None:
        LOGGER.info("Cleaning up relay controller")
        self._gpio.cleanup()
