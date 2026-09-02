import threading

import controller as controller_module
from controller import AppController
from models import AirPodsState
from PySide6.QtCore import QObject
from services.audio_output import AudioOutput
from services.bluetooth_status import BluetoothDeviceStatus, BluetoothConnectionError, reconnect_paired_audio


class FakeTimer:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False


def make_audio_controller() -> AppController:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._demo_mode = False
    controller._airpods_paired = True
    controller._airpods = AirPodsState()
    controller._audio_outputs = []
    controller._audio_known_outputs = [AudioOutput("airpods-endpoint", "AirPods Pro 3")]
    controller._audio_button_configs = [
        {"device_id": "airpods-endpoint", "name": "AirPods Pro 3", "kind": "airpods"}
    ]
    controller._audio_reconnect_timer = FakeTimer()
    controller._pending_audio_output_id = ""
    controller._pending_audio_output_attempts = 0
    controller._audio_switch_busy = False
    controller._audio_switch_device_id = ""
    controller._audio_switch_token = 0
    controller._audio_volume_available = True
    controller._audio_volume = 0
    controller._audio_volume_set_token = 0
    controller._audio_volume_set_busy = False
    controller._audio_volume_set_pending = None
    controller._audio_volume_set_thread = None
    controller._set_audio_feedback = lambda text: setattr(controller, "feedback", text)
    controller._refresh_audio_output = lambda: None
    controller._retry_pending_audio_output = lambda: None
    return controller


def test_paired_airpods_shortcut_requests_reconnect_before_endpoint_switch(monkeypatch):
    controller = make_audio_controller()
    calls = []
    controller_module.find_airpods_status = lambda: BluetoothDeviceStatus(
        "AirPods Pro 3", 0x1234, paired=True, connected=False
    )
    monkeypatch.setattr(
        controller_module,
        "reconnect_paired_audio",
        lambda status: calls.append(("reconnect", status.address)),
    )
    monkeypatch.setattr(
        controller_module,
        "set_default_output",
        lambda device_id: calls.append(("default", device_id)),
    )

    controller.selectAudioOutput("airpods-endpoint")
    controller._audio_reconnect_thread.join(timeout=1.0)

    assert calls == [("reconnect", 0x1234)]
    assert controller.feedback == "AirPods 연결 중"
    assert controller._pending_audio_output_id == "airpods-endpoint"
    # Endpoint polling starts only after the worker reports a completed
    # Bluetooth service toggle; the UI click itself must not run a poll.
    assert controller._audio_reconnect_timer.started is False


def test_reconnect_paired_audio_rejects_unpaired_devices_without_touching_windows():
    try:
        reconnect_paired_audio(
            BluetoothDeviceStatus("AirPods Pro 3", 0x1234, paired=False, connected=False)
        )
    except BluetoothConnectionError:
        return
    raise AssertionError("An unpaired device must not receive a Bluetooth reconnect request.")


def test_active_audio_shortcut_switch_runs_backend_call_in_worker(monkeypatch):
    controller = make_audio_controller()
    controller._airpods_paired = False
    observed = []
    monkeypatch.setattr(
        controller_module,
        "set_default_output",
        lambda device_id: observed.append((device_id, threading.current_thread().name)),
    )

    controller.selectAudioOutput("airpods-endpoint")
    controller._audio_switch_thread.join(timeout=1.0)

    assert observed == [("airpods-endpoint", "WindowsAudioSwitch")]


def test_volume_write_runs_backend_call_in_worker(monkeypatch):
    controller = make_audio_controller()
    observed = []
    monkeypatch.setattr(
        controller_module,
        "set_volume",
        lambda value: observed.append((value, threading.current_thread().name)),
    )

    controller.setAudioVolume(58)
    controller._audio_volume_set_thread.join(timeout=1.0)

    assert observed == [(58, "WindowsAudioVolumeWrite")]
    assert controller._audio_volume == 58


def test_audio_endpoint_refresh_backend_runs_off_the_qt_thread(monkeypatch):
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._demo_mode = False
    controller._airpods_paired = False
    controller._audio_refresh_generation = 0
    controller._audio_refresh_busy = False
    controller._audio_refresh_thread = None
    controller._audio_output_id = ""
    controller._audio_output_name = ""
    controller._audio_output_is_airpods = False
    controller._audio_output_available = False
    controller._audio_target_id = ""
    controller._audio_target_name = ""
    controller._audio_outputs = []
    controller._audio_known_outputs = []
    controller._audio_volume = -1
    controller._audio_volume_available = False
    controller._audio_devices_signature = ()
    controller._audio_button_configs = []
    controller._ensure_audio_button_configs = lambda outputs: None
    controller.audioChanged.connect(lambda: None)

    observed_threads = []
    output = AudioOutput("speaker", "Speaker")

    def record(function, result):
        def wrapped(*args, **kwargs):
            observed_threads.append((function, threading.current_thread().name))
            return result

        return wrapped

    monkeypatch.setattr(controller_module, "current_output", record("current", output))
    monkeypatch.setattr(controller_module, "active_outputs", record("active", [output]))
    monkeypatch.setattr(controller_module, "known_outputs", record("known", [output]))
    monkeypatch.setattr(controller_module, "current_volume", record("volume", 42))

    controller._refresh_audio_output()
    controller._audio_refresh_thread.join(timeout=1.0)

    assert {name for _, name in observed_threads} == {"WindowsAudioRefresh"}
