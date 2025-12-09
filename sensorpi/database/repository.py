"""Data access helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from sensorpi.database import models
from sensorpi.sensors import SensorReading


class SensorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_readings(self, readings: Iterable[SensorReading]) -> None:
        entities = []
        for reading in readings:
            try:
                sensor_type = models.SensorType(reading.measurement)
            except ValueError as exc:  # pragma: no cover - configuration error
                raise ValueError(
                    f"Unsupported measurement '{reading.measurement}' for persistence"
                ) from exc
            entities.append(
                models.SensorReading(
                    sensor_id=reading.sensor_id,
                    sensor_type=sensor_type,
                    measurement=reading.measurement,
                    value=reading.value,
                    unit=reading.unit,
                    location=reading.location,
                )
            )
        self._session.add_all(entities)


__all__ = ["SensorRepository"]
