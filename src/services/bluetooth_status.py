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
