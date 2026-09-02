from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "widget": {
        "visible": True,
        "x": 72,
        "y": 72,
        "scale": 1.0,
        "opacity": 0.90,
        "locked": False,
        "always_on_top": False,
        "layout_mode": "flow",
        "theme": "dark",
    },
    "media": {
        "visible": True,
        "always_visible": False,
        "auto_pause": True,
        "auto_resume": False,
    },
    "audio": {
        # None means first-run auto setup. An empty list is a deliberate
        # choice to hide every output shortcut.
        "buttons": None,
    },
    "battery": {
        "alert_enabled": True,
        "threshold": 10,
        "reset_threshold": 20,
        "volume": 60,
        "popup_enabled": True,
        "sound_during_games": True,
        "popup_during_games": False,
    },
    "popup": {"connection_enabled": True, "suppress_during_games": True},
    "system": {
        "start_with_windows": False,
        "rssi_min": -85,
        "game_processes": [
            "League of Legends.exe",
            "LeagueClient.exe",
            "LeagueClientUx.exe",
            "VALORANT-Win64-Shipping.exe",
        ],
    },
}


def app_data_dir() -> Path:
    base = os.getenv("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    path = Path(base) / "AirPodsWidget"
    path.mkdir(parents=True, exist_ok=True)
    return path


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings.json"
        self.data = deepcopy(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self._deep_update(self.data, loaded)
        except (OSError, json.JSONDecodeError, TypeError):
            # Keep known-safe defaults when a settings file is damaged.
            return

    def save(self) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any, *, save: bool = True) -> None:
        self.data.setdefault(section, {})[key] = value
        if save:
            self.save()

    @staticmethod
    def _deep_update(target: dict[str, Any], incoming: dict[str, Any]) -> None:
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                SettingsStore._deep_update(target[key], value)
            else:
                target[key] = value
