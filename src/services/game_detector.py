from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Iterable


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def foreground_process_name() -> str:
    if os.name != "nt":
        return ""

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    get_foreground_window = user32.GetForegroundWindow
    get_foreground_window.argtypes = []
    get_foreground_window.restype = wintypes.HWND

    get_window_process = user32.GetWindowThreadProcessId
    get_window_process.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    get_window_process.restype = wintypes.DWORD

    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE

    query_image_name = kernel32.QueryFullProcessImageNameW
    query_image_name.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    query_image_name.restype = wintypes.BOOL

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    hwnd = get_foreground_window()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    get_window_process(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    handle = open_process(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not query_image_name(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return os.path.basename(buffer.value)
    finally:
        close_handle(handle)


def is_game_foreground(process_names: Iterable[str]) -> bool:
    current = foreground_process_name().casefold()
    return bool(current) and current in {name.casefold() for name in process_names}
