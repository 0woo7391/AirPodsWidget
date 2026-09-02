import time

from services.airpods_protocol import parse_airpods_manufacturer_data
from services.state_manager import AirPodsStateManager
from test_airpods_protocol import packet


def test_merges_and_expires_state():
    manager = AirPodsStateManager(rssi_min=-90, lost_timeout=10)
    now = time.monotonic()
    left = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=8, right=7), address="A", rssi=-45, timestamp=now
    )
    right = parse_airpods_manufacturer_data(
        packet(left_broadcast=False, left=8, right=7), address="B", rssi=-46, timestamp=now + 1
    )
    assert left and right
    assert manager.update(left) is not None
    manager.update(right)
    merged = manager.current
    assert merged is not None
    assert merged.left.battery.percent == 80
    assert merged.right.battery.percent == 70
    assert manager.expire_if_needed(now=now + 12) is True
    assert manager.current is None


def test_rejects_implausible_address_change():
    manager = AirPodsStateManager(rssi_min=-90)
    now = time.monotonic()
    first = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=8), address="A", rssi=-45, timestamp=now
    )
    jump = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=3), address="CHANGED", rssi=-45, timestamp=now + 1
    )
    assert first and jump
    assert manager.update(first) is not None
    assert manager.update(jump) is None
    assert manager.current is not None
    assert manager.current.left.battery.percent == 80


def test_expired_side_drops_stale_in_ear_state_without_losing_device():
    manager = AirPodsStateManager(rssi_min=-90, lost_timeout=10, side_lost_timeout=3)
    now = time.monotonic()
    left = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left_in_ear=True, right_in_ear=True),
        address="A",
        rssi=-45,
        timestamp=now,
    )
    right = parse_airpods_manufacturer_data(
        packet(left_broadcast=False, left_in_ear=False, right_in_ear=True),
        address="B",
        rssi=-46,
        timestamp=now + 4,
    )
    assert left and right
    manager.update(left)
    manager.update(right)

    assert manager.expire_if_needed(now=now + 5) is False
    refreshed = manager.consume_expiry_state()
    assert refreshed is not None
    assert refreshed.left.in_ear is False
    assert refreshed.right.in_ear is True
    assert refreshed.in_ear_fresh is False
    assert manager.current is not None


def test_all_expired_sides_clear_stale_in_ear_but_keep_battery():
    manager = AirPodsStateManager(rssi_min=-90, lost_timeout=10, side_lost_timeout=3)
    now = time.monotonic()
    advertisement = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=8, right=7, left_in_ear=True, right_in_ear=True),
        address="A",
        rssi=-45,
        timestamp=now,
    )
    assert advertisement
    manager.update(advertisement)

    assert manager.expire_if_needed(now=now + 4) is False
    refreshed = manager.consume_expiry_state()
    assert refreshed is not None
    assert refreshed.left.in_ear is False
    assert refreshed.right.in_ear is False
    assert refreshed.in_ear_fresh is False
    assert refreshed.left.battery.percent == 80
    assert refreshed.right.battery.percent == 70


def test_rssi_only_change_does_not_emit_visible_state_update():
    manager = AirPodsStateManager(rssi_min=-90)
    now = time.monotonic()
    first = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=8, right=7), address="A", rssi=-45, timestamp=now
    )
    second = parse_airpods_manufacturer_data(
        packet(left_broadcast=True, left=8, right=7), address="A", rssi=-52, timestamp=now + 1
    )
    assert first and second
    emitted = manager.update(first)
    assert emitted is not None
    emitted.connected = True  # a UI consumer must not be able to mutate the manager cache
    assert manager.update(second) is None
    assert manager.current is not None
    assert manager.current.rssi == -52
