"""Microphone mute, per-app volume and the output level meter (Windows Core Audio), for the mic and volume modules.

Reuses the raw COM helpers of services/audio_output.py. A worker thread reads the
default microphone and the playback sessions once a second and runs commands;
results reach the GUI thread through a queued signal.
"""
from __future__ import annotations

import ctypes
import os
import queue
import threading
import time
from ctypes import wintypes

from PySide6.QtCore import Property, QObject, Signal, Slot

from services import audio_output as ao

E_DATA_FLOW_CAPTURE = 1
AUDIO_SESSION_STATE_EXPIRED = 2
IID_SESSION_MANAGER2 = "{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}"
IID_SESSION_CONTROL2 = "{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}"
IID_SIMPLE_VOLUME = "{87CE5498-68D6-44E5-9215-6DA47EF883D8}"
IID_AUDIO_METER = "{C02216F6-8C67-4B5B-9D00-D008E73E0064}"
HRESULT = ao.HRESULT
REFRESH_SECONDS = 1.0


def _default_device(flow: int, role: int) -> ctypes.c_void_p:
    enumerator = ao._co_create(ao.CLSID_MM_DEVICE_ENUMERATOR, ao.IID_MM_DEVICE_ENUMERATOR)
    device = ctypes.c_void_p()
    try:
        ao._check_hresult(ao._vtable_call(enumerator, 4, HRESULT,
                                          [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                                          flow, role, ctypes.byref(device)), "GetDefaultAudioEndpoint")
        return device
    finally:
        ao._release(enumerator)


def _activate(device: ctypes.c_void_p, iid: str) -> ctypes.c_void_p:
    result = ctypes.c_void_p()
    ao._check_hresult(ao._vtable_call(device, 3, HRESULT,
                                      [ctypes.POINTER(ao.GUID), wintypes.DWORD, ctypes.c_void_p,
                                       ctypes.POINTER(ctypes.c_void_p)],
                                      ctypes.byref(ao._guid(iid)), ao.CLSCTX_INPROC_SERVER, None,
                                      ctypes.byref(result)), "Activate")
    return result


def _query(pointer: ctypes.c_void_p, iid: str) -> ctypes.c_void_p:
    result = ctypes.c_void_p()
    ao._check_hresult(ao._vtable_call(pointer, 0, HRESULT, [ctypes.POINTER(ao.GUID), ctypes.POINTER(ctypes.c_void_p)],
                                      ctypes.byref(ao._guid(iid)), ctypes.byref(result)), "QueryInterface")
    return result


# ---- microphone -----------------------------------------------------------------

def read_mic() -> dict:
    try:
        device = _default_device(E_DATA_FLOW_CAPTURE, ao.E_ROLE_CONSOLE)
    except ao.AudioOutputError:
        return dict(available=False, name="", muted=False)
    endpoint = None
    try:
        name = ao._friendly_name(device)
        endpoint = _activate(device, ao.IID_AUDIO_ENDPOINT_VOLUME)
        muted = ctypes.c_int()
        ao._check_hresult(ao._vtable_call(endpoint, 15, HRESULT, [ctypes.POINTER(ctypes.c_int)],
                                          ctypes.byref(muted)), "GetMute")
        return dict(available=True, name=name, muted=bool(muted.value))
    finally:
        ao._release(endpoint)
        ao._release(device)


def set_mic_mute(value: bool) -> None:
    device = _default_device(E_DATA_FLOW_CAPTURE, ao.E_ROLE_CONSOLE)
    endpoint = None
    try:
        endpoint = _activate(device, ao.IID_AUDIO_ENDPOINT_VOLUME)
        ao._check_hresult(ao._vtable_call(endpoint, 14, HRESULT, [ctypes.c_int, ctypes.c_void_p],
                                          int(value), None), "SetMute")
    finally:
        ao._release(endpoint)
        ao._release(device)


# ---- per-app sessions ---------------------------------------------------------------

def process_path(pid: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


_descriptions: dict[str, str] = {}


def app_name(path: str) -> str:
    """The program's own name (its version info's FileDescription), else the file name."""
    if path in _descriptions:
        return _descriptions[path]
    name = os.path.splitext(os.path.basename(path))[0] or "앱"
    try:
        version = ctypes.WinDLL("version")
        size = version.GetFileVersionInfoSizeW(path, None)
        if size:
            data = ctypes.create_string_buffer(size)
            if version.GetFileVersionInfoW(path, 0, size, data):
                pointer, length = ctypes.c_void_p(), wintypes.UINT()
                if version.VerQueryValueW(data, "\\VarFileInfo\\Translation", ctypes.byref(pointer), ctypes.byref(length)) and length.value:
                    lang, codepage = ctypes.cast(pointer, ctypes.POINTER(wintypes.WORD * 2)).contents
                    key = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription"
                    if version.VerQueryValueW(data, key, ctypes.byref(pointer), ctypes.byref(length)) and length.value:
                        described = ctypes.wstring_at(pointer, length.value).strip("\x00 ")
                        name = described or name
    except OSError:
        pass
    _descriptions[path] = name
    return name


def _each_session(action):
    """Call action(path, pid, state, simple_volume) for every playback session of the default output."""
    device = _default_device(ao.E_DATA_FLOW_RENDER, ao.E_ROLE_MULTIMEDIA)
    manager = enumerator = None
    try:
        manager = _activate(device, IID_SESSION_MANAGER2)
        enumerator = ctypes.c_void_p()
        ao._check_hresult(ao._vtable_call(manager, 5, HRESULT, [ctypes.POINTER(ctypes.c_void_p)],
                                          ctypes.byref(enumerator)), "GetSessionEnumerator")
        count = ctypes.c_int()
        ao._check_hresult(ao._vtable_call(enumerator, 3, HRESULT, [ctypes.POINTER(ctypes.c_int)],
                                          ctypes.byref(count)), "GetCount")
        for index in range(count.value):
            control = control2 = simple = None
            try:
                control = ctypes.c_void_p()
                ao._check_hresult(ao._vtable_call(enumerator, 4, HRESULT, [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)],
                                                  index, ctypes.byref(control)), "GetSession")
                control2 = _query(control, IID_SESSION_CONTROL2)
                if ao._vtable_call(control2, 15, HRESULT, []) == 0:   # IsSystemSoundsSession: S_OK
                    continue
                pid, state = wintypes.DWORD(), ctypes.c_int()
                ao._vtable_call(control2, 14, HRESULT, [ctypes.POINTER(wintypes.DWORD)], ctypes.byref(pid))
                ao._vtable_call(control2, 3, HRESULT, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(state))
                path = process_path(pid.value) if pid.value else ""
                if not path or state.value == AUDIO_SESSION_STATE_EXPIRED:
                    continue
                simple = _query(control, IID_SIMPLE_VOLUME)
                action(path, pid.value, state.value, simple)
            except ao.AudioOutputError:
                continue
            finally:
                ao._release(simple)
                ao._release(control2)
                ao._release(control)
    finally:
        ao._release(enumerator)
        ao._release(manager)
        ao._release(device)


def read_sessions() -> list[dict]:
    """One entry per program (a browser has many sessions), playing ones first."""
    apps: dict[str, dict] = {}

    def collect(path, pid, state, simple):
        volume, muted = ctypes.c_float(), ctypes.c_int()
        ao._vtable_call(simple, 4, HRESULT, [ctypes.POINTER(ctypes.c_float)], ctypes.byref(volume))
        ao._vtable_call(simple, 6, HRESULT, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(muted))
        key = path.lower()
        entry = apps.setdefault(key, dict(key=key, path=path, name=app_name(path), active=False,
                                          volume=round(volume.value * 100), muted=bool(muted.value)))
        entry["active"] = entry["active"] or state == 1

    _each_session(collect)
    return sorted(apps.values(), key=lambda a: (not a["active"], a["name"].lower()))


def set_session(key: str, volume: int | None = None, muted: bool | None = None) -> None:
    def apply(path, pid, state, simple):
        if path.lower() != key:
            return
        if volume is not None:
            ao._vtable_call(simple, 3, HRESULT, [ctypes.c_float, ctypes.c_void_p], max(0.0, min(1.0, volume / 100)), None)
        if muted is not None:
            ao._vtable_call(simple, 5, HRESULT, [ctypes.c_int, ctypes.c_void_p], int(muted), None)

    _each_session(apply)


# ---- backend ----------------------------------------------------------------------------

class AudioExtras(QObject):
    micChanged = Signal()
    sessionsChanged = Signal()
    micToggled = Signal(bool)         # the mute state changed (from anywhere), for the island
    _read = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mic = dict(available=False, name="", muted=False)
        self._sessions: list[dict] = []
        self._commands: queue.SimpleQueue = queue.SimpleQueue()
        self._stop = threading.Event()
        self._thread = None
        self._first = True
        self._read.connect(self._apply)

    @Property("QVariantMap", notify=micChanged)
    def mic(self):
        return dict(self._mic)

    @Property("QVariantList", notify=sessionsChanged)
    def sessions(self):
        return list(self._sessions)

    @Slot()
    def toggleMic(self):
        self._commands.put(("mic", not self._mic.get("muted")))

    @Slot(str, int)
    def setAppVolume(self, key, value):
        self._commands.put(("volume", key, value))

    @Slot(str)
    def toggleAppMute(self, key):
        entry = next((s for s in self._sessions if s["key"] == key), None)
        if entry:
            self._commands.put(("mute", key, not entry["muted"]))

    # Windows remembers each app's level between runs; these put it back to 100 % and unmuted.
    @Slot(str)
    def resetApp(self, key):
        self._commands.put(("reset", key))

    @Slot()
    def resetAllApps(self):
        for entry in self._sessions:
            self._commands.put(("reset", entry["key"]))

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="AudioExtras", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        self._commands.put(None)

    def _run(self):
        def work():
            while not self._stop.is_set():
                try:
                    while True:
                        command = self._commands.get(timeout=REFRESH_SECONDS)
                        if command is None:
                            return
                        if command[0] == "mic":
                            set_mic_mute(command[1])
                        elif command[0] == "volume":
                            set_session(command[1], volume=command[2])
                        elif command[0] == "mute":
                            set_session(command[1], muted=command[2])
                        elif command[0] == "reset":
                            set_session(command[1], volume=100, muted=False)
                        if self._commands.empty():
                            break
                except queue.Empty:
                    pass
                except Exception:
                    pass   # a device vanished mid-command; the next read shows the truth
                try:
                    self._read.emit((read_mic(), read_sessions()))
                except Exception:
                    self._read.emit((dict(available=False, name="", muted=False), []))
        ao._with_com(work)

    @Slot(object)
    def _apply(self, result):
        mic, sessions = result
        if mic != self._mic:
            toggled = mic.get("available") and self._mic.get("available") and mic["muted"] != self._mic["muted"]
            self._mic = mic
            self.micChanged.emit()
            if toggled and not self._first:
                self.micToggled.emit(mic["muted"])
        if sessions != self._sessions:
            self._sessions = sessions
            self.sessionsChanged.emit()
        self._first = False


class AudioMeter(QObject):
    """The default output's peak level, 30 times a second, for the music visualizer and the volume card."""
    levelChanged = Signal()
    _value = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._stop = threading.Event()
        self._thread = None
        self._value.connect(self._apply)

    @Property(float, notify=levelChanged)
    def level(self):
        return self._level

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="AudioMeter", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        def work():
            device = meter = None
            opened = 0.0
            while not self._stop.wait(1 / 30):
                try:
                    # Re-open now and then: the default output can change (AirPods connect).
                    if meter is None or time.monotonic() - opened > 5:
                        ao._release(meter)
                        ao._release(device)
                        device = _default_device(ao.E_DATA_FLOW_RENDER, ao.E_ROLE_MULTIMEDIA)
                        meter = _activate(device, IID_AUDIO_METER)
                        opened = time.monotonic()
                    peak = ctypes.c_float()
                    ao._check_hresult(ao._vtable_call(meter, 3, HRESULT, [ctypes.POINTER(ctypes.c_float)],
                                                      ctypes.byref(peak)), "GetPeakValue")
                    self._value.emit(float(peak.value))
                except Exception:
                    ao._release(meter)
                    ao._release(device)
                    device = meter = None
                    self._value.emit(0.0)
            ao._release(meter)
            ao._release(device)
        ao._with_com(work)

    @Slot(float)
    def _apply(self, value):
        if abs(value - self._level) > 0.002:
            self._level = value
            self.levelChanged.emit()
