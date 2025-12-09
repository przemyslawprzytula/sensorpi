"""Background service that polls all sensors and persists readings."""
from __future__ import annotations

import logging
import time
from typing import Optional

from sensorpi.automation import AutomationEngine
from sensorpi.config.settings import Settings
from sensorpi.controllers import RelayController
from sensorpi.database.repository import SensorRepository
from sensorpi.database.session import get_session
from sensorpi.sensors import SensorManager

LOGGER = logging.getLogger(__name__)


class DataCollectorService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        relay_controller: Optional[RelayController] = None,
        automation_engine: Optional[AutomationEngine] = None,
    ) -> None:
        self._settings = settings or Settings()
        self._sensor_manager = SensorManager()
        self._interval = int(self._settings.sensors.get("poll_interval_seconds", 60))
        self._initialized = False
        self._relay_controller = relay_controller
        self._automation = automation_engine or self._build_automation(relay_controller)

    def _build_automation(
        self, relay_controller: Optional[RelayController]
    ) -> Optional[AutomationEngine]:
        automation_cfg = self._settings.automation
        if not automation_cfg.get("enabled") or relay_controller is None:
            return None
        rules = automation_cfg.get("rules", [])
        if not rules:
            LOGGER.warning("Automation enabled but no rules are configured")
            return None
        return AutomationEngine(relay_controller, rules)

    def initialize(self) -> None:
        if self._initialized:
            return
        LOGGER.info("Initializing sensors")
        self._sensor_manager.load_from_config(self._settings.sensors)
        self._initialized = True

    def run_once(self) -> int:
        if not self._initialized:
            self.initialize()
        readings = self._sensor_manager.poll()
        if not readings:
            LOGGER.warning("No sensor readings captured during this cycle")
            return 0
        LOGGER.info("Captured %s sensor readings", len(readings))
        with get_session() as session:
            repo = SensorRepository(session)
            repo.save_readings(readings)
        if self._automation and self._relay_controller:
            self._automation.process(readings)
        return len(readings)

    def run_forever(self) -> None:  # pragma: no cover - long running loop
        LOGGER.info("Starting data collector loop with %s second interval", self._interval)
        while True:
            start = time.perf_counter()
            try:
                self.run_once()
            except Exception:  # log and continue loop
                LOGGER.exception("Sensor polling cycle failed")
            elapsed = time.perf_counter() - start
            sleep_time = max(self._interval - elapsed, 0)
            time.sleep(sleep_time)
