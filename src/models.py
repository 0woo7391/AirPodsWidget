from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Side(str, Enum):
    LEFT = "left"
    RIGHT = "right"


MODEL_NAMES: dict[int, str] = {
    0x2002: "AirPods (1st generation)",
    0x200F: "AirPods (2nd generation)",
    0x2013: "AirPods (3rd generation)",
    0x2019: "AirPods 4",
    0x201B: "AirPods 4 with ANC",
    0x200E: "AirPods Pro",
    0x2014: "AirPods Pro (2nd generation)",
    0x2024: "AirPods Pro 2 (USB-C)",
    0x2027: "AirPods Pro 3",
    0x200A: "AirPods Max",
    0x2012: "Beats Fit Pro",
}


@dataclass(slots=True)
class BatteryState:
    percent: Optional[int] = None
    charging: bool = False

    @property
    def available(self) -> bool:
        return self.percent is not None


@dataclass(slots=True)
class PodState:
    battery: BatteryState = field(default_factory=BatteryState)
    in_ear: bool = False


@dataclass(slots=True)
class CaseState:
    battery: BatteryState = field(default_factory=BatteryState)
    both_pods_in_case: bool = False
    lid_open: bool = False


@dataclass(slots=True)
class AirPodsState:
    model_id: int = 0
    model_name: str = "AirPods"
    left: PodState = field(default_factory=PodState)
    right: PodState = field(default_factory=PodState)
    case: CaseState = field(default_factory=CaseState)
    rssi: int = -127
    detected: bool = False
    connected: bool = False
    device_name: str = "AirPods Pro 3"

    @property
    def any_in_ear(self) -> bool:
        return self.left.in_ear or self.right.in_ear

    @property
    def both_in_ear(self) -> bool:
        return self.left.in_ear and self.right.in_ear


@dataclass(slots=True)
class ParsedAdvertisement:
    address: str
    timestamp: float
    rssi: int
    model_id: int
    side: Side
    state: AirPodsState


@dataclass(slots=True)
class MediaState:
    available: bool = False
    title: str = ""
    artist: str = ""
    source_app: str = ""
    playing: bool = False
    can_previous: bool = False
    can_next: bool = False
    can_play_pause: bool = False
    position_seconds: float = 0.0
    duration_seconds: float = 0.0
    seekable: bool = False
