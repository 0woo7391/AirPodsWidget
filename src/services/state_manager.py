from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import replace
from typing import Optional

from models import AirPodsState, ParsedAdvertisement, Side


class AirPodsStateManager:
    """Merge advertisements from the two randomized AirPods BLE broadcasters.

    This mirrors the conservative parts of AirPodsDesktop's state manager: model consistency,
    battery-difference checks when a randomized address changes, RSSI sanity checks, freshest
    available field selection, and a timeout when advertisements disappear.
    """

    def __init__(
        self,
        *,
        rssi_min: int = -85,
        lost_timeout: float = 10.0,
        side_lost_timeout: float = 3.0,
    ) -> None:
        self.rssi_min = rssi_min
        self.lost_timeout = lost_timeout
        self.side_lost_timeout = side_lost_timeout
        self._by_side: dict[Side, ParsedAdvertisement] = {}
        self._current: Optional[AirPodsState] = None
        self._last_seen = 0.0
        self._pending_expiry_state: Optional[AirPodsState] = None

    @property
    def current(self) -> Optional[AirPodsState]:
        self.expire_if_needed()
        return deepcopy(self._current)

    def reset(self) -> None:
        self._by_side.clear()
        self._current = None
        self._last_seen = 0.0
        self._pending_expiry_state = None

    def expire_if_needed(self, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        if self._current is not None and now - self._last_seen > self.lost_timeout:
            self.reset()
            return True
        stale = [
            side
            for side, adv in self._by_side.items()
            if now - adv.timestamp > self.side_lost_timeout
        ]
        for side in stale:
            self._by_side.pop(side, None)
        if stale:
            if self._by_side:
                # Keep the device detected when one broadcaster temporarily
                # goes quiet, but stop exposing stale in-ear information.
                self._current = self._merge()
            elif self._current is not None:
                # Preserve the last battery readings across an advertisement
                # gap, but never keep usage/auto-pause active from stale ear
                # flags when both broadcasters have expired.
                self._current.left.in_ear = False
                self._current.right.in_ear = False
            if self._current is not None:
                # Expiry is an uncertainty boundary. It must not be treated
                # as a fresh physical removal by the auto-pause feature.
                self._current.in_ear_fresh = False
            self._pending_expiry_state = deepcopy(self._current)
        return False

    def consume_expiry_state(self) -> Optional[AirPodsState]:
        state = self._pending_expiry_state
        self._pending_expiry_state = None
        return deepcopy(state)

    def update(self, adv: ParsedAdvertisement) -> Optional[AirPodsState]:
        if adv.rssi < self.rssi_min:
            return None
        if not self._is_plausible(adv):
            return None

        # A fresh advertisement supersedes a pending partial-expiry update.
        self._pending_expiry_state = None
        self._by_side[adv.side] = adv
        self._last_seen = max(self._last_seen, adv.timestamp)
        merged = self._merge()
        if self._current is not None:
            visible_candidate = replace(merged, rssi=self._current.rssi)
            if visible_candidate == self._current:
                self._current.rssi = merged.rssi
                return None
        self._current = merged
        return deepcopy(merged)

    def _is_plausible(self, adv: ParsedAdvertisement) -> bool:
        if self._current and self._current.model_id and self._current.model_id != adv.model_id:
            return False

        previous = self._by_side.get(adv.side)
        other = self._by_side.get(Side.RIGHT if adv.side is Side.LEFT else Side.LEFT)

        if previous and previous.address != adv.address:
            for new_value, old_value in (
                (adv.state.left.battery.percent, previous.state.left.battery.percent),
                (adv.state.right.battery.percent, previous.state.right.battery.percent),
                (adv.state.case.battery.percent, previous.state.case.battery.percent),
            ):
                if new_value is not None and old_value is not None and abs(new_value - old_value) > 10:
                    return False
            if abs(adv.rssi - previous.rssi) > 50:
                return False

        if other and abs(adv.rssi - other.rssi) > 50:
            return False
        return True

    def _merge(self) -> AirPodsState:
        advertisements = list(self._by_side.values())
        if not advertisements:
            raise RuntimeError("Cannot merge without advertisements")
        newest = max(advertisements, key=lambda item: item.timestamp)

        result = replace(newest.state)
        result.left = replace(newest.state.left)
        result.right = replace(newest.state.right)
        result.case = replace(newest.state.case)

        left_source = max(
            [a for a in advertisements if a.state.left.battery.percent is not None] or advertisements,
            key=lambda a: a.timestamp,
        ).state.left
        right_source = max(
            [a for a in advertisements if a.state.right.battery.percent is not None] or advertisements,
            key=lambda a: a.timestamp,
        ).state.right
        case_source = max(
            [a for a in advertisements if a.state.case.battery.percent is not None] or advertisements,
            key=lambda a: a.timestamp,
        ).state.case

        result.left = replace(left_source, battery=replace(left_source.battery))
        result.right = replace(right_source, battery=replace(right_source.battery))
        result.case = replace(case_source, battery=replace(case_source.battery))
        result.rssi = max(a.rssi for a in advertisements)
        result.detected = True
        return result
