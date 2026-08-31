from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Iterable


HRESULT = ctypes.c_long
CLSCTX_INPROC_SERVER = 0x1
DEVICE_STATE_ACTIVE = 0x1
DEVICE_STATEMASK_ALL = 0xF
E_DATA_FLOW_RENDER = 0
E_ROLE_CONSOLE = 0
E_ROLE_MULTIMEDIA = 1
E_ROLE_COMMUNICATIONS = 2
STGM_READ = 0
VT_LPWSTR = 31

CLSID_MM_DEVICE_ENUMERATOR = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
IID_MM_DEVICE_ENUMERATOR = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
IID_AUDIO_ENDPOINT_VOLUME = "{5CDF2C82-841E-4546-9722-0CF74078229A}"
CLSID_POLICY_CONFIG_CLIENT = "{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}"
IID_POLICY_CONFIG = "{F8679F50-850A-41CF-9C72-430F290290C8}"

PKEY_DEVICE_FRIENDLY_NAME = (
    "{A45C254E-DF1C-4EFD-8020-67D146A850E0}",
    14,
)


class AudioOutputError(RuntimeError):
    """Raised when Windows cannot enumerate or change an audio endpoint."""


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", wintypes.USHORT),
        ("wReserved1", wintypes.USHORT),
        ("wReserved2", wintypes.USHORT),
        ("wReserved3", wintypes.USHORT),
        ("value", ctypes.c_void_p),
    ]


@dataclass(frozen=True, slots=True)
class AudioOutput:
    device_id: str
    name: str

    @property
    def is_airpods(self) -> bool:
        return "airpods" in self.name.casefold()

    @property
    def kind(self) -> str:
        name = self.name.casefold()
        if self.is_airpods:
            return "airpods"
        if any(token in name for token in ("headphone", "headset", "earphone", "헤드폰", "헤드셋")):
            return "headphones"
        return "speaker"


def _guid(value: str) -> GUID:
    result = GUID()
    ole32 = ctypes.windll.ole32
    ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
    ole32.CLSIDFromString.restype = HRESULT
    if ole32.CLSIDFromString(value, ctypes.byref(result)) != 0:
        raise AudioOutputError(f"Invalid GUID: {value}")
    return result


def _check_hresult(value: int, operation: str) -> None:
    if value < 0:
        raise AudioOutputError(f"{operation} failed with HRESULT 0x{value & 0xFFFFFFFF:08X}")


def _vtable_call(pointer: ctypes.c_void_p, index: int, restype, argtypes, *args):
    if not pointer:
        raise AudioOutputError("Audio COM interface is unavailable")
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    function = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(table[index])
    return function(pointer, *args)


def _release(pointer: ctypes.c_void_p | None) -> None:
    if pointer:
        try:
            _vtable_call(pointer, 2, HRESULT, [])
        except Exception:
            pass


def _co_create(clsid: str, iid: str) -> ctypes.c_void_p:
    ole32 = ctypes.windll.ole32
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = HRESULT
    result = ctypes.c_void_p()
    _check_hresult(
        ole32.CoCreateInstance(
            ctypes.byref(_guid(clsid)),
            None,
            CLSCTX_INPROC_SERVER,
            ctypes.byref(_guid(iid)),
            ctypes.byref(result),
        ),
        "CoCreateInstance",
    )
    return result


def _friendly_name(device: ctypes.c_void_p) -> str:
    store = ctypes.c_void_p()
    key_guid, key_pid = PKEY_DEVICE_FRIENDLY_NAME
    key = PROPERTYKEY(fmtid=_guid(key_guid), pid=key_pid)
    try:
        _check_hresult(
            _vtable_call(
                device,
                4,
                HRESULT,
                [wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                STGM_READ,
                ctypes.byref(store),
            ),
            "OpenPropertyStore",
        )
        value = PROPVARIANT()
        _check_hresult(
            _vtable_call(
                store,
                5,
                HRESULT,
                [ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT)],
                ctypes.byref(key),
                ctypes.byref(value),
            ),
            "GetValue",
        )
        if value.vt != VT_LPWSTR or not value.value:
            return "오디오 출력"
        return ctypes.wstring_at(value.value)
    finally:
        if store:
            _release(store)


def _device_id(device: ctypes.c_void_p) -> str:
    raw_id = ctypes.c_wchar_p()
    _check_hresult(
        _vtable_call(
            device,
            5,
            HRESULT,
            [ctypes.POINTER(ctypes.c_wchar_p)],
            ctypes.byref(raw_id),
        ),
        "GetId",
    )
    try:
        return raw_id.value or ""
    finally:
        if raw_id:
            ctypes.windll.ole32.CoTaskMemFree(raw_id)


def _with_com(operation):
    ole32 = ctypes.windll.ole32
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = HRESULT
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    result = ole32.CoInitializeEx(None, 0x2)
    _check_hresult(result if result not in (1, 0) else 0, "CoInitializeEx")
    try:
        return operation()
    finally:
        ole32.CoUninitialize()


def _enumerate_outputs(state_mask: int = DEVICE_STATE_ACTIVE) -> list[AudioOutput]:
    enumerator = _co_create(CLSID_MM_DEVICE_ENUMERATOR, IID_MM_DEVICE_ENUMERATOR)
    collection = ctypes.c_void_p()
    outputs: list[AudioOutput] = []
    try:
        _check_hresult(
            _vtable_call(
                enumerator,
                3,
                HRESULT,
                [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                E_DATA_FLOW_RENDER,
                state_mask,
                ctypes.byref(collection),
            ),
            "EnumAudioEndpoints",
        )
        count = wintypes.UINT()
        _check_hresult(
            _vtable_call(collection, 3, HRESULT, [ctypes.POINTER(wintypes.UINT)], ctypes.byref(count)),
            "GetDeviceCount",
        )
        for index in range(count.value):
            device = ctypes.c_void_p()
            try:
                _check_hresult(
                    _vtable_call(
                        collection,
                        4,
                        HRESULT,
                        [wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                        index,
                        ctypes.byref(device),
                    ),
                    "Item",
                )
                outputs.append(AudioOutput(_device_id(device), _friendly_name(device)))
            except AudioOutputError:
                # Windows can retain stale disabled endpoints whose property
                # store no longer opens. One orphan must not hide every other
                # remembered output shortcut.
                continue
            finally:
                if device:
                    _release(device)
        return outputs
    finally:
        if collection:
            _release(collection)
        _release(enumerator)


def _default_output() -> AudioOutput:
    enumerator = _co_create(CLSID_MM_DEVICE_ENUMERATOR, IID_MM_DEVICE_ENUMERATOR)
    device = ctypes.c_void_p()
    try:
        _check_hresult(
            _vtable_call(
                enumerator,
                4,
                HRESULT,
                [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                E_DATA_FLOW_RENDER,
                E_ROLE_MULTIMEDIA,
                ctypes.byref(device),
            ),
            "GetDefaultAudioEndpoint",
        )
        return AudioOutput(_device_id(device), _friendly_name(device))
    finally:
        if device:
            _release(device)
        _release(enumerator)


def _set_default_output(device_id: str) -> None:
    policy = _co_create(CLSID_POLICY_CONFIG_CLIENT, IID_POLICY_CONFIG)
    try:
        for role in (E_ROLE_CONSOLE, E_ROLE_MULTIMEDIA, E_ROLE_COMMUNICATIONS):
            _check_hresult(
                _vtable_call(
                    policy,
                    13,
                    HRESULT,
                    [wintypes.LPCWSTR, wintypes.DWORD],
                    device_id,
                    role,
                ),
                "SetDefaultEndpoint",
            )
    finally:
        _release(policy)


def current_output() -> AudioOutput:
    return _with_com(_default_output)


def active_outputs() -> list[AudioOutput]:
    return _with_com(_enumerate_outputs)


def known_outputs() -> list[AudioOutput]:
    """Return active and remembered render endpoints for shortcut setup."""
    return _with_com(lambda: _enumerate_outputs(DEVICE_STATEMASK_ALL))


def set_default_output(device_id: str) -> None:
    if not device_id:
        raise AudioOutputError("Audio endpoint ID is empty")
    _with_com(lambda: _set_default_output(device_id))


def _activate_endpoint_volume(device: ctypes.c_void_p) -> ctypes.c_void_p:
    endpoint = ctypes.c_void_p()
    _check_hresult(
        _vtable_call(
            device,
            3,
            HRESULT,
            [ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
            ctypes.byref(_guid(IID_AUDIO_ENDPOINT_VOLUME)),
            CLSCTX_INPROC_SERVER,
            None,
            ctypes.byref(endpoint),
        ),
        "Activate(IAudioEndpointVolume)",
    )
    return endpoint


def _default_endpoint_volume() -> ctypes.c_void_p:
    enumerator = _co_create(CLSID_MM_DEVICE_ENUMERATOR, IID_MM_DEVICE_ENUMERATOR)
    device = ctypes.c_void_p()
    try:
        _check_hresult(
            _vtable_call(
                enumerator,
                4,
                HRESULT,
                [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)],
                E_DATA_FLOW_RENDER,
                E_ROLE_MULTIMEDIA,
                ctypes.byref(device),
            ),
            "GetDefaultAudioEndpoint",
        )
        return _activate_endpoint_volume(device)
    finally:
        if device:
            _release(device)
        _release(enumerator)


def _get_default_volume() -> int:
    endpoint = _default_endpoint_volume()
    try:
        value = ctypes.c_float()
        _check_hresult(
            _vtable_call(
                endpoint,
                9,
                HRESULT,
                [ctypes.POINTER(ctypes.c_float)],
                ctypes.byref(value),
            ),
            "GetMasterVolumeLevelScalar",
        )
        return max(0, min(100, int(round(value.value * 100))))
    finally:
        _release(endpoint)


def _set_default_volume(percent: int) -> None:
    endpoint = _default_endpoint_volume()
    try:
        _check_hresult(
            _vtable_call(
                endpoint,
                7,
                HRESULT,
                [ctypes.c_float, ctypes.c_void_p],
                max(0.0, min(1.0, percent / 100.0)),
                None,
            ),
            "SetMasterVolumeLevelScalar",
        )
    finally:
        _release(endpoint)


def current_volume() -> int:
    return _with_com(_get_default_volume)


def set_volume(percent: int) -> None:
    _with_com(lambda: _set_default_volume(max(0, min(100, int(percent)))))


def find_airpods(outputs: Iterable[AudioOutput]) -> AudioOutput | None:
    candidates = [item for item in outputs if item.is_airpods]
    candidates.sort(key=lambda item: ("hands-free" in item.name.casefold(), item.name.casefold()))
    return candidates[0] if candidates else None


def find_speaker(outputs: Iterable[AudioOutput], *, exclude_id: str = "") -> AudioOutput | None:
    candidates = [item for item in outputs if not item.is_airpods and item.device_id != exclude_id]
    if not candidates:
        return None

    def score(item: AudioOutput) -> tuple[int, str]:
        name = item.name.casefold()
        preferred = ("speaker", "realtek", "high definition", "display audio", "스피커")
        return (0 if any(token in name for token in preferred) else 1, name)

    return sorted(candidates, key=score)[0]


def find_headphones(outputs: Iterable[AudioOutput], *, exclude_id: str = "") -> AudioOutput | None:
    candidates = [
        item
        for item in outputs
        if item.device_id != exclude_id and item.kind == "headphones" and not item.is_airpods
    ]
    return sorted(candidates, key=lambda item: item.name.casefold())[0] if candidates else None
