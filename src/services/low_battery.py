from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from models import AirPodsState


@dataclass(slots=True)
class LowBatteryPolicy:
    threshold: int = 10
    reset_threshold: int = 20
    _latched: dict[str, bool] = field(
        default_factory=lambda: {"left": False, "right": False, "case": False}
    )

    def evaluate(self, state: AirPodsState) -> list[tuple[str, int]]:
        values = {
            "left": state.left.battery.percent,
            "right": state.right.battery.percent,
            "case": state.case.battery.percent,
        }
        triggered: list[tuple[str, int]] = []
        for name, value in values.items():
            if value is None:
                continue
            if value >= self.reset_threshold:
                self._latched[name] = False
            elif value <= self.threshold and not self._latched[name]:
                self._latched[name] = True
                triggered.append((name, value))
        return triggered

    def reset(self, devices: Iterable[str] | None = None) -> None:
        for name in devices or self._latched.keys():
            if name in self._latched:
                self._latched[name] = False
