from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class BluetoothDeviceStatus:
    name: str
    address: int
    paired: bool
    connected: bool


class BluetoothConnectionError(RuntimeError):
    """Raised when Windows cannot request a paired Bluetooth audio link."""


_A2DP_AUDIO_SINK_SERVICE = "{0000110B-0000-1000-8000-00805F9B34FB}"
_BLUETOOTH_SERVICE_DISABLE = 0
_BLUETOOTH_SERVICE_ENABLE = 1
_ERROR_SUCCESS = 0
_ERROR_INVALID_PARAMETER = 87
_ERROR_SERVICE_DOES_NOT_EXIST = 1060
_E_INVALIDARG = 0x80070057


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class _BLUETOOTH_FIND_RADIO_PARAMS(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD)]


if os.name == "nt":
    class BLUETOOTH_ADDRESS(ctypes.Union):
        _fields_ = [("ullLong", ctypes.c_ulonglong), ("rgBytes", ctypes.c_ubyte * 6)]


    class SYSTEMTIME(ctypes.Structure):
        _fields_ = [
            ("wYear", wintypes.WORD),
            ("wMonth", wintypes.WORD),
            ("wDayOfWeek", wintypes.WORD),
            ("wDay", wintypes.WORD),
            ("wHour", wintypes.WORD),
            ("wMinute", wintypes.WORD),
            ("wSecond", wintypes.WORD),
            ("wMilliseconds", wintypes.WORD),
        ]


    class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("Address", BLUETOOTH_ADDRESS),
            ("ulClassofDevice", wintypes.ULONG),
            ("fConnected", wintypes.BOOL),
            ("fRemembered", wintypes.BOOL),
            ("fAuthenticated", wintypes.BOOL),
            ("stLastSeen", SYSTEMTIME),
            ("stLastUsed", SYSTEMTIME),
            ("szName", wintypes.WCHAR * 248),
        ]


    class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("fReturnAuthenticated", wintypes.BOOL),
            ("fReturnRemembered", wintypes.BOOL),
            ("fReturnUnknown", wintypes.BOOL),
            ("fReturnConnected", wintypes.BOOL),
            ("fIssueInquiry", wintypes.BOOL),
            ("cTimeoutMultiplier", ctypes.c_ubyte),
            ("hRadio", wintypes.HANDLE),
        ]


def find_airpods_status() -> Optional[BluetoothDeviceStatus]:
    """Return the remembered AirPods device and its current connection state."""
    if os.name != "nt":
        return None

    library = ctypes.WinDLL("bthprops.cpl")
    first = library.BluetoothFindFirstDevice
    next_device = library.BluetoothFindNextDevice
    close = library.BluetoothFindDeviceClose
    first.argtypes = [ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS), ctypes.POINTER(BLUETOOTH_DEVICE_INFO)]
    first.restype = wintypes.HANDLE
    next_device.argtypes = [wintypes.HANDLE, ctypes.POINTER(BLUETOOTH_DEVICE_INFO)]
    next_device.restype = wintypes.BOOL
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL

    params = BLUETOOTH_DEVICE_SEARCH_PARAMS()
    params.dwSize = ctypes.sizeof(params)
    params.fReturnAuthenticated = True
    params.fReturnRemembered = True
    params.fReturnUnknown = False
    params.fReturnConnected = True
    params.fIssueInquiry = False
    params.cTimeoutMultiplier = 1
    params.hRadio = None

    info = BLUETOOTH_DEVICE_INFO()
    info.dwSize = ctypes.sizeof(info)
    handle = first(ctypes.byref(params), ctypes.byref(info))
    if not handle:
        return None
    try:
        while True:
            paired = bool(info.fAuthenticated) or bool(info.fRemembered)
            if paired and "airpods" in info.szName.casefold():
                return BluetoothDeviceStatus(
                    info.szName,
                    info.Address.ullLong,
                    paired=True,
                    connected=bool(info.fConnected),
                )
            info = BLUETOOTH_DEVICE_INFO()
            info.dwSize = ctypes.sizeof(info)
            if not next_device(handle, ctypes.byref(info)):
                break
    finally:
        close(handle)
    return None


def find_connected_airpods() -> Optional[BluetoothDeviceStatus]:
    """Compatibility helper that returns AirPods only while connected."""
    device = find_airpods_status()
    return device if device is not None and device.connected else None


def reconnect_paired_audio(device: Optional[BluetoothDeviceStatus] = None) -> None:
    """Ask the Windows Bluetooth stack to reconnect a paired audio device.

    Windows does not expose a general desktop ``ConnectAsync`` for a paired
    A2DP endpoint. Resetting the built-in Audio Sink service is the documented
    user-mode Bluetooth service operation that makes Windows renegotiate the
    paired audio link. It does not install a custom driver or open a raw
    Bluetooth socket.
    """
    if os.name != "nt":
        raise BluetoothConnectionError("Bluetooth audio reconnect is Windows-only")

    device = device or find_airpods_status()
    if device is None or not device.paired:
        raise BluetoothConnectionError("No paired Bluetooth audio device was found")

    device_info = BLUETOOTH_DEVICE_INFO()
    device_info.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_INFO)
    device_info.Address.ullLong = device.address
    device_info.fRemembered = True
    device_info.fAuthenticated = True

    bluetooth = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
    find_first_radio = bluetooth.BluetoothFindFirstRadio
    find_first_radio.argtypes = [
        ctypes.POINTER(_BLUETOOTH_FIND_RADIO_PARAMS),
        ctypes.POINTER(wintypes.HANDLE),
    ]
    find_first_radio.restype = wintypes.HANDLE
    close_radio_find = bluetooth.BluetoothFindRadioClose
    close_radio_find.argtypes = [wintypes.HANDLE]
    close_radio_find.restype = wintypes.BOOL
    set_service_state = bluetooth.BluetoothSetServiceState
    set_service_state.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
        ctypes.POINTER(_GUID),
        wintypes.DWORD,
    ]
    set_service_state.restype = wintypes.DWORD

    radio_params = _BLUETOOTH_FIND_RADIO_PARAMS()
    radio_params.dwSize = ctypes.sizeof(radio_params)
    radio = wintypes.HANDLE()
    radio_find = find_first_radio(ctypes.byref(radio_params), ctypes.byref(radio))
    if not radio_find or not radio.value:
        error = ctypes.get_last_error()
        raise BluetoothConnectionError(
            f"Bluetooth radio was not available (Win32 error {error})"
        )

    try:
        service_guid = _GUID()
        ole32 = ctypes.WinDLL("ole32")
        clsid_from_string = ole32.CLSIDFromString
        clsid_from_string.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(_GUID)]
        clsid_from_string.restype = ctypes.c_long
        if clsid_from_string(_A2DP_AUDIO_SINK_SERVICE, ctypes.byref(service_guid)) != 0:
            raise BluetoothConnectionError("A2DP service GUID could not be parsed")

        disable_result = int(
            set_service_state(
                radio.value,
                ctypes.byref(device_info),
                ctypes.byref(service_guid),
                _BLUETOOTH_SERVICE_DISABLE,
            )
        )
        if disable_result == _ERROR_SERVICE_DOES_NOT_EXIST:
            raise BluetoothConnectionError("Paired device has no Audio Sink service")
        if disable_result not in (_ERROR_SUCCESS, _ERROR_INVALID_PARAMETER, _E_INVALIDARG):
            raise BluetoothConnectionError(
                f"Audio Sink disconnect request failed (Win32 error {disable_result})"
            )

        enable_result = int(
            set_service_state(
                radio.value,
                ctypes.byref(device_info),
                ctypes.byref(service_guid),
                _BLUETOOTH_SERVICE_ENABLE,
            )
        )
        if enable_result == _ERROR_SERVICE_DOES_NOT_EXIST:
            raise BluetoothConnectionError("Paired device has no Audio Sink service")
        if enable_result not in (_ERROR_SUCCESS, _ERROR_INVALID_PARAMETER, _E_INVALIDARG):
            raise BluetoothConnectionError(
                f"Audio Sink connect request failed (Win32 error {enable_result})"
            )
    finally:
        close_radio_find(radio_find)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        close_handle(radio.value)
