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
                         pending=False, error="", status="", canPlay=True, canNext=True, canPrevious=True)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self.data)

    @Property("QVariantMap", notify=contentChanged)
    def content(self):
        return dict(self.data)

    @Slot(str, str, str)
    def command(self, action, token, identity):
        if action == "toggle":
            self.data["playing"] = not self.data["playing"]
            self.changed.emit()


class DemoDevices(QObject):
    changed = Signal()
    batteriesChanged = Signal()
    connectionHint = Signal()

    def __init__(self):
        super().__init__()
        self.data = dict(targetId="DEMO", name="AirPods Pro", paired=True, connected=True,
                         pending=False, error="", status="연결됨")
        self._batteries = [dict(label="L", value=80, charging=False, quality="fresh"),
                           dict(label="R", value=70, charging=False, quality="fresh"),
                           dict(label="CASE", value=60, charging=True, quality="fresh")]

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
