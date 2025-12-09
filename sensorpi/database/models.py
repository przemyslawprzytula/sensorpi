"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime, timezone
import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SensorType(str, enum.Enum):
    """Sensor measurement type - values match database enum."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"

    def __str__(self) -> str:
        return self.value


class DeviceType(enum.Enum):
    VENTILATION = "ventilation"
    LED = "led"


class TriggerSource(enum.Enum):
    AUTOMATION = "automation"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class Sensor(Base):
    """Sensor metadata - static information about each sensor."""
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(SensorType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    measurement: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    location: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="CURRENT_TIMESTAMP"
    )

    # Relationship to readings
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    """Sensor readings - lean table with just value and timestamp."""
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("ix_sensor_readings_sensor_recorded", "sensor_fk", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_fk: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="CURRENT_TIMESTAMP"
    )

    # Relationship to sensor
    sensor: Mapped["Sensor"] = relationship(back_populates="readings")


class ControlEvent(Base):
    __tablename__ = "control_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    trigger_source: Mapped[TriggerSource] = mapped_column(Enum(TriggerSource), nullable=False)
    trigger_value: Mapped[str | None] = mapped_column(String(128))


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


__all__ = [
    "Base",
    "Sensor",
    "SensorReading",
    "ControlEvent",
    "SystemConfig",
    "SensorType",
    "DeviceType",
    "TriggerSource",
]
