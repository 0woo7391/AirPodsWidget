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


def test_module_order_and_visibility(tmp_path):
    prefs = DockPrefs(QSettings(str(tmp_path / "dock.ini"), QSettings.IniFormat))
    assert [m["id"] for m in prefs.modules] == ["airpods", "media", "volume", "output", "launcher", "instagram"]
    prefs.moveModule("launcher", -10)
    prefs.setModuleVisible("media", False)
    assert [(m["id"], m["visible"]) for m in prefs.modules][:3] == [("launcher", True), ("airpods", True),
                                                                     ("media", False)]
    for module in ["airpods", "launcher", "volume", "output", "instagram"]:
        prefs.setModuleVisible(module, False)
    assert any(m["visible"] for m in prefs.modules)  # the last visible module cannot be hidden


def test_instagram_toasts_are_recognised_and_others_ignored():
    from notifications import instagram_message
    assert instagram_message("Google Chrome Chrome", ["mika", "오늘 저녁 어때?", "instagram.com"]) == ("mika", "오늘 저녁 어때?")
    assert instagram_message("Google Chrome Chrome", ["Instagram", "mika: 안녕", "instagram.com"]) == ("mika", "안녕")
    assert instagram_message("Instagram Facebook.InstagramBeta", ["mika", "사진을 보냈습니다"]) == ("mika", "사진을 보냈습니다")
    assert instagram_message("Google Chrome Chrome", ["YouTube", "새 동영상", "youtube.com"]) is None
    assert instagram_message("Discord", ["mika", "instagram 링크 봤어?"]) is None   # not a browser or the app


def test_instagram_dm_hides_content_unless_allowed(tmp_path, monkeypatch):
    dock, _devices, _media, notices = make(tmp_path, monkeypatch)
    titles = []
    dock.notice.connect(lambda title, *_: titles.append(title))
    dock.on_instagram("mika", "비밀 내용")
    assert notices[-1] == ("Instagram 새 메시지", "message") and titles[-1] == "mika"
    dock.set("island/instagramContent", True)
    dock.on_instagram("mika", "비밀 내용")
    assert notices[-1] == ("비밀 내용", "message")
    dock.set("island/instagram", False)
    dock.on_instagram("mika", "x")
    assert len(notices) == 2


def test_watcher_keeps_recent_dms_and_unread_count():
    from notifications import MAX_RECENT, NotificationWatcher
    watcher = NotificationWatcher()
    seen = []
    watcher.message.connect(lambda sender, content: seen.append(sender))
    for i in range(MAX_RECENT + 3):
        watcher.add(f"user{i}", "hi")
    assert len(watcher.messages) == MAX_RECENT and watcher.messages[0]["sender"] == f"user{MAX_RECENT + 2}"
    assert watcher.unread == MAX_RECENT + 3 and len(seen) == MAX_RECENT + 3
    watcher.markRead()
    assert watcher.unread == 0 and len(watcher.messages) == MAX_RECENT


def test_blocked_instagram_permission_is_found(tmp_path, monkeypatch):
    import json
    from notifications import blocked_browsers
    profile = tmp_path / "Google" / "Chrome" / "User Data" / "Default"
    profile.mkdir(parents=True)
    sites = {"https://www.instagram.com:443,*": {"setting": 2}}
    (profile / "Preferences").write_text(json.dumps(
        {"profile": {"content_settings": {"exceptions": {"notifications": sites}}}}), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert blocked_browsers() == ["Chrome"]
    sites["https://www.instagram.com:443,*"]["setting"] = 1
    (profile / "Preferences").write_text(json.dumps(
        {"profile": {"content_settings": {"exceptions": {"notifications": sites}}}}), encoding="utf-8")
    assert blocked_browsers() == []


def test_sender_found_in_other_instagram_body_formats():
    from notifications import format_shape, instagram_message
    chrome = "Google Chrome Chrome"
    assert instagram_message(chrome, ["Instagram", "공주님이 메시지를 보냈습니다.", "instagram.com"])[0] == "공주"
    assert instagram_message(chrome, ["Instagram", "mika sent you a message.", "instagram.com"])[0] == "mika"
    assert instagram_message(chrome, ["Instagram", "mika · 사진", "instagram.com"]) == ("mika", "사진")
    assert instagram_message(chrome, ["Instagram", "새 알림이 있습니다", "instagram.com"])[0] == "Instagram"
    assert format_shape("공주: hi 12!") == "가가: aa 00!"


def test_unnamed_follow_up_dm_takes_the_one_recent_sender_and_repeats_are_dropped():
    from notifications import NotificationWatcher
    watcher = NotificationWatcher()
    watcher.add("공주", "안녕")
    watcher.add("Instagram", "뭐해")            # follow-up without a name
    watcher.add("Instagram", "뭐해")            # the same notification re-posted
    assert [(m["sender"], m["content"]) for m in watcher.messages] == [("공주", "뭐해"), ("공주", "안녕")]
    assert watcher.unread == 2
    watcher.add("mika", "hi")
    watcher.add("Instagram", "누구게")           # two named chats: no guess
    assert watcher.messages[0]["sender"] == "Instagram"
