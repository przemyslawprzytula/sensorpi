"""Data access helpers."""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from sensorpi.database import models
from sensorpi.sensors import SensorReading as SensorReadingDTO


class SensorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._sensor_cache: Dict[str, models.Sensor] = {}

    def _get_or_create_sensor(self, reading: SensorReadingDTO) -> models.Sensor:
        """Get existing sensor or create new one."""
        # Check cache first
        if reading.sensor_id in self._sensor_cache:
            return self._sensor_cache[reading.sensor_id]

        # Query database
        sensor = (
            self._session.query(models.Sensor)
            .filter(models.Sensor.sensor_id == reading.sensor_id)
            .first()
        )

        if sensor is None:
            # Create new sensor
            try:
                sensor_type = models.SensorType(reading.measurement)
            except ValueError as exc:
                raise ValueError(
                    f"Unsupported measurement '{reading.measurement}' for persistence"
                ) from exc

            sensor = models.Sensor(
                sensor_id=reading.sensor_id,
                sensor_type=sensor_type,
                measurement=reading.measurement,
                unit=reading.unit,
                location=reading.location,
            )
            self._session.add(sensor)
            self._session.flush()  # Get the ID

        self._sensor_cache[reading.sensor_id] = sensor
        return sensor

    def save_readings(self, readings: Iterable[SensorReadingDTO]) -> None:
        """Save sensor readings to database."""
        for reading in readings:
            sensor = self._get_or_create_sensor(reading)
            sensor_reading = models.SensorReading(
                sensor_fk=sensor.id,
                value=reading.value,
            )
            self._session.add(sensor_reading)

    def get_sensor_by_id(self, sensor_id: str) -> Optional[models.Sensor]:
        """Get sensor by its string ID."""
        return (
            self._session.query(models.Sensor)
            .filter(models.Sensor.sensor_id == sensor_id)
            .first()
        )

    def get_all_sensors(self) -> list[models.Sensor]:
        """Get all sensors."""
        return self._session.query(models.Sensor).all()


__all__ = ["SensorRepository"]
