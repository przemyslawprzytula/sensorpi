"""Driver wrapper for the Si7021 temperature & humidity sensor."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .base_sensor import BaseSensor, SensorReading

try:  # pragma: no cover - hardware import
    import board
    import busio
    import adafruit_si7021
except Exception:  # pragma: no cover - hardware import
    board = None
    busio = None
    adafruit_si7021 = None


class SI7021Sensor(BaseSensor):
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
        self._device: Optional["adafruit_si7021.SI7021"] = None

    def initialize(self) -> None:
        if adafruit_si7021 is None:
            raise RuntimeError(
                "adafruit-circuitpython-si7021 is not installed or I2C stack is unavailable"
            )
        if self._i2c_bus is None:
            if busio is None or board is None:
                raise RuntimeError("I2C bus is not available on this platform")
            self._i2c_bus = busio.I2C(board.SCL, board.SDA)
        self._device = adafruit_si7021.SI7021(self._i2c_bus)

    def read(self) -> list[SensorReading]:
        if self._device is None:
            raise RuntimeError("Sensor not initialized")
        timestamp = datetime.now(timezone.utc)
        temperature = float(self._device.temperature)
        humidity = float(self._device.relative_humidity)
        return [
            SensorReading(
                sensor_id=f"{self.sensor_id}_temp",
                measurement="temperature",
                value=temperature,
                unit="C",
                timestamp=timestamp,
                location=self.location,
                metadata={"address": self.address},
            ),
            SensorReading(
                sensor_id=f"{self.sensor_id}_humidity",
                measurement="humidity",
                value=humidity,
                unit="%RH",
                timestamp=timestamp,
                location=self.location,
                metadata={"address": self.address},
            ),
        ]
