from types import SimpleNamespace

from controller import AppController
from models import AirPodsState


class SignalRecorder:
    def __init__(self):
        self.count = 0

    def emit(self, *args):
        self.count += 1


def controller_double(*, detected: bool, pending_popup: bool):
    state = AirPodsState(
        model_id=0x2027,
        model_name="AirPods Pro 3",
        detected=detected,
        connected=True,
    )
    state.left.battery.percent = 80
    state.right.battery.percent = 70
    state.case.battery.percent = 60
    popup_calls = []
    double = SimpleNamespace(
        _airpods=state,
        _connected_device_name="AirPods Pro 3",
        _connection_popup_pending=pending_popup,
        airpodsChanged=SignalRecorder(),
        _handle_ear_detection=lambda *args: None,
        _update_usage_active=lambda: None,
        _handle_low_battery=lambda: None,
        _maybe_show_connection_popup=lambda: popup_calls.append(True),
        popup_calls=popup_calls,
    )
    return double


def test_ble_advertisement_gap_preserves_last_known_battery_state():
    double = controller_double(detected=True, pending_popup=False)
    original_state = double._airpods

    AppController._on_airpods_lost(double)

    assert double._airpods is original_state
    assert double._airpods.detected is False
    assert double._airpods.left.battery.percent == 80
    assert double._airpods.right.battery.percent == 70
    assert double._airpods.case.battery.percent == 60
    assert double.popup_calls == []


def test_ble_recovery_does_not_show_connection_popup_without_real_bt_transition():
    double = controller_double(detected=False, pending_popup=False)
    recovered = AirPodsState(model_id=0x2027, model_name="AirPods Pro 3", detected=True)
    recovered.connected = True

    AppController._on_airpods_state(double, recovered)
    assert double.popup_calls == []

    double._connection_popup_pending = True
    AppController._on_airpods_state(double, recovered)
    assert double.popup_calls == [True]
