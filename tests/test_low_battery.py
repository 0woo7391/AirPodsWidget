from models import AirPodsState
from services.low_battery import LowBatteryPolicy


def make_state(left=None, right=None, case=None):
    state = AirPodsState(connected=True, detected=True)
    state.left.battery.percent = left
    state.right.battery.percent = right
    state.case.battery.percent = case
    return state


def test_alerts_at_first_available_ten_percent_step():
    policy = LowBatteryPolicy(threshold=10, reset_threshold=20)
    assert policy.evaluate(make_state(left=20)) == []
    assert policy.evaluate(make_state(left=10)) == [("left", 10)]


def test_does_not_repeat_until_recovered():
    policy = LowBatteryPolicy(threshold=10, reset_threshold=20)
    assert policy.evaluate(make_state(right=9)) == [("right", 9)]
    assert policy.evaluate(make_state(right=8)) == []
    assert policy.evaluate(make_state(right=20)) == []
    assert policy.evaluate(make_state(right=9)) == [("right", 9)]


def test_groups_multiple_new_low_devices():
    policy = LowBatteryPolicy(threshold=10, reset_threshold=20)
    assert policy.evaluate(make_state(left=9, right=8, case=7)) == [
        ("left", 9), ("right", 8), ("case", 7)
    ]


def test_custom_decile_threshold_rearms_one_step_higher():
    policy = LowBatteryPolicy(threshold=20, reset_threshold=30)
    assert policy.evaluate(make_state(left=30)) == []
    assert policy.evaluate(make_state(left=20)) == [("left", 20)]
    assert policy.evaluate(make_state(left=10)) == []
    assert policy.evaluate(make_state(left=30)) == []
    assert policy.evaluate(make_state(left=20)) == [("left", 20)]
