"""Pydantic schemas for API request/response models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SensorTypeEnum(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"


class RelayStateEnum(str, Enum):
    ON = "on"
    OFF = "off"


# --- Sensor Schemas ---

class SensorBase(BaseModel):
    sensor_id: str
    sensor_type: SensorTypeEnum
    measurement: str
    unit: str
    location: Optional[str] = None


class SensorResponse(SensorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SensorReadingBase(BaseModel):
    value: float


class SensorReadingResponse(SensorReadingBase):
    id: int
    sensor_fk: int
    recorded_at: datetime

    class Config:
        from_attributes = True


class SensorWithLatestReading(SensorResponse):
    """Sensor with its most recent reading."""
    latest_value: Optional[float] = None
    latest_recorded_at: Optional[datetime] = None


class SensorReadingsQuery(BaseModel):
    """Query parameters for sensor readings."""
    sensor_id: Optional[str] = None
    sensor_type: Optional[SensorTypeEnum] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    timestamp: datetime
    value: float


class SensorTimeSeries(BaseModel):
    """Time series data for a single sensor."""
    sensor_id: str
    sensor_type: str
    unit: str
    location: Optional[str]
    data: List[TimeSeriesPoint]


# --- Relay Schemas ---

class RelayInfo(BaseModel):
    """Relay information and current state."""
    id: str
    name: str
    state: RelayStateEnum
    pin: Optional[int] = None


class RelaySetRequest(BaseModel):
    """Request to set relay state."""
    state: RelayStateEnum


class RelaySetResponse(BaseModel):
    """Response after setting relay state."""
    id: str
    state: RelayStateEnum
    message: str


class RelaysResponse(BaseModel):
    """All relays with their states."""
    relays: List[RelayInfo]
    dependencies: Dict[str, Any]
    nc_wiring: bool


# --- Automation Rule Schemas ---

class ConditionOperator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="


class RuleCondition(BaseModel):
    """Single condition for a rule."""
    sensor_type: SensorTypeEnum
    operator: ConditionOperator
    threshold: float


class AutomationRule(BaseModel):
    """Automation rule definition."""
    name: str
    device_id: str
    condition_type: str = "threshold"
    conditions: List[RuleCondition]
    is_active: bool = True


class AutomationConfig(BaseModel):
    """Full automation configuration."""
    enabled: bool
    rules: List[AutomationRule]


# --- WebSocket Message Schemas ---

class WSMessageType(str, Enum):
    SENSOR_UPDATE = "sensor_update"
    RELAY_UPDATE = "relay_update"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: WSMessageType
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSSensorUpdate(BaseModel):
    """WebSocket sensor update payload."""
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    location: Optional[str]
    recorded_at: datetime


class WSRelayUpdate(BaseModel):
    """WebSocket relay update payload."""
    relay_id: str
    state: RelayStateEnum
    changed_by: str = "api"


# --- System Schemas ---

class SystemStatus(BaseModel):
    """Overall system status."""
    rpi_connected: bool
    rpi_address: str
    database_connected: bool
    sensor_count: int
    reading_count: int
    automation_enabled: bool
    last_reading_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: bool
    rpi_api: bool


__all__ = [
    "SensorTypeEnum",
    "RelayStateEnum",
    "SensorBase",
    "SensorResponse",
    "SensorReadingBase",
    "SensorReadingResponse",
    "SensorWithLatestReading",
    "SensorReadingsQuery",
    "TimeSeriesPoint",
    "SensorTimeSeries",
    "RelayInfo",
    "RelaySetRequest",
    "RelaySetResponse",
    "RelaysResponse",
    "ConditionOperator",
    "RuleCondition",
    "AutomationRule",
    "AutomationConfig",
    "WSMessageType",
    "WSMessage",
    "WSSensorUpdate",
    "WSRelayUpdate",
    "SystemStatus",
    "HealthResponse",
]
