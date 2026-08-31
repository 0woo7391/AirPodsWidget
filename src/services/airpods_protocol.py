from __future__ import annotations

import time
from typing import Optional

from models import (
    AirPodsState,
    BatteryState,
    CaseState,
    MODEL_NAMES,
    ParsedAdvertisement,
    PodState,
    Side,
)

APPLE_COMPANY_ID = 0x004C
PROXIMITY_PAIRING_PACKET = 0x07
EXPECTED_PACKET_SIZE = 27
EXPECTED_REMAINING_LENGTH = 25
AIRPODS_PRO_3_MODEL_ID = 0x2027


def _battery_percent(raw: int) -> Optional[int]:
    """Continuity battery values are deciles (0..10); other values mean unavailable."""
    if 0 <= raw <= 10:
        return raw * 10
    return None


def parse_airpods_manufacturer_data(
    data: bytes,
    *,
    address: str = "",
    rssi: int = -127,
    timestamp: Optional[float] = None,
) -> Optional[ParsedAdvertisement]:
    """Parse Apple's 27-byte AirPods Continuity advertisement.

    ``data`` must be the value associated with Apple company ID 0x004C. Bleak already strips
    the two-byte company identifier, so the first byte here is the Continuity packet type.
    """
    if len(data) != EXPECTED_PACKET_SIZE:
        return None
    if data[0] != PROXIMITY_PAIRING_PACKET or data[1] != EXPECTED_REMAINING_LENGTH:
        return None

    model_id = int.from_bytes(data[3:5], byteorder="little", signed=False)
    if model_id not in MODEL_NAMES:
        return None

    flags = data[5]
    current_in_ear = bool(flags & 0b0000_0010)
    both_in_case = bool(flags & 0b0000_0100)
    another_in_ear = bool(flags & 0b0000_1000)
    broadcast_from_left = bool(flags & 0b0010_0000)
    side = Side.LEFT if broadcast_from_left else Side.RIGHT

    battery_pair = data[6]
    current_raw = battery_pair & 0x0F
    another_raw = (battery_pair >> 4) & 0x0F

    case_and_charging = data[7]
    case_raw = case_and_charging & 0x0F
    current_charging = bool(case_and_charging & 0x10)
    another_charging = bool(case_and_charging & 0x20)
    case_charging = bool(case_and_charging & 0x40)

    lid_flags = data[8]
    lid_closed = bool(lid_flags & 0x08)

    if side is Side.LEFT:
        left_raw, right_raw = current_raw, another_raw
        left_charging, right_charging = current_charging, another_charging
        left_in_ear, right_in_ear = current_in_ear, another_in_ear
    else:
        left_raw, right_raw = another_raw, current_raw
        left_charging, right_charging = another_charging, current_charging
        left_in_ear, right_in_ear = another_in_ear, current_in_ear

    # AirPods may set an in-ear bit while a pod is charging. Match AirPodsDesktop's filter.
    left_in_ear = left_in_ear and not left_charging
    right_in_ear = right_in_ear and not right_charging

    state = AirPodsState(
        model_id=model_id,
        model_name=MODEL_NAMES[model_id],
        left=PodState(BatteryState(_battery_percent(left_raw), left_charging), left_in_ear),
        right=PodState(BatteryState(_battery_percent(right_raw), right_charging), right_in_ear),
        case=CaseState(
            BatteryState(_battery_percent(case_raw), case_charging),
            both_pods_in_case=both_in_case,
            lid_open=not lid_closed,
        ),
        rssi=rssi,
        detected=True,
        device_name=MODEL_NAMES[model_id],
    )
    return ParsedAdvertisement(
        address=address,
        timestamp=time.monotonic() if timestamp is None else timestamp,
        rssi=rssi,
        model_id=model_id,
        side=side,
        state=state,
    )
