"""Driver wrapper for MCP9808 temperature sensors."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .base_sensor import BaseSensor, SensorReading

try:  # pragma: no cover - hardware import
    import board
    import busio
    from adafruit_mcp9808 import MCP9808
except Exception:  # pragma: no cover - hardware import
    board = None
    busio = None
    MCP9808 = None


class MCP9808Sensor(BaseSensor):
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
        self._device: Optional[MCP9808] = None

    def initialize(self) -> None:
        if MCP9808 is None:
            raise RuntimeError(
                "adafruit-circuitpython-mcp9808 is not installed or I2C stack is unavailable"
            )
        if self._i2c_bus is None:
            if busio is None or board is None:
                raise RuntimeError("I2C bus is not available on this platform")
            self._i2c_bus = busio.I2C(board.SCL, board.SDA)
        self._device = MCP9808(self._i2c_bus, address=self.address)

    def read(self) -> list[SensorReading]:
        if self._device is None:
            raise RuntimeError("Sensor not initialized")
        temperature = float(self._device.temperature)
        reading = SensorReading(
            sensor_id=self.sensor_id,
            measurement="temperature",
            value=temperature,
            unit="C",
            timestamp=datetime.now(timezone.utc),
            location=self.location,
            metadata={"address": self.address},
        )
        return [reading]
