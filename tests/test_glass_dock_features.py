import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QObject, QSettings, Signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_dock"))
import features  # noqa: E402
from features import DockFeatures  # noqa: E402

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
    dock = DockFeatures(devices, media, settings, tmp_path / "none.mp3", usage_path=tmp_path / "usage.json")
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
