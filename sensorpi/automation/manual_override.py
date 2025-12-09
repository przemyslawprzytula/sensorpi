"""Manual override utilities for actuators."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sensorpi.controllers import RelayState


@dataclass(slots=True)
class ManualOverride:
    device_id: str
    state: RelayState
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class ManualOverrideManager:
    def __init__(self) -> None:
        self._overrides: Dict[str, ManualOverride] = {}

    def set_override(
        self, device_id: str, state: RelayState, duration_minutes: int = 60
    ) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self._overrides[device_id] = ManualOverride(device_id, state, expires_at)

    def clear_override(self, device_id: str) -> None:
        self._overrides.pop(device_id, None)

    def get_override(self, device_id: str) -> Optional[ManualOverride]:
        override = self._overrides.get(device_id)
        if override and override.is_expired:
            self._overrides.pop(device_id, None)
            return None
        return override

    def cleanup(self) -> None:
        expired = [device_id for device_id, entry in self._overrides.items() if entry.is_expired]
        for device_id in expired:
            self._overrides.pop(device_id, None)

    def active_overrides(self) -> Dict[str, ManualOverride]:
        self.cleanup()
        return dict(self._overrides)
