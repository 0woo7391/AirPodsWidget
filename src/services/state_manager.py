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
        self.last_update_accepted = False
        self._pending_expiry_state: Optional[AirPodsState] = None
        self._pending_flags: dict[str, tuple[tuple[bool, ...], Side, float]] = {}

    @property
    def current(self) -> Optional[AirPodsState]:
        self.expire_if_needed()
        return deepcopy(self._current)

    def reset(self) -> None:
        self.last_update_accepted = False
        self._by_side.clear()
        self._current = None
        self._last_seen = 0.0
        self._pending_expiry_state = None
        self._pending_flags.clear()

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
            self._pending_flags.clear()
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
        self.last_update_accepted = False
        if adv.rssi < self.rssi_min:
            return None
        if not self._is_plausible(adv):
            return None
        previous = self._by_side.get(adv.side)
        if previous and adv.timestamp <= previous.timestamp:
            return None

        # An accepted unchanged packet can return None too; freshness needs both facts.
        self.last_update_accepted = True
        # A fresh advertisement supersedes a pending partial-expiry update.
        self._pending_expiry_state = None
        self._by_side[adv.side] = adv
        self._last_seen = max(self._last_seen, adv.timestamp)
        merged = self._merge(adv)
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

    def _merge(self, incoming: Optional[ParsedAdvertisement] = None) -> AirPodsState:
        advertisements = list(self._by_side.values())
        if not advertisements:
            raise RuntimeError("Cannot merge without advertisements")
        newest = max(advertisements, key=lambda item: item.timestamp)

        result = replace(newest.state)
        result.left = replace(newest.state.left)
        result.right = replace(newest.state.right)
        result.case = replace(newest.state.case)

        fresh = [a for a in advertisements if newest.timestamp - a.timestamp <= self.side_lost_timeout]
        for name, preferred in (("left", Side.LEFT), ("right", Side.RIGHT), ("case", Side.LEFT)):
            # Prefer a pod's own report; keep one case source while it is fresh.
            source = next((a for a in fresh if a.side == preferred), newest)
            pod = deepcopy(getattr(source.state, name))
            if pod.battery.percent is None:
                valid = [a for a in fresh if getattr(a.state, name).battery.percent is not None]
                if valid:
                    pod.battery.percent = getattr(max(valid, key=lambda a: a.timestamp).state, name).battery.percent
                elif self._current:
                    pod.battery.percent = getattr(self._current, name).battery.percent
            flags = (pod.battery.charging,) if name == "case" else (pod.battery.charging, pod.in_ear)
            if incoming is not None and self._current is not None:
                old = getattr(self._current, name)
                old_flags = (old.battery.charging,) if name == "case" else (old.battery.charging, old.in_ear)
                if flags == old_flags:
                    self._pending_flags.pop(name, None)
                else:
                    pending = self._pending_flags.get(name)
                    confirmed = (source is incoming and pending is not None
                                 and pending[:2] == (flags, source.side)
                                 and 0 < source.timestamp - pending[2] <= self.side_lost_timeout)
                    if confirmed:
                        self._pending_flags.pop(name, None)
                    else:
                        if source is incoming:
                            self._pending_flags[name] = (flags, source.side, source.timestamp)
                        pod.battery.charging = old.battery.charging
                        if name != "case":
                            if pod.in_ear != old.in_ear:
                                result.in_ear_fresh = False
                            pod.in_ear = old.in_ear
            setattr(result, name, pod)
        result.rssi = max(a.rssi for a in advertisements)
        result.detected = True
        return result
