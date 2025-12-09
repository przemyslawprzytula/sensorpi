"""Automation rule evaluation and relay control."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Dict, Iterable, List, Optional, Sequence
import logging

from sensorpi.controllers import RelayController, RelayState
from sensorpi.sensors import SensorReading
from .manual_override import ManualOverrideManager

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ThresholdCondition:
    measurement: str
    operator: str
    threshold: float

    def is_met(self, values: Sequence[float]) -> bool:
        for value in values:
            if _compare(value, self.operator, self.threshold):
                return True
        return False


@dataclass(slots=True)
class ScheduleCondition:
    start: time
    end: time

    def is_met(self, now: time) -> bool:
        if self.start <= self.end:
            return self.start <= now <= self.end
        # Overnight schedule (wrap around midnight)
        return now >= self.start or now <= self.end


@dataclass(slots=True)
class AutomationRule:
    name: str
    device_id: str
    action_on_true: RelayState
    condition_type: str
    threshold_conditions: List[ThresholdCondition]
    schedule_condition: Optional[ScheduleCondition] = None

    def evaluate(self, snapshot: "SensorSnapshot") -> Optional[RelayState]:
        if self.condition_type == "threshold":
            values = [snapshot.get_measurement(cond.measurement) for cond in self.threshold_conditions]
            for cond, measurement_values in zip(self.threshold_conditions, values):
                if not measurement_values:
                    continue
                if cond.is_met(measurement_values):
                    return self.action_on_true
            return RelayState.OFF if self.action_on_true == RelayState.ON else RelayState.ON
        if self.condition_type == "schedule" and self.schedule_condition:
            now = snapshot.now_local.time()
            if self.schedule_condition.is_met(now):
                return self.action_on_true
            return RelayState.OFF if self.action_on_true == RelayState.ON else RelayState.ON
        return None


class SensorSnapshot:
    def __init__(self, readings: Iterable[SensorReading], tz: timezone | None = None) -> None:
        self._values: Dict[str, List[float]] = {}
        for reading in readings:
            self._values.setdefault(reading.measurement, []).append(reading.value)
        self.now_local = datetime.now(tz or timezone.utc)

    def get_measurement(self, measurement: str) -> Sequence[float]:
        return self._values.get(measurement, [])


class AutomationEngine:
    def __init__(
        self,
        relay_controller: RelayController,
        rules_config: List[Dict[str, object]],
        manual_overrides: Optional[ManualOverrideManager] = None,
    ) -> None:
        self._relay_controller = relay_controller
        self._overrides = manual_overrides or ManualOverrideManager()
        self._rules: List[AutomationRule] = self._build_rules(rules_config)

    def process(self, readings: Iterable[SensorReading]) -> None:
        snapshot = SensorSnapshot(readings)
        self._overrides.cleanup()
        for rule in self._rules:
            override = self._overrides.get_override(rule.device_id)
            if override:
                continue
            desired_state = rule.evaluate(snapshot)
            if desired_state is None:
                continue
            current_state = self._relay_controller.get_state(rule.device_id)
            if desired_state != current_state:
                LOGGER.info(
                    "Automation rule '%s' switching %s -> %s",
                    rule.name,
                    rule.device_id,
                    desired_state.name,
                )
                self._relay_controller.set_state(rule.device_id, desired_state)

    def set_manual_override(
        self, device_id: str, state: RelayState, duration_minutes: int = 60
    ) -> None:
        self._overrides.set_override(device_id, state, duration_minutes)
        self._relay_controller.set_state(device_id, state)

    def clear_manual_override(self, device_id: str) -> None:
        self._overrides.clear_override(device_id)

    def _build_rules(self, rules_config: List[Dict[str, object]]) -> List[AutomationRule]:
        rules: List[AutomationRule] = []
        for entry in rules_config:
            condition_type = entry.get("condition_type", "threshold")
            action = entry.get("action", "on")
            rule = AutomationRule(
                name=entry.get("name", entry.get("device_id", "rule")),
                device_id=entry["device_id"],
                action_on_true=RelayState.ON if action == "on" else RelayState.OFF,
                condition_type=condition_type,
                threshold_conditions=self._build_threshold_conditions(entry),
                schedule_condition=self._build_schedule(entry),
            )
            rules.append(rule)
        return rules

    def _build_threshold_conditions(self, entry: Dict[str, object]) -> List[ThresholdCondition]:
        conditions = []
        for condition in entry.get("conditions", []):
            measurement = condition.get("measurement") or condition.get("sensor_type")
            if not measurement:
                continue
            conditions.append(
                ThresholdCondition(
                    measurement=measurement,
                    operator=condition.get("operator", ">"),
                    threshold=float(condition.get("threshold", 0.0)),
                )
            )
        return conditions

    def _build_schedule(self, entry: Dict[str, object]) -> Optional[ScheduleCondition]:
        schedule = entry.get("schedule")
        if not schedule:
            return None
        start = time.fromisoformat(schedule["start"])
        end = time.fromisoformat(schedule["end"])
        return ScheduleCondition(start=start, end=end)


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    if operator == "!=":
        return value != threshold
    return False
