"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SensorType(enum.Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"


class DeviceType(enum.Enum):
    VENTILATION = "ventilation"
    LED = "led"


class TriggerSource(enum.Enum):
    AUTOMATION = "automation"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(Enum(SensorType), nullable=False)
    measurement: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    location: Mapped[str | None] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


__all__ = [
    "Base",
    "SensorReading",
    "ControlEvent",
    "SystemConfig",
    "SensorType",
    "DeviceType",
    "TriggerSource",
]
