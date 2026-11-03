"""Sample-data backends with the same QML surface as the real ones, for previews and checks."""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


class DemoAudio(QObject):
    changed = Signal()
    devicesChanged = Signal()
    quickOutputsChanged = Signal()

    def __init__(self):
        super().__init__()
        self._devices = [
            dict(id="airpods", name="AirPods Pro", kind="headphones", available=True),
            dict(id="speakers", name="스피커 (Realtek Audio)", kind="speaker", available=True),
            dict(id="monitor", name="LG ULTRAGEAR", kind="speaker", available=True),
        ]
        self.data = dict(available=True, currentId="airpods", name="AirPods Pro", kind="headphones",
                         volume=62, muted=False, pendingId="", error="", status="")

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self.data)

    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        return self._devices

    @Property("QVariantList", notify=quickOutputsChanged)
    def quickOutputs(self):
        return self._devices[:2]

    @Slot(int)
    def setVolume(self, value):
        self.data.update(volume=int(value), muted=False)
        self.changed.emit()

    @Slot()
    def toggleMute(self):
        self.data["muted"] = not self.data["muted"]
        self.changed.emit()

    @Slot(str)
    def selectOutput(self, key):
        device = next((d for d in self._devices if d["id"] == key), None)
        if device:
            self.data.update(currentId=key, name=device["name"], kind=device["kind"])
            self.changed.emit()


class DemoMedia(QObject):
    changed = Signal()
    contentChanged = Signal()

    def __init__(self):
        super().__init__()
        self.data = dict(available=True, token="demo", identity="ditto", title="Ditto",
                         artist="NewJeans", sourceName="Spotify", artwork="", playing=True,
                         pending=False, error="", status="", canPlay=True, canNext=True, canPrevious=True,
                         position=42.0, duration=185.0, seekable=True)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self.data)

    @Property("QVariantMap", notify=contentChanged)
    def content(self):
        return dict(self.data)

    @Slot(str, str, str)
    def command(self, action, token, identity):
        if action in ("toggle", "play", "pause"):
            self.data["playing"] = action == "play" or (action == "toggle" and not self.data["playing"])
            self.changed.emit()

    @Slot(str, str, float)
    def seek(self, token, identity, seconds):
        self.data["position"] = max(0.0, min(self.data["duration"], seconds))
        self.changed.emit()


class DemoDevices(QObject):
    changed = Signal()
    batteriesChanged = Signal()
    connectionHint = Signal()

    def __init__(self):
        super().__init__()
        self.data = dict(targetId="DEMO", name="AirPods Pro", paired=True, connected=True,
                         pending=False, error="", status="연결됨")
        self._batteries = [dict(label="L", value=80, charging=False, quality="fresh", inEar=True),
                           dict(label="R", value=70, charging=False, quality="fresh", inEar=True),
                           dict(label="CASE", value=60, charging=True, quality="fresh", inEar=False)]

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self.data)

    @Property("QVariantList", notify=batteriesChanged)
    def batteries(self):
        return self._batteries

    @Slot()
    def connectDevice(self):
        self.data.update(connected=True, pending=False, status="연결됨")
        self.changed.emit()


class DemoExtras(QObject):
    """Sample microphone and per-app volumes with the AudioExtras surface."""
    micChanged = Signal()
    sessionsChanged = Signal()
    micToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mic = dict(available=True, name="마이크 (Realtek Audio)", muted=False)
        self._sessions = [dict(key="spotify", path="C:/demo/Spotify.exe", name="Spotify", active=True, volume=70, muted=False),
                          dict(key="discord", path="C:/demo/Discord.exe", name="Discord", active=True, volume=100, muted=False),
                          dict(key="chrome", path="C:/demo/chrome.exe", name="Google Chrome", active=False, volume=45, muted=True)]

    @Property("QVariantMap", notify=micChanged)
    def mic(self):
        return dict(self._mic)

    @Property("QVariantList", notify=sessionsChanged)
    def sessions(self):
        return [dict(s) for s in self._sessions]

    @Slot()
    def toggleMic(self):
        self._mic["muted"] = not self._mic["muted"]
        self.micChanged.emit()
        self.micToggled.emit(self._mic["muted"])

    @Slot(str, int)
    def setAppVolume(self, key, value):
        for s in self._sessions:
            if s["key"] == key:
                s["volume"] = int(value)
        self.sessionsChanged.emit()

    @Slot(str)
    def toggleAppMute(self, key):
        for s in self._sessions:
            if s["key"] == key:
                s["muted"] = not s["muted"]
        self.sessionsChanged.emit()

    @Slot(str)
    def resetApp(self, key):
        for s in self._sessions:
            if s["key"] == key:
                s.update(volume=100, muted=False)
        self.sessionsChanged.emit()

    @Slot()
    def resetAllApps(self):
        for s in self._sessions:
            s.update(volume=100, muted=False)
        self.sessionsChanged.emit()


class DemoMeter(QObject):
    """A music-like level for previews: a beat with some wobble."""
    levelChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        import math
        self._t = 0.0
        self._level = 0.6
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self._math = math

    def _tick(self):
        self._t += 0.033
        beat = abs(self._math.sin(self._t * 3.6)) ** 3
        self._level = 0.35 + 0.5 * beat + 0.08 * self._math.sin(self._t * 17)
        self.levelChanged.emit()

    @Property(float, notify=levelChanged)
    def level(self):
        return self._level


class DemoSystem(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(cpu=23, memory=41, memoryUsed=13.1, memoryTotal=31.9, ping=6)


class DemoAi(QObject):
    """Sample assistants for previews (no logos: the cards fall back to their layout)."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        import time
        now = time.time() * 1000
        self._items = [
            dict(id="codex", name="Codex", logo="", unread=1, tokens=0, lastUsed=0, asOf=now - 3600e3,
                 limits=[dict(label="5시간", used=42, resetsAt=now + 2.2 * 3600e3, window=300),
                         dict(label="주간", used=91, resetsAt=now + 26 * 3600e3, window=10080)]),
            dict(id="claude", name="Claude", logo="", unread=0, tokens=1_106_086, lastUsed=now - 120e3, asOf=now - 300e3,
                 limits=[dict(label="5시간", used=63, resetsAt=now + 1.5 * 3600e3, window=300),
                         dict(label="주간", used=28, resetsAt=now + 4 * 86400e3, window=10080)]),
        ]

    @Property("QVariantList", notify=changed)
    def assistants(self):
        return [dict(i) for i in self._items]

    @Slot(str)
    def openApp(self, assistant_id):
        for item in self._items:
            if item["id"] == assistant_id:
                item["unread"] = 0
        self.changed.emit()


DEMO_APPS = [
    dict(name="Chrome", path="C:/Program Files/Google/Chrome/Application/chrome.exe"),
    dict(name="Discord", path="C:/Users/demo/AppData/Local/Discord/Update.exe"),
    dict(name="Spotify", path="C:/Users/demo/AppData/Roaming/Spotify/Spotify.exe"),
    dict(name="VS Code", path="C:/Program Files/Microsoft VS Code/Code.exe"),
    dict(name="Steam", path="C:/Program Files (x86)/Steam/steam.exe"),
    dict(name="문서", path="C:/Users/demo/Documents"),
]



def demo_events(devices: DemoDevices) -> QTimer:
    """Every 6 s an AirPods event, so the island shows: disconnect, connect, left bud low."""
    timer = QTimer()
    step = 0

    def tick():
        nonlocal step
        kind = step % 3
        if kind == 0:
            devices.data.update(connected=False, status="등록됨 · 미연결")
            devices.changed.emit()
        elif kind == 1:
            devices._batteries[0]["value"] = 80
            devices.batteriesChanged.emit()
            devices.connectDevice()
        else:
            devices._batteries[0]["value"] = 15
            devices.batteriesChanged.emit()
        step += 1

    timer.timeout.connect(tick)
    timer.start(6000)
    QTimer.singleShot(1000, tick)
    return timer
