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
    assert loaded.get("widget", "layout_mode") == "flow"
    assert loaded.get("media", "always_visible") is False


def test_widget_layout_mode_defaults_to_flow(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.get("widget", "layout_mode") == "flow"
