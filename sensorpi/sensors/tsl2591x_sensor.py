"""Driver wrapper for the TSL2591X lux sensor."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .base_sensor import BaseSensor, SensorReading

try:  # pragma: no cover - hardware import
    import board
    import busio
    import adafruit_tsl2591
except Exception:  # pragma: no cover - hardware import
    board = None
    busio = None
    adafruit_tsl2591 = None


class TSL2591XSensor(BaseSensor):
    def __init__(
        self,
        sensor_id: str,
        address: int,
        location: str = "",
        i2c_bus: Optional["busio.I2C"] = None,
    ) -> None:
        super().__init__(sensor_id=sensor_id, location=location)
        self.address = address
        self._i2c_bus = i2c_bus
        self._device: Optional["adafruit_tsl2591.TSL2591"] = None

    def initialize(self) -> None:
        if adafruit_tsl2591 is None:
            raise RuntimeError(
                "adafruit-circuitpython-tsl2591 is not installed or I2C stack is unavailable"
            )
        if self._i2c_bus is None:
            if busio is None or board is None:
                raise RuntimeError("I2C bus is not available on this platform")
            self._i2c_bus = busio.I2C(board.SCL, board.SDA)
        self._device = adafruit_tsl2591.TSL2591(self._i2c_bus, address=self.address)

    def read(self) -> list[SensorReading]:
        if self._device is None:
            raise RuntimeError("Sensor not initialized")
        lux = float(self._device.lux or 0.0)
        reading = SensorReading(
            sensor_id=self.sensor_id,
            measurement="light",
            value=lux,
            unit="lux",
            timestamp=datetime.now(timezone.utc),
            location=self.location,
            metadata={
                "broadband": float(self._device.broadband),
                "infrared": float(self._device.infrared),
                "visible": float(self._device.visible),
            },
        )
        return [reading]
