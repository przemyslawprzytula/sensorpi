"""Configuration utilities for the SensorPi project."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os

_DEFAULT_CONFIG: Dict[str, Any] = {
    "database": {
        "host": "localhost",
        "port": 3306,
        "database": "greenhouse",
        "username": "greenhouse_user",
        "password": "change_me",
        "ssl": False,
    },
    "sensors": {
        "poll_interval_seconds": 60,
        "mcp9808": [
            {"address": 0x18, "location": "air_high"},
            {"address": 0x19, "location": "air_mid"},
            {"address": 0x1A, "location": "air_low"},
        ],
        "tsl2591x": {"address": 0x29, "location": "canopy"},
        "si7021": {"address": 0x40, "location": "ambient"},
        "aht20": {"address": 0x38, "location": "soil"},
    },
    "relays": {
        "pins": {
            "ventilation_main": 17,
            "ventilation_aux": 18,
            "led_primary": 27,
            "led_secondary": 22,
        },
        "names": {
            "ventilation_main": "Main Ventilation Fan",
            "ventilation_aux": "Auxiliary Ventilation",
            "led_primary": "Primary Grow Lights",
            "led_secondary": "Supplemental LEDs",
        },
        "fail_safe_state": "off",
    },
    "automation": {
        "enabled": True,
        "rules": [
            {
                "name": "Baseline Temperature Control",
                "device_id": "ventilation_main",
                "condition_type": "threshold",
                "conditions": [
                    {"sensor_type": "temperature", "operator": ">", "threshold": 25.0}
                ],
                "is_active": True,
            }
        ],
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": False,
    },
}


@dataclass(slots=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl: bool = False

    @property
    def dsn(self) -> str:
        """Return a SQLAlchemy compatible DSN string."""
        ssl_args = "?ssl=true" if self.ssl else ""
        return (
            f"mysql+pymysql://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}{ssl_args}"
        )


class Settings:
    """Loads and stores project configuration values."""

    def __init__(self, config_path: Optional[Path | str] = None):
        self._config_path = Path(
            config_path or os.environ.get("SENSORPI_CONFIG", "config/settings.json")
        )
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self._config_path.exists():
            with self._config_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        # Ensure parent directory exists for future saves
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        # Persist default configuration for convenience
        with self._config_path.open("w", encoding="utf-8") as handle:
            json.dump(_DEFAULT_CONFIG, handle, indent=2)
        return _DEFAULT_CONFIG.copy()

    @property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(**self._data.get("database", {}))

    @property
    def sensors(self) -> Dict[str, Any]:
        return self._data.get("sensors", {})

    @property
    def relays(self) -> Dict[str, Any]:
        return self._data.get("relays", {})

    @property
    def automation(self) -> Dict[str, Any]:
        return self._data.get("automation", {})

    @property
    def api(self) -> Dict[str, Any]:
        return self._data.get("api", {})

    def get(self, key: str, default: Any | None = None) -> Any:
        """Retrieve dotted configuration keys, e.g., `database.host`."""
        parts = key.split(".")
        current: Any = self._data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current


__all__ = ["Settings", "DatabaseConfig"]
