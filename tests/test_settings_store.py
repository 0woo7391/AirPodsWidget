from pathlib import Path

from services.settings_store import SettingsStore


def test_round_trip_and_default_merge(tmp_path: Path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.set("battery", "volume", 77)
    loaded = SettingsStore(path)
    assert loaded.get("battery", "volume") == 77
    assert loaded.get("widget", "theme") == "dark"
    assert loaded.get("widget", "always_on_top") is False
