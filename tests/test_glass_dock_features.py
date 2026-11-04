import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QObject, QSettings, Signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_dock"))
import features  # noqa: E402
from features import DockFeatures  # noqa: E402
from prefs import DockPrefs  # noqa: E402

from PySide6.QtGui import QGuiApplication  # noqa: E402

# A GUI application: the memo test lays out text documents.
_app = QCoreApplication.instance() or QGuiApplication([])


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


def test_event_reminders_fire_once_and_survive_a_restart(tmp_path):
    from datetime import datetime, timedelta
    from PySide6.QtCore import QCoreApplication
    from events import EventStore
    QCoreApplication.instance() or QCoreApplication([])
    clock = {"now": datetime(2026, 11, 4, 14, 0)}
    path = tmp_path / "events.json"
    store = EventStore(path, clock=lambda: clock["now"], start=False)
    shown = []
    store.reminder.connect(lambda *args: shown.append(args))
    meeting = store.save(dict(date="2026-11-04", time="14:30", title="디자인 리뷰", color=store.colors[2], remind=10))
    store.save(dict(date="2026-11-05", time="", title="생일", color=store.colors[3], remind=0))
    assert store.save(dict(date="2026-11-04", time="25:00", title="x", remind=0)) == ""     # bad time
    assert store.save(dict(date="2026-11-04", time="", title="  ", remind=0)) == ""       # no title
    assert store.next["title"] == "디자인 리뷰" and store.next["when"] == "오늘 14:30"
    assert store.marks == {"2026-11-04": [store.colors[2]], "2026-11-05": [store.colors[3]]}
    store.check()
    assert shown == []
    clock["now"] = datetime(2026, 11, 4, 14, 20)
    store.check()
    store.check()
    assert shown == [("디자인 리뷰", "10분 후 · 14:30", store.colors[2])]
    # A restart does not repeat it; an all-day reminder long missed (dock was off) is skipped.
    clock["now"] = datetime(2026, 11, 5, 11, 0)
    again = EventStore(path, clock=lambda: clock["now"], start=False)
    again.reminder.connect(lambda *args: shown.append(args))
    again.check()
    assert len(shown) == 1
    # Moving the event later lets its reminder fire again.
    again.save(dict(id=meeting, date="2026-11-05", time="11:05", title="디자인 리뷰", color=store.colors[2], remind=5))
    again.check()
    assert shown[-1] == ("디자인 리뷰", "5분 후 · 11:05", store.colors[2])
    again.remove(meeting)
    assert [e["title"] for e in again.forDay("2026-11-05")] == ["생일"]


def test_memo_live_formatting_round_trips_as_markdown():
    from PySide6.QtGui import QGuiApplication, QTextCursor, QTextDocument
    from memo_format import MemoFormat
    QGuiApplication.instance() or QGuiApplication([])
    f = MemoFormat()
    doc = QTextDocument()

    def end():
        c = QTextCursor(doc)
        c.movePosition(QTextCursor.End)
        return c.position()

    def type_(text):
        """Like the editor: Enter on an empty item ends the list; typing after an inline style is plain."""
        pending = []
        for ch in text:
            c = QTextCursor(doc)
            c.movePosition(QTextCursor.End)
            if ch == "\n":
                if f.blockKind(doc, end()) != "plain" and f.blockEmpty(doc, end()):
                    f.setBlock(doc, end(), "plain")
                    continue
                c.insertBlock()
                f.afterNewline(doc, end())
            else:
                start = end()
                c.insertText(ch)
                for kind in pending:
                    f.apply(doc, start, start + 1, kind, False)
                pending = []
            moved = f.autoformat(doc, end())
            if moved >= 0 and moved != f.blockStart(doc, moved):   # inline style, not a line prefix
                pending = [k for k in ("bold", "strike") if f.has(doc, moved, k)]

    type_("# 장보기\n- 우유\n- 빵\n\n[] 계란\n\n그냥 **굵게** 글 ~~취소~~ 끝 www.naver.com 링크")
    md = doc.toMarkdown()
    assert md.startswith("# 장보기\n\n- 우유\n- 빵\n- [ ] 계란\n")
    # Bold is checked on the text: the offscreen test platform has no fonts, and Qt's
    # Markdown export reads bold through the font (it saves fine on Windows).
    assert "그냥 굵게 글 ~~취소~~ 끝 [www.naver.com](https://www.naver.com) 링크" in md.replace("**", "")
    line = doc.lastBlock()
    bold_at = line.position() + line.text().index("굵게")
    assert f.has(doc, bold_at + 1, "bold") and f.has(doc, bold_at + 2, "bold")
    assert not f.has(doc, bold_at + 3, "bold") and not f.has(doc, line.position() + 1, "bold")
    assert f.toggle(doc, bold_at, bold_at + 2, "bold") is False and not f.has(doc, bold_at + 1, "bold")
    # check it, take the bullet off "빵", and the heading back to a plain line
    f.toggleCheck(doc, doc.findBlockByNumber(3).position())
    f.setBlock(doc, doc.findBlockByNumber(2).position(), "plain")
    f.setBlock(doc, 0, "plain")
    md = doc.toMarkdown()
    assert md.startswith("장보기\n\n- 우유\n\n빵\n\n- [x] 계란")
    again = QTextDocument()
    again.setMarkdown(md)
    f.normalize(again)
    assert again.toMarkdown() == md


def test_events_over_several_days(tmp_path):
    from datetime import datetime
    from events import EventStore
    store = EventStore(tmp_path / "events.json", clock=lambda: datetime(2026, 11, 3, 9, 0), start=False)
    trip = store.save(dict(date="2026-11-04", end="2026-11-08", time="", title="여행", color=store.colors[4], remind=0))
    store.save(dict(date="2026-11-06", time="12:00", title="점심", color=store.colors[1], remind=-1))
    assert store.save(dict(date="2026-11-08", end="2026-11-04", title="거꾸로", remind=-1)) == ""
    assert [e["title"] for e in store.forDay("2026-11-06")] == ["여행", "점심"]
    assert store.forDay("2026-11-06")[0]["span"] == "11/4–11/8"
    assert store.forDay("2026-11-09") == []
    assert [(r["id"], r["date"], r["end"]) for r in store.ranges] == [(trip, "2026-11-04", "2026-11-08")]
    assert store.marks == {"2026-11-06": [store.colors[1]]}       # dots only for one-day events
    assert store.next["when"] == "내일 11/4–11/8"
    # An old save without an end reads as one day.
    again = EventStore(tmp_path / "events.json", start=False)
    assert all(e["end"] >= e["date"] for e in again.forDay("2026-11-06"))


def test_codex_limits_come_from_the_newest_session_that_has_them(tmp_path):
    import json
    import os
    import time
    from ai_status import latest_codex_limits
    now = time.time()
    old = tmp_path / "2026" / "11" / "01" / "rollout-a.jsonl"
    new = tmp_path / "2026" / "11" / "04" / "rollout-b.jsonl"
    for path in (old, new):
        path.parent.mkdir(parents=True)
    old.write_text(json.dumps({"payload": {"rate_limits": {"secondary": {
        "used_percent": 99, "window_minutes": 10080, "resets_at": now + 3600}}}}) + "\n", encoding="utf-8")
    new.write_text('{"payload": {"type": "session_meta"}}\n', encoding="utf-8")   # opened, no turn yet
    os.utime(old, (now - 86400, now - 86400))
    limits = latest_codex_limits(tmp_path, now)["limits"]
    assert [(l["label"], l["used"]) for l in limits] == [("주간", 99)]
    assert latest_codex_limits(tmp_path / "missing", now)["limits"] == []


def test_claude_usage_reads_the_usage_page_without_leaking_the_login(tmp_path, monkeypatch):
    import io
    import json
    import time
    import urllib.request
    import ai_status
    now = time.time()
    login = tmp_path / ".credentials.json"
    login.write_text(json.dumps({"claudeAiOauth": {"accessToken": "secret-token", "expiresAt": (now + 3600) * 1000}}),
                     encoding="utf-8")
    seen = {}

    def answer(request, timeout):
        seen["url"], seen["auth"] = request.full_url, request.get_header("Authorization")
        return io.BytesIO(json.dumps({
            "five_hour": {"utilization": 53.0, "resets_at": "2099-01-01T00:00:00+00:00"},
            "seven_day": {"utilization": 50.0, "resets_at": now - 60}}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", answer)
    result = ai_status.claude_usage(login, now)
    assert seen == {"url": "https://api.anthropic.com/api/oauth/usage", "auth": "Bearer secret-token"}
    assert [(l["label"], l["used"]) for l in result["limits"]] == [("5시간", 53), ("주간", 0)]   # the week rolled over
    assert result["note"] == "" and "secret-token" not in json.dumps(result)
    # An expired login is not sent anywhere (renewing it is left to Claude).
    login.write_text(json.dumps({"claudeAiOauth": {"accessToken": "secret-token", "expiresAt": (now - 60) * 1000}}),
                     encoding="utf-8")
    seen.clear()
    assert ai_status.claude_usage(login, now)["note"] == "expired" and seen == {}
    assert ai_status.claude_usage(tmp_path / "none.json", now)["note"] == "nologin"
