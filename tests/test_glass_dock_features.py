import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QObject, QSettings, Signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_dock"))
import features  # noqa: E402
from features import DockFeatures  # noqa: E402
from prefs import DockPrefs  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])


class Devices(QObject):
    changed = Signal()
    batteriesChanged = Signal()

    def __init__(self):
        super().__init__()
        self.state = dict(name="AirPods Pro", connected=True)
        self.batteries = self.parts(80, 70, True, True)

    @staticmethod
    def parts(left, right, left_in, right_in):
        return [dict(label="L", value=left, charging=False, quality="fresh", inEar=left_in),
                dict(label="R", value=right, charging=False, quality="fresh", inEar=right_in),
                dict(label="CASE", value=60, charging=False, quality="fresh", inEar=False)]

    def set(self, *args):
        self.batteries = self.parts(*args)
        self.batteriesChanged.emit()


class Media:
    def __init__(self):
        self.state = dict(playing=True, token="t", identity="i")
        self.commands = []

    def command(self, action, token, identity):
        self.commands.append(action)


def make(tmp_path, monkeypatch, **values):
    monkeypatch.setattr(features, "is_game_foreground", lambda _names: False)
    settings = QSettings(str(tmp_path / "dock.ini"), QSettings.IniFormat)
    for key, value in values.items():
        settings.setValue(key.replace("_", "/", 1), value)
    devices, media = Devices(), Media()
    dock = DockFeatures(devices, media, DockPrefs(settings), tmp_path / "none.mp3", usage_path=tmp_path / "usage.json")
    notices = []
    dock.notice.connect(lambda *args: notices.append(args[1:3]))
    monkeypatch.setattr(dock, "play_alert", lambda: notices.append(("sound", "")))
    return dock, devices, media, notices


def test_low_battery_warns_once_until_it_recovers(tmp_path, monkeypatch):
    dock, devices, _media, notices = make(tmp_path, monkeypatch)
    devices.set(15, 70, True, True)
    devices.set(14, 70, True, True)
    assert notices == [("sound", ""), ("배터리 부족 · 왼쪽 15%", "low")]
    devices.set(35, 70, True, True)
    devices.set(18, 70, True, True)
    assert notices[-1] == ("배터리 부족 · 왼쪽 18%", "low")


def test_low_battery_respects_sound_setting(tmp_path, monkeypatch):
    dock, devices, _media, notices = make(tmp_path, monkeypatch, battery_sound=False)
    devices.set(10, 70, True, True)
    assert notices == [("배터리 부족 · 왼쪽 10%", "low")]


def test_connect_and_disconnect_notices(tmp_path, monkeypatch):
    dock, devices, _media, notices = make(tmp_path, monkeypatch)
    devices.state["connected"] = False
    devices.changed.emit()
    devices.state["connected"] = True
    devices.changed.emit()
    assert notices == [("연결 해제됨", "disconnected"), ("연결됨", "connected")]


def test_removing_both_buds_pauses_and_putting_them_back_resumes(tmp_path, monkeypatch):
    dock, devices, media, _notices = make(tmp_path, monkeypatch, media_autoResume=True)
    devices.set(80, 70, False, False)
    dock._confirm_pause(dock._ear_generation)
    assert media.commands == ["pause"]
    devices.set(80, 70, True, True)
    dock._confirm_resume(dock._ear_generation)
    assert media.commands == ["pause", "play"]


def test_stale_reading_is_not_a_removal(tmp_path, monkeypatch):
    dock, devices, media, _notices = make(tmp_path, monkeypatch)
    devices.batteries = [dict(p, quality="cached", inEar=False) for p in devices.batteries]
    devices.batteriesChanged.emit()
    assert dock._ear == (True, True)
    dock._confirm_pause(dock._ear_generation)
    assert media.commands == []


def test_auto_battery_source_takes_nearby_airpods_of_one_model_while_connected():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_audio_widget"))
    from types import SimpleNamespace
    from device_backend import DeviceBackend

    backend = SimpleNamespace(auto_sources=True, AUTO_RSSI=DeviceBackend.AUTO_RSSI, _auto_model=None,
                              _state=dict(connected=True))
    accept = lambda rssi, model: DeviceBackend._auto_accept(backend, SimpleNamespace(rssi=rssi, model_id=model))
    assert not accept(-80, 0x2027)           # too far to be the user's own
    assert accept(-55, 0x2027)
    assert not accept(-50, 0x2014)           # another model nearby is ignored
    backend._state["connected"] = False
    assert not accept(-50, 0x2027)           # not connected: never guess
    backend.auto_sources = False
    backend._state["connected"] = True
    assert not accept(-50, 0x2027)           # opt-in only (glass widget keeps manual sources)


def test_in_ear_holds_through_the_gap_between_advertisements(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_audio_widget"))
    from types import SimpleNamespace
    from device_backend import DeviceBackend

    class Scanner(QObject):
        advertisementReceived = Signal(object)
        errorOccurred = Signal(str)

    now = [0.0]
    backend = DeviceBackend(scanner=Scanner(), settings=QSettings(str(tmp_path / "d.ini"), QSettings.IniFormat),
                            start=False, clock=lambda: now[0])

    def state(in_ear, fresh):
        pod = lambda: SimpleNamespace(in_ear=in_ear, battery=SimpleNamespace(percent=60, charging=False))
        case = SimpleNamespace(battery=SimpleNamespace(percent=None, charging=False))
        return SimpleNamespace(current=SimpleNamespace(left=pod(), right=pod(), case=case, in_ear_fresh=fresh))

    backend._valid_at = {"left": 0.0, "right": 0.0}
    backend._manager = state(True, True)
    backend.refresh()
    assert [b["inEar"] for b in backend.batteries[:2]] == [True, True]
    now[0] = 4.0   # the state manager has cleared the flags as uncertain
    backend._manager = state(False, False)
    backend.refresh()
    assert [b["inEar"] for b in backend.batteries[:2]] == [True, True]
    now[0] = 11.0  # no fresh reading any more: unknown, and marked cached
    backend.refresh()
    assert [(b["inEar"], b["quality"]) for b in backend.batteries[:2]] == [(False, "cached")] * 2


def test_module_order_visibility_and_size(tmp_path):
    prefs = DockPrefs(QSettings(str(tmp_path / "dock.ini"), QSettings.IniFormat))
    shown = [m["id"] for m in prefs.modules if m["visible"]]
    assert shown == ["airpods", "media", "volume", "output", "launcher"]
    prefs.moveModule("launcher", -10)
    prefs.setModuleVisible("media", False)
    assert [(m["id"], m["visible"]) for m in prefs.modules][:3] == [("launcher", True), ("airpods", True),
                                                                     ("media", False)]
    prefs.addModule("clock", "full")                     # from the gallery: after the last visible card
    shown = [m["id"] for m in prefs.modules if m["visible"]]
    assert shown[-1] == "clock" and next(m for m in prefs.modules if m["id"] == "clock")["size"] == "full"
    prefs.setModuleSize("clock", "half")
    prefs.setModuleSize("airpods", "half")               # AirPods has no half size: ignored
    sizes = {m["id"]: m["size"] for m in prefs.modules}
    assert sizes["clock"] == "half" and sizes["airpods"] == "full"
    prefs.moveModuleTo("clock", 0)
    assert prefs.modules[0]["id"] == "clock"
    for module in [m["id"] for m in prefs.modules]:
        prefs.setModuleVisible(module, False)
    assert any(m["visible"] for m in prefs.modules)  # the last visible module cannot be hidden


def test_cpu_percent_from_idle_and_busy_time():
    from system_status import cpu_percent
    assert cpu_percent((100, 1000), (150, 1100)) == 50     # 50 of 100 ticks idle
    assert cpu_percent((100, 1000), (100, 1000)) == 0      # no time passed


def test_codex_limits_read_from_the_session_log(tmp_path):
    import json, time
    from ai_status import codex_limits
    now = time.time()
    entry = {"type": "event_msg", "payload": {"rate_limits": {
        "primary": {"used_percent": 42.0, "window_minutes": 300, "resets_at": now + 3600},
        "secondary": {"used_percent": 99.0, "window_minutes": 10080, "resets_at": now - 60}}}}
    log = tmp_path / "rollout.jsonl"
    log.write_text(json.dumps({"type": "other"}) + "\n" + json.dumps(entry) + "\n", encoding="utf-8")
    limits = codex_limits(log, now)["limits"]
    assert [(l["label"], l["used"]) for l in limits] == [("5시간", 42), ("주간", 0)]   # the weekly window rolled over
    assert codex_limits(None)["limits"] == []


def test_claude_tokens_count_each_reply_once(tmp_path):
    import json, time
    from datetime import datetime, timezone
    from ai_status import claude_today
    project = tmp_path / "proj"
    project.mkdir()
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    line = lambda mid, out: json.dumps({"timestamp": stamp, "message": {"id": mid, "usage": {
        "input_tokens": 10, "output_tokens": out, "cache_creation_input_tokens": 5, "cache_read_input_tokens": 999}}})
    (project / "s.jsonl").write_text("\n".join([line("a", 1), line("a", 20), line("b", 100)]) + "\n", encoding="utf-8")
    assert claude_today(tmp_path, time.time())["tokens"] == (10 + 20 + 5) + (10 + 100 + 5)


def test_claude_limits_read_from_the_status_line_save(tmp_path):
    import json
    import time
    from ai_status import claude_limits
    now = time.time()
    saved = tmp_path / "claude_limits.json"
    saved.write_text("﻿" + json.dumps({"five_hour": {"used_percentage": 37.4, "resets_at": now - 60},
                                              "seven_day": {"used_percentage": 81, "resets_at": now + 3600}}),
                     encoding="utf-8")
    limits = claude_limits(saved, now)["limits"]
    assert [(l["label"], l["used"]) for l in limits] == [("5시간", 0), ("주간", 81)]   # the 5-hour one rolled over
    assert limits[1]["resetsAt"] == (now + 3600) * 1000
    assert claude_limits(tmp_path / "missing.json")["limits"] == []


def test_web_addresses_and_site_names():
    from launcher import normalize_url, site_name
    assert normalize_url("naver.com") == "https://naver.com"
    assert normalize_url(" https://www.instagram.com/ ") == "https://www.instagram.com/"
    assert normalize_url("not a site") == "" and normalize_url("hello") == "" and normalize_url("ftp://x.com") == ""
    assert site_name("https://www.instagram.com/") == "Instagram"
    assert site_name("https://m.naver.com") == "Naver"
    assert site_name("https://www.naver.co.kr") == "Naver"


def test_launcher_adds_sites_follows_shortcuts_and_reorders(tmp_path, monkeypatch):
    import time
    import launcher
    from PySide6.QtCore import QCoreApplication, QSettings, QUrl
    from PySide6.QtGui import QImage
    app = QCoreApplication.instance() or QCoreApplication([])
    icon = QImage(64, 64, QImage.Format_ARGB32)
    icon.fill(0xFF3366CC)
    monkeypatch.setattr(launcher, "fetch_site", lambda url: (icon, "NAVER" if "naver" in url else ""))
    settings = QSettings(str(tmp_path / "launcher.ini"), QSettings.IniFormat)
    backend = launcher.LauncherBackend(settings)
    shortcut = tmp_path / "Insta.url"
    shortcut.write_text("[InternetShortcut]\nURL=https://www.instagram.com/\n", encoding="utf-8")
    exe = tmp_path / "tool.exe"
    exe.write_bytes(b"")
    assert backend.addWebsite("naver.com")
    assert not backend.addWebsite("naver.com")          # already there
    assert backend.addUrls([QUrl.fromLocalFile(str(shortcut)), QUrl.fromLocalFile(str(exe)),
                            QUrl("https://github.com/")]) == 3
    deadline = time.time() + 5
    while any(not a["hasIcon"] for a in backend.apps if a.get("url")) and time.time() < deadline:
        app.processEvents()
    apps = backend.apps
    assert [a["name"] for a in apps] == ["NAVER", "Instagram", "tool", "Github"]
    assert all(a["hasIcon"] for a in apps)
    backend.move(3, 0)
    assert [a["name"] for a in backend.apps] == ["Github", "NAVER", "Instagram", "tool"]
    again = launcher.LauncherBackend(QSettings(str(tmp_path / "launcher.ini"), QSettings.IniFormat))
    assert [(a["name"], a.get("url", "")) for a in again.apps][:2] == [("Github", "https://github.com/"),
                                                                       ("NAVER", "https://naver.com")]
