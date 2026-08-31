from __future__ import annotations

import os
import sys


def set_start_with_windows(enabled: bool, app_name: str = "AirPodsWidget") -> None:
    if os.name != "nt":
        return
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            executable = sys.executable
            value = f'"{executable}"'
            if not getattr(sys, "frozen", False):
                value += f' "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
