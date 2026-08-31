from services.airpods_protocol import parse_airpods_manufacturer_data


def packet(*, model_id=0x2027, left_broadcast=True, left=8, right=7, case=6,
           left_in_ear=True, right_in_ear=True, left_charging=False,
           right_charging=False, case_charging=False, lid_open=False):
    data = bytearray(27)
    data[0] = 0x07
    data[1] = 25
    data[2] = 1
    data[3:5] = model_id.to_bytes(2, "little")

    flags = 0
    current_in_ear = left_in_ear if left_broadcast else right_in_ear
    another_in_ear = right_in_ear if left_broadcast else left_in_ear
    if current_in_ear:
        flags |= 0x02
    if another_in_ear:
        flags |= 0x08
    if left_broadcast:
        flags |= 0x20
    data[5] = flags

    current = left if left_broadcast else right
    another = right if left_broadcast else left
    data[6] = (another << 4) | current

    current_charging = left_charging if left_broadcast else right_charging
    another_charging = right_charging if left_broadcast else left_charging
    charge = case
    if current_charging:
        charge |= 0x10
    if another_charging:
        charge |= 0x20
    if case_charging:
        charge |= 0x40
    data[7] = charge
    data[8] = 0x00 if lid_open else 0x08
    return bytes(data)


def test_parse_pro3_left_broadcast():
    parsed = parse_airpods_manufacturer_data(packet(), address="AA", rssi=-48, timestamp=12.0)
    assert parsed is not None
    assert parsed.model_id == 0x2027
    assert parsed.state.model_name == "AirPods Pro 3"
    assert parsed.state.left.battery.percent == 80
    assert parsed.state.right.battery.percent == 70
    assert parsed.state.case.battery.percent == 60
    assert parsed.state.left.in_ear is True
    assert parsed.state.right.in_ear is True
    assert parsed.state.case.lid_open is False


def test_right_broadcast_maps_current_to_right():
    parsed = parse_airpods_manufacturer_data(
        packet(left_broadcast=False, left=4, right=9), timestamp=1.0
    )
    assert parsed is not None
    assert parsed.state.left.battery.percent == 40
    assert parsed.state.right.battery.percent == 90


def test_charging_pod_is_not_treated_as_in_ear():
    parsed = parse_airpods_manufacturer_data(packet(left_charging=True), timestamp=1.0)
    assert parsed is not None
    assert parsed.state.left.battery.charging is True
    assert parsed.state.left.in_ear is False


def test_rejects_wrong_length_and_unknown_model():
    assert parse_airpods_manufacturer_data(b"\x07" * 26) is None
    assert parse_airpods_manufacturer_data(packet(model_id=0xFFFF)) is None
