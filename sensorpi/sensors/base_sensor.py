"""Abstract sensor interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class SensorReading:
    sensor_id: str
    measurement: str
    value: float
    unit: str
    timestamp: datetime
    location: str = ""
    metadata: Optional[Dict[str, Any]] = None


class BaseSensor(ABC):
    """Base class for all sensors."""

    def __init__(self, sensor_id: str, location: str = "") -> None:
        self.sensor_id = sensor_id
        self.location = location
        self._healthy = True
        self._last_error: Optional[str] = None

    @abstractmethod
    def read(self) -> list[SensorReading]:
        """Fetch one or more readings from the sensor."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the sensor communication."""

    def mark_unhealthy(self, error: Exception) -> None:
        self._healthy = False
        self._last_error = str(error)

    def mark_healthy(self) -> None:
        self._healthy = True
        self._last_error = None

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
