from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Any

def apply_window_material(window: Any, dark: bool) -> bool:
    """Apply a native Windows backdrop, then keep QML responsible for shape."""
    if os.name != "nt":
        return False
    try:
        hwnd = int(window.winId())
    except (AttributeError, TypeError, ValueError, OSError):
        return False
    if not hwnd:
        return False

    backdrop_applied = _apply_dwm_backdrop(hwnd, dark)
    # The region is still required because a DWM backdrop is painted for the
    # whole HWND. It prevents the transparent QML margin from becoming a
    # rectangular patch around the rounded shell.
    shaped = apply_window_shape(window)
    return backdrop_applied or shaped


def _apply_dwm_backdrop(hwnd: int, dark: bool) -> bool:
    """Use Windows 11's transient Acrylic backdrop when the OS exposes it.

    This is a documented DWM window attribute. Windows 10 simply returns a
    failure and the caller keeps the QML alpha-material fallback; no driver,
    service, hook, or audio device manipulation is involved.
    """
    try:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        set_attribute = dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        set_attribute.restype = ctypes.c_long

        dark_mode = ctypes.c_int(1 if dark else 0)
        # DWMWA_USE_IMMERSIVE_DARK_MODE is supported on current Windows 10/11.
        set_attribute(
            wintypes.HWND(hwnd),
            20,
            ctypes.byref(dark_mode),
            ctypes.sizeof(dark_mode),
        )

        # DWMWA_SYSTEMBACKDROP_TYPE / DWMSBT_TRANSIENTWINDOW = Acrylic.
        backdrop_type = ctypes.c_int(3)
        result = set_attribute(
            wintypes.HWND(hwnd),
            38,
            ctypes.byref(backdrop_type),
            ctypes.sizeof(backdrop_type),
        )
        return result >= 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def apply_window_shape(window: Any) -> bool:
    """Clip translucent top-level windows to their rounded visual surface."""
    if os.name != "nt":
        return False
    try:
        hwnd = int(window.winId())
        width = max(1, int(window.width()))
        height = max(1, int(window.height()))
        inset = max(0, int(window.property("materialInset") or 0))
        radius = max(1, int(window.property("materialCornerRadius") or 32))
        radius = min(radius, max(1, min(width, height) // 2))
    except (AttributeError, TypeError, ValueError, OSError):
        return False
    if not hwnd:
        return False

    try:
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32.CreateRoundRectRgn.argtypes = [
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
        ]
        # ctypes does not expose HRGN on every Python 3.11 Windows build;
        # HRGN is an opaque HANDLE in the Win32 API.
        gdi32.CreateRoundRectRgn.restype = wintypes.HANDLE
        user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        user32.SetWindowRgn.restype = ctypes.c_int
        region = gdi32.CreateRoundRectRgn(
            inset,
            inset,
            max(inset + 1, width - inset),
            max(inset + 1, height - inset),
            radius * 2,
            radius * 2,
        )
        if not region:
            return False
        return bool(user32.SetWindowRgn(wintypes.HWND(hwnd), region, True))
    except (AttributeError, OSError):
        return False
