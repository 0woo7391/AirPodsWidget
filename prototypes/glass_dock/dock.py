"""Glass dock: a column of glass cards on the right edge of the desktop.

Each card shows a summary and expands into its detail while hovered; minimized,
the dock is a rail of icons that widens into labels. The window spans the dock
column plus room for an expanded card, and its mask is kept to the column so the
rest of the window lets clicks through to the desktop. AirPods events (connect,
disconnect, low battery) show as an island at the top of the chosen screen(s);
features.py carries the old widget's sound alert, ear detection, in-ear time,
game suppression and start with Windows.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import (Property, QObject, QPoint, QRect, QSettings, QStandardPaths, QTimer, QUrl, Qt,
                            Signal, Slot)
from PySide6.QtGui import QAction, QActionGroup, QColor, QCursor, QFontDatabase, QGuiApplication, QIcon, QRegion
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

BASE = Path(__file__).resolve().parent
PROTOTYPES = BASE.parent
PROJECT = PROTOTYPES.parent
if getattr(sys, "frozen", False):  # GlassDock.spec puts qml/ and assets/ at the bundle root
    BASE = PROJECT = Path(sys._MEIPASS)
CONCEPT = PROTOTYPES / "audio_widget_concepts"
for path in (CONCEPT, PROTOTYPES / "glass_audio_widget", PROJECT / "src", BASE):
    sys.path.insert(0, str(path))

from preview import LucianProvider  # noqa: E402
from launcher import AppIconProvider, LauncherBackend  # noqa: E402
from optical import IconMetrics  # noqa: E402
from features import DockFeatures  # noqa: E402

WINDOW_WIDTH = 340
EDGE_MARGIN = 12


def dock_settings() -> QSettings:
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    return QSettings(str(folder / "dock.ini"), QSettings.IniFormat)


def pref(settings: QSettings, key: str, default):
    return settings.value(key, default, type=type(default))


def screen_label(screen, index: int) -> str:
    size = screen.size()
    primary = " · 주 화면" if screen is QGuiApplication.primaryScreen() else ""
    return f"화면 {index + 1} ({size.width()}×{size.height()}){primary}"


def island_screens(choice: str) -> list:
    """Screens an island shows on: primary, secondary, all, or the one under the cursor."""
    primary = QGuiApplication.primaryScreen()
    screens = QGuiApplication.screens()
    if choice == "all":
        return list(screens)
    if choice == "secondary":
        others = [s for s in screens if s is not primary]
        return others[:1] or [primary]
    if choice == "cursor":
        return [QGuiApplication.screenAt(QCursor.pos()) or primary]
    return [primary]


class DockView(QQuickView):
    alwaysOnTopChanged = Signal()
    minimizedChanged = Signal()
    nativeGlassChanged = Signal()

    def __init__(self, audio, media, devices, launcher, features, settings: QSettings, *, always_on_top=False,
                 preview_backdrop=False):
        super().__init__()
        self.setTitle("Glass Dock")
        self.settings = settings
        self._always_on_top = always_on_top or pref(settings, "dock/alwaysOnTop", False)
        self._minimized = pref(settings, "dock/minimized", False) and not preview_backdrop
        self._native_glass = False
        self._masking = not preview_backdrop
        self.setFlags(self._flags())
        surface = self.format()
        surface.setAlphaBufferSize(8)
        self.setFormat(surface)
        self.setColor(QColor(Qt.transparent))
        self.setResizeMode(QQuickView.SizeRootObjectToView)

        # Pretendard static weights, as in the main app; the variable SUIT build renders too light.
        family = ""
        for weight in ("Regular", "Medium", "SemiBold"):
            font_id = QFontDatabase.addApplicationFont(str(PROJECT / "assets" / "fonts" / f"Pretendard-{weight}.otf"))
            if font_id >= 0 and not family:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.icons = LucianProvider()
        self.metrics = IconMetrics(self.icons, self)
        self.engine().addImageProvider("lucian", self.icons)
        self.engine().addImageProvider("appicon", AppIconProvider(launcher))
        self.qml_warnings: list[str] = []
        self.engine().warnings.connect(lambda issues: self.qml_warnings.extend(i.toString() for i in issues))
        context = self.rootContext()
        context.setContextProperty("dockFont", family)
        context.setContextProperty("dockHost", self)
        context.setContextProperty("iconMetrics", self.metrics)
        context.setContextProperty("outputBackend", audio)
        context.setContextProperty("mediaBackend", media)
        context.setContextProperty("deviceBackend", devices)
        context.setContextProperty("launcherBackend", launcher)
        context.setContextProperty("dockFeatures", features)
        context.setContextProperty("previewBackdrop", preview_backdrop)
        self.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "GlassDock.qml")))
        if self.status() == QQuickView.Error:
            raise RuntimeError("\n".join(e.toString() for e in self.errors()))
        self.placeOnRightEdge()

    def _flags(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        return flags | (Qt.WindowStaysOnTopHint if self._always_on_top else Qt.WindowStaysOnBottomHint)

    def targetScreen(self):
        name = pref(self.settings, "dock/screen", "primary")
        for screen in QGuiApplication.screens():
            if screen.name() == name:
                return screen
        return QGuiApplication.primaryScreen()

    @Slot()
    def placeOnRightEdge(self):
        """Full height on the right edge of the chosen screen; follows taskbar and resolution changes."""
        screen = self.targetScreen()
        if self.screen() is not screen:
            self.setScreen(screen)
        area = screen.availableGeometry()
        self.resize(WINDOW_WIDTH, area.height())
        self.setPosition(QPoint(area.right() - WINDOW_WIDTH + 1, area.top()))

    def followScreens(self, app: QGuiApplication):
        def watch(screen):
            screen.availableGeometryChanged.connect(self.placeOnRightEdge)
        for screen in app.screens():
            watch(screen)
        app.screenAdded.connect(watch)
        app.screenAdded.connect(self.placeOnRightEdge)
        app.screenRemoved.connect(lambda _screen: QTimer.singleShot(0, self.placeOnRightEdge))
        app.primaryScreenChanged.connect(self.placeOnRightEdge)

    @Property(bool, notify=alwaysOnTopChanged)
    def alwaysOnTop(self):
        return self._always_on_top

    @Slot(bool)
    def setAlwaysOnTop(self, value):
        if value == self._always_on_top:
            return
        self._always_on_top = value
        self.settings.setValue("dock/alwaysOnTop", value)
        visible = self.isVisible()
        self.setFlags(self._flags())
        if visible:
            self.show()
        self.alwaysOnTopChanged.emit()

    @Property(bool, notify=minimizedChanged)
    def minimized(self):
        return self._minimized

    @Slot(bool)
    def setMinimized(self, value):
        if value == self._minimized:
            return
        self._minimized = value
        self.settings.setValue("dock/minimized", value)
        self.minimizedChanged.emit()

    @Property(bool, notify=nativeGlassChanged)
    def nativeGlass(self):
        return self._native_glass

    def applyNativeGlass(self):
        """Windows 11 Acrylic behind the cards; QML keeps a tinted fallback elsewhere."""
        if os.name != "nt":
            return
        try:
            from services.windows_material import _apply_dwm_backdrop
            self._native_glass = _apply_dwm_backdrop(int(self.winId()), True)
        except Exception:
            self._native_glass = False
        self.nativeGlassChanged.emit()

    @Slot("QVariantList")
    def updateMask(self, rects):
        """Only the dock column (and a grown card) takes input; the rest passes clicks through.

        Plain rectangles with an outset: a rounded polygon mask is a hard window
        region on Windows and cuts the cards' antialiased rims into stairs.
        """
        if not self._masking:
            return
        region = QRegion()
        for x, y, w, h in rects:
            region = region.united(QRegion(QRect(int(x), int(y), int(round(w)) + 1, int(round(h)) + 1)))
        self.setMask(region)


class IslandView(QQuickView):
    """One island window on one screen: above everything, never taking input."""

    def __init__(self, dock: DockView):
        super().__init__(dock.engine(), None)  # shares fonts, icon providers and context properties
        self.setTitle("Glass Dock Island")
        self.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
                      | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        surface = self.format()
        surface.setAlphaBufferSize(8)
        self.setFormat(surface)
        self.setColor(QColor(Qt.transparent))
        self.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "Island.qml")))
        if self.status() == QQuickView.Error:
            raise RuntimeError("\n".join(e.toString() for e in self.errors()))
        self.rootObject().finished.connect(self.hide)

    def place(self, screen, align: str, offset: int):
        if self.screen() is not screen:
            self.setScreen(screen)
        area = screen.availableGeometry()
        if align == "left":
            x = area.left() + 16
        elif align == "right":
            x = area.right() + 1 - self.width() - 16
        else:
            x = area.center().x() - self.width() // 2
        self.setPosition(QPoint(x, area.top() + offset))

    def notify(self, title, subtitle, tone, batteries):
        self.show()
        self.rootObject().show(title, subtitle, tone, batteries)


class IslandHub(QObject):
    """Shows an island on the screens the settings choose, one window per screen."""

    def __init__(self, dock: DockView, settings: QSettings):
        super().__init__(dock)
        self.dock = dock
        self.settings = settings
        self.views: dict = {}
        QGuiApplication.instance().screenRemoved.connect(self._drop)

    def _drop(self, screen):
        view = self.views.pop(screen, None)
        if view is not None:
            view.hide()
            view.setSource(QUrl())
            view.deleteLater()

    def notify(self, title, subtitle, tone, batteries=None):
        align = pref(self.settings, "island/align", "center")
        offset = pref(self.settings, "island/offset", 0)
        for screen in island_screens(pref(self.settings, "island/screens", "primary")):
            view = self.views.get(screen)
            if view is None:
                view = self.views[screen] = IslandView(self.dock)
            view.place(screen, align, offset)
            view.notify(title, subtitle, tone, batteries or [])

    def close(self):
        for view in self.views.values():
            view.setSource(QUrl())


def make_tray(view: DockView, hub: IslandHub, features: DockFeatures, settings: QSettings, devices,
              app: QApplication) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(QIcon(str(PROJECT / "assets" / "app.ico")), app)
    tray.setToolTip("Glass Dock")
    menu = QMenu()

    on_top = QAction("항상 위에 표시", menu, checkable=True)
    on_top.setChecked(view.alwaysOnTop)
    on_top.toggled.connect(view.setAlwaysOnTop)
    menu.addAction(on_top)
    minimized = QAction("최소화 (레일)", menu, checkable=True)
    minimized.setChecked(view.minimized)
    minimized.toggled.connect(view.setMinimized)
    menu.addAction(minimized)

    def choices(parent: QMenu, title: str, key: str, default, options, changed=None):
        sub = parent.addMenu(title)

        def fill():
            sub.clear()
            group = QActionGroup(sub)
            current = pref(settings, key, default)
            for value, label in (options() if callable(options) else options):
                action = sub.addAction(label)
                action.setCheckable(True)
                action.setChecked(value == current)
                group.addAction(action)
                action.triggered.connect(lambda _=False, v=value: (settings.setValue(key, v), changed and changed()))

        sub.aboutToShow.connect(fill)  # screens come and go, so the list is built on open
        fill()
        return sub

    def screen_options():
        return [("primary", "주 화면")] + [(s.name(), screen_label(s, i)) for i, s in enumerate(QGuiApplication.screens())]

    choices(menu, "Dock 화면", "dock/screen", "primary", screen_options, view.placeOnRightEdge)

    if hasattr(devices, "selectDevice"):
        target = menu.addMenu("AirPods 기기")

        def fill_devices():
            target.clear()
            group = QActionGroup(target)
            current = devices.state.get("targetId", "")
            for device in devices.devices:
                action = target.addAction(device.get("name") or device.get("id"))
                action.setCheckable(True)
                action.setChecked(device.get("id") == current)
                group.addAction(action)
                action.triggered.connect(lambda _=False, key=device.get("id"): devices.selectDevice(key))
            if not devices.devices:
                target.addAction("페어링된 기기 없음").setEnabled(False)

        target.aboutToShow.connect(fill_devices)
        fill_devices()

        # Battery advertisements nearby; at most two of the same model can be bound (glass widget rule).
        sources = menu.addMenu("배터리 출처")

        def fill_sources():
            sources.clear()
            bound = list(devices.batterySources)
            for item in devices.candidates:
                address = item.get("address")
                action = sources.addAction(f"{item.get('name') or '?'} · {address}")
                action.setCheckable(True)
                action.setChecked(address in bound)

                def toggle(checked, address=address):
                    chosen = [a for a in devices.batterySources if a != address] + ([address] if checked else [])
                    devices.bindSources(chosen)
                action.toggled.connect(toggle)
            if not devices.candidates:
                sources.addAction("케이스를 열고 잠시 기다리세요").setEnabled(False)
            sources.addSeparator()
            sources.addAction("초기화").triggered.connect(lambda: devices.bindSources([]))

        sources.aboutToShow.connect(fill_sources)
        fill_sources()

    island = menu.addMenu("아일랜드 알림")
    choices(island, "표시 화면", "island/screens", "primary",
            [("primary", "주 화면"), ("secondary", "보조 화면"), ("all", "모든 화면"), ("cursor", "마우스가 있는 화면")])
    choices(island, "위치", "island/align", "center", [("center", "가운데"), ("left", "왼쪽"), ("right", "오른쪽")])
    choices(island, "위쪽 여백", "island/offset", 0, [(0, "0 px"), (8, "8 px"), (16, "16 px"), (32, "32 px")])
    island.addSeparator()
    def toggle(parent: QMenu, key: str, label: str):
        action = QAction(label, parent, checkable=True)
        action.setChecked(features.get(key))
        action.toggled.connect(lambda value: features.set(key, value))
        parent.addAction(action)

    for key, label in (("island/connect", "연결"), ("island/disconnect", "연결 해제"),
                       ("island/lowBattery", "배터리 부족"), ("island/suppressDuringGames", "게임 중 숨기기")):
        toggle(island, key, label)
    island.addSeparator()
    preview = island.addAction("미리 보기")
    preview.triggered.connect(lambda: hub.notify(devices.state.get("name") or "AirPods", "연결됨", "connected",
                                                 list(devices.batteries)))

    battery = menu.addMenu("배터리 경고")
    choices(battery, "기준", "battery/threshold", 20, [(10, "10%"), (15, "15%"), (20, "20%"), (30, "30%")])
    toggle(battery, "battery/sound", "경고음")
    choices(battery, "경고음 크기", "battery/soundVolume", 60, [(30, "30%"), (60, "60%"), (100, "100%")])
    toggle(battery, "battery/soundDuringGames", "게임 중에도 경고음")
    battery.addAction("경고음 미리 듣기").triggered.connect(features.play_alert)

    media = menu.addMenu("미디어")
    toggle(media, "media/followAny", "재생 중인 아무 앱이나 따라가기")
    media.addSeparator()
    toggle(media, "media/autoPause", "귀에서 빼면 일시정지")
    toggle(media, "media/autoResume", "다시 끼면 재생")

    toggle(menu, "system/startWithWindows", "Windows 시작 시 실행")

    menu.addSeparator()
    quit_action = QAction("종료", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray._menu = menu  # keep the menu alive with the tray
    tray.show()
    return tray


def demo_backends():
    from demo_backends import DEMO_APPS, DemoAudio, DemoDevices, DemoMedia
    import json
    folder = tempfile.mkdtemp(prefix="glass-dock-demo-")
    settings = QSettings(str(Path(folder) / "launcher.ini"), QSettings.IniFormat)
    settings.setValue("launcher/apps", json.dumps(DEMO_APPS, ensure_ascii=False))
    return DemoAudio(), DemoMedia(), DemoDevices(), LauncherBackend(settings)


def real_backends():
    from audio_backend import AudioBackend
    from media_backend import MediaBackend
    from device_backend import DeviceBackend
    # Reuse the glass widget's saved AirPods, battery sources, output and media choices.
    shared = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)).parent / "GlassAudioWidget"

    def ini(name):
        return QSettings(str(shared / name), QSettings.IniFormat)
    return (AudioBackend(settings=ini("output.ini")), MediaBackend(settings=ini("media.ini")),
            DeviceBackend(settings=ini("devices.ini"), auto_sources=True), LauncherBackend())


def capture(view: DockView, hub: IslandHub, devices, app: QApplication, folder: Path) -> int:
    """Render dock states (bento, rail, magnified, details) and island moments to PNGs."""
    folder.mkdir(parents=True, exist_ok=True)
    root = view.rootObject()
    # (file name, forcedCard, minimized, forcedPointerY, forcedRailOpen)
    states = [("summary", "", False, -1, -1), ("magnify-media", "", False, 330, -1),
              ("airpods", "airpods", False, -1, -1), ("media", "media", False, -1, -1),
              ("volume", "volume", False, -1, -1), ("output", "output", False, -1, -1),
              ("rail", "", True, -1, 0), ("rail-open", "", True, 300, 1), ("rail-airpods", "airpods", True, -1, 0)]
    moments = [0.05, 0.3, 1.5, 3.5]
    tones = [("connected", "연결됨"), ("low", "배터리 부족 · 왼쪽 15%"), ("disconnected", "연결 해제됨")]
    shots = [(tone, sub, m) for tone, sub in tones for m in moments]
    hub.notify("AirPods Pro", "연결됨", "connected", list(devices.batteries))
    island = next(iter(hub.views.values()))
    island_root = island.rootObject()

    def step(index=0):
        if index:
            view.grabWindow().save(str(folder / f"dock-{states[index - 1][0]}.png"))
        if index == len(states):
            QTimer.singleShot(300, island_step)
            return
        _, card, rail, pointer_y, rail_open = states[index]
        view.setMinimized(rail)
        root.setProperty("forcedCard", card)
        root.setProperty("forcedPointerY", pointer_y)
        root.setProperty("forcedRailOpen", rail_open)
        QTimer.singleShot(900, lambda: step(index + 1))

    def island_step(index=0):
        if index:
            tone, _, moment = shots[index - 1]
            island.grabWindow().save(str(folder / f"island-{tone}-{moment:.2f}s.png"))
        if index == len(shots):
            app.quit()
            return
        tone, sub, moment = shots[index]
        island_root.show("AirPods Pro", sub, tone, [] if tone == "disconnected" else list(devices.batteries))
        island_root.setProperty("forcedTime", moment)
        QTimer.singleShot(200, lambda: island_step(index + 1))

    QTimer.singleShot(400, step)
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Sample data instead of the real devices.")
    parser.add_argument("--capture", type=Path, help="Write preview PNGs to this folder and exit (implies --demo).")
    parser.add_argument("--on-top", action="store_true", help="Keep the dock above other windows.")
    args = parser.parse_args()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("GlassDock")
    app.setQuitOnLastWindowClosed(False)
    QQuickStyle.setStyle("Basic")

    demo = args.demo or args.capture is not None
    audio, media, devices, launcher = demo_backends() if demo else real_backends()
    previewing = args.capture is not None
    # Previews must not read or change the user's dock settings.
    settings = QSettings(str(Path(tempfile.mkdtemp(prefix="glass-dock-capture-")) / "dock.ini"),
                         QSettings.IniFormat) if previewing else dock_settings()
    # Sample data must not count towards the real in-ear time.
    usage_path = Path(tempfile.mkdtemp(prefix="glass-dock-usage-")) / "usage.json" if demo else None
    features = DockFeatures(devices, media, settings, PROJECT / "assets" / "low_power_warning.mp3",
                            usage_path=usage_path)
    view = DockView(audio, media, devices, launcher, features, settings, always_on_top=args.on_top,
                    preview_backdrop=previewing)
    hub = IslandHub(view, settings)
    features.notice.connect(hub.notify)
    if previewing:
        view.resize(WINDOW_WIDTH + 40, 760)
        view.show()
        code = capture(view, hub, devices, app, args.capture)
        hub.close()
        view.setSource(QUrl())  # release QML before the backends go away
        if view.qml_warnings:
            print("\n".join(view.qml_warnings), file=sys.stderr)
            return 1
        return code

    view.show()
    view.applyNativeGlass()
    view.followScreens(app)
    features.apply_startup()
    if demo:
        from demo_backends import demo_events
        demo_timer = demo_events(devices)  # noqa: F841 - kept alive for the app's lifetime
    tray = make_tray(view, hub, features, settings, devices, app)
    for owner in (audio, media, devices):
        if hasattr(owner, "stop"):
            app.aboutToQuit.connect(owner.stop)
    app.aboutToQuit.connect(tray.hide)
    app.aboutToQuit.connect(features.save)
    code = app.exec()
    hub.close()
    view.setSource(QUrl())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
