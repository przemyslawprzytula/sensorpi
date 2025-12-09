"""Sensor aggregation and polling utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Dict, List, Sequence
import logging

from .base_sensor import BaseSensor, SensorReading

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SensorDefinition:
    module_path: str
    class_name: str
    kwargs: Dict[str, object]


class SensorManager:
    """Initializes and polls sensors based on configuration."""

    def __init__(self) -> None:
        self._sensors: List[BaseSensor] = []

    @property
    def sensors(self) -> Sequence[BaseSensor]:
        return tuple(self._sensors)

    def load_from_config(self, config: Dict[str, object]) -> None:
        """Instantiate sensor objects from configuration dictionary."""
        self._sensors.clear()
        definitions = self._expand_config(config)
        for definition in definitions:
            sensor = self._build_sensor(definition)
            try:
                sensor.initialize()
                LOGGER.info("Initialized sensor %s", sensor.sensor_id)
            except Exception as exc:  # pragma: no cover - hardware specific
                LOGGER.exception("Failed to initialize sensor %s", sensor.sensor_id)
                sensor.mark_unhealthy(exc)
            self._sensors.append(sensor)

    def poll(self) -> List[SensorReading]:
        """Read all sensors and return flattened readings."""
        readings: List[SensorReading] = []
        for sensor in self._sensors:
            try:
                sensor_readings = sensor.read()
                readings.extend(sensor_readings)
                sensor.mark_healthy()
            except Exception as exc:  # pragma: no cover - hardware specific
                LOGGER.exception("Sensor %s read failure", sensor.sensor_id)
                sensor.mark_unhealthy(exc)
        return readings

    # ------------------------------------------------------------------
    def _build_sensor(self, definition: SensorDefinition) -> BaseSensor:
        module = import_module(definition.module_path)
        sensor_cls = getattr(module, definition.class_name)
        return sensor_cls(**definition.kwargs)

    def _expand_config(self, config: Dict[str, object]) -> List[SensorDefinition]:
        definitions: List[SensorDefinition] = []
        if "mcp9808" in config:
            for idx, entry in enumerate(config["mcp9808"]):
                definitions.append(
                    SensorDefinition(
                        module_path="sensorpi.sensors.mcp9808_sensor",
                        class_name="MCP9808Sensor",
                        kwargs={
                            "sensor_id": f"mcp9808_{idx+1}",
                            "address": entry["address"],
                            "location": entry.get("location", ""),
                        },
                    )
                )
        if "tsl2591x" in config:
            entry = config["tsl2591x"]
            definitions.append(
                SensorDefinition(
                    module_path="sensorpi.sensors.tsl2591x_sensor",
                    class_name="TSL2591XSensor",
                    kwargs={
                        "sensor_id": "tsl2591x_1",
                        "address": entry["address"],
                        "location": entry.get("location", ""),
                    },
                )
            )
        if "si7021" in config:
            entry = config["si7021"]
            definitions.append(
                SensorDefinition(
                    module_path="sensorpi.sensors.si7021_sensor",
                    class_name="SI7021Sensor",
                    kwargs={
                        "sensor_id": "si7021_1",
                        "address": entry["address"],
                        "location": entry.get("location", ""),
                    },
                )
            )
        if "aht20" in config:
            entry = config["aht20"]
            definitions.append(
                SensorDefinition(
                    module_path="sensorpi.sensors.aht20_sensor",
                    class_name="AHT20Sensor",
                    kwargs={
                        "sensor_id": "aht20_1",
                        "address": entry["address"],
                        "location": entry.get("location", ""),
                    },
                )
            )
        return definitions
