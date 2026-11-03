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
import ctypes
import math
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import (Property, QObject, QPoint, QRect, QSettings, QSize, QStandardPaths, QTimer, QUrl, Qt,
                            Signal, Slot)
from PySide6.QtGui import QAction, QColor, QCursor, QFontDatabase, QGuiApplication, QIcon, QRegion
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
from prefs import DockPrefs, screens_in_order  # noqa: E402

WINDOW_WIDTH = 580   # dock column plus the flyout beside it
EDGE_MARGIN = 12
# shortcut: where Explorer starts its icon grid on each monitor, measured here at 100 % with
# medium icons (first icon at +11, +2). Read real icon positions (LVM_GETITEMPOSITION) if the
# dock stops lining up with icons on other setups.
DESKTOP_GRID_OFFSET = (11, 2)


def desktop_icon_cell(screen):
    """The desktop icon grid cell (width, height) in logical px, or None without a desktop."""
    if os.name != "nt":
        return None
    user32 = ctypes.WinDLL("user32")
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.FindWindowExW.restype = ctypes.c_void_p
    user32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p]
    view = user32.FindWindowExW(user32.FindWindowExW(None, None, "Progman", None), None, "SHELLDLL_DefView", None)
    worker = None
    while not view:  # with a wallpaper slideshow the icons live under a WorkerW
        worker = user32.FindWindowExW(None, worker, "WorkerW", None)
        if not worker:
            return None
        view = user32.FindWindowExW(worker, None, "SHELLDLL_DefView", None)
    listview = user32.FindWindowExW(view, None, "SysListView32", None)
    spacing = user32.SendMessageW(listview, 0x1033, 0, 0) if listview else 0   # LVM_GETITEMSPACING
    width, height = spacing & 0xFFFF, (spacing >> 16) & 0xFFFF
    if not width or not height:
        return None
    ratio = screen.devicePixelRatio()
    return width / ratio, height / ratio


def dock_settings() -> QSettings:
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    return QSettings(str(folder / "dock.ini"), QSettings.IniFormat)


def load_fonts() -> str:
    """Pretendard static weights, as in the main app; the variable SUIT build renders too light."""
    family = ""
    for weight in ("Regular", "Medium", "SemiBold"):
        font_id = QFontDatabase.addApplicationFont(str(PROJECT / "assets" / "fonts" / f"Pretendard-{weight}.otf"))
        if font_id >= 0 and not family:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
    return family


class DockView(QQuickView):
    alwaysOnTopChanged = Signal()
    minimizedChanged = Signal()
    edgeChanged = Signal()
    gridChanged = Signal()
    nativeGlassChanged = Signal()

    def __init__(self, audio, media, devices, launcher, features, prefs: DockPrefs, *, always_on_top=False,
                 preview_backdrop=False):
        super().__init__()
        self.setTitle("Glass Dock")
        self.prefs = prefs
        self._force_on_top = always_on_top
        self._native_glass = False
        self._grid = {}
        self._masking = not preview_backdrop
        self.setFlags(self._flags())
        surface = self.format()
        surface.setAlphaBufferSize(8)
        self.setFormat(surface)
        self.setColor(QColor(Qt.transparent))
        self.setResizeMode(QQuickView.SizeRootObjectToView)

        self.icons = LucianProvider()
        self.metrics = IconMetrics(self.icons, self)
        self.engine().addImageProvider("lucian", self.icons)
        self.engine().addImageProvider("appicon", AppIconProvider(launcher))
        self.qml_warnings: list[str] = []
        self.engine().warnings.connect(lambda issues: self.qml_warnings.extend(i.toString() for i in issues))
        context = self.rootContext()
        context.setContextProperty("dockFont", load_fonts())
        context.setContextProperty("dockHost", self)
        context.setContextProperty("dockPrefs", prefs)
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
        prefs.changed.connect(self._on_pref)
        prefs.screensChanged.connect(lambda: QTimer.singleShot(0, self.place))
        self.place()

    def _flags(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        return flags | (Qt.WindowStaysOnTopHint if self.alwaysOnTop else Qt.WindowStaysOnBottomHint)

    def _on_pref(self, key):
        if key == "dock/alwaysOnTop":
            visible = self.isVisible()
            self.setFlags(self._flags())
            if visible:
                self.show()
            self.alwaysOnTopChanged.emit()
        elif key == "dock/minimized":
            self.minimizedChanged.emit()
        elif key in ("dock/screen", "dock/edge", "dock/grid", "dock/columns"):
            self.edgeChanged.emit()
            self.place()

    @Slot()
    def place(self):
        """Full height on the chosen edge of the chosen screen; follows taskbar and resolution changes."""
        screen = self.prefs.dock_screen()
        if self.screen() is not screen:
            self.setScreen(screen)
        area = screen.availableGeometry()
        self.resize(WINDOW_WIDTH, area.height())
        x = area.left() if self.edge == "left" else area.right() - WINDOW_WIDTH + 1
        self.setPosition(QPoint(x, area.top()))
        grid = self._desktop_grid(screen, x, area)
        if grid != self._grid:
            self._grid = grid
            self.gridChanged.emit()

    def _desktop_grid(self, screen, window_x, area) -> dict:
        """The block of desktop icon cells the dock fills, in window coordinates; {} when off."""
        cell = desktop_icon_cell(screen) if self.prefs.get("dock/grid") else None
        if cell is None:
            return {}
        cell_w, cell_h = cell
        geo = screen.geometry()
        origin_x, origin_y = geo.left() + DESKTOP_GRID_OFFSET[0], geo.top() + DESKTOP_GRID_OFFSET[1]
        columns = self.prefs.get("dock/columns")
        total = int((geo.width() - DESKTOP_GRID_OFFSET[0]) // cell_w)
        first = 0 if self.edge == "left" else max(0, total - columns)
        # Rows wholly inside the work area (below a top taskbar, above a bottom one).
        first_row = max(0, math.ceil((area.top() - origin_y) / cell_h))
        top = origin_y + first_row * cell_h
        return dict(cellW=cell_w, cellH=cell_h, x=origin_x + first * cell_w - window_x, y=top - area.top(),
                    width=columns * cell_w, rows=int((area.bottom() + 1 - top) // cell_h))

    @Property("QVariantMap", notify=gridChanged)
    def grid(self):
        return self._grid

    def followScreens(self, app: QGuiApplication):
        def watch(screen):
            screen.availableGeometryChanged.connect(self.place)
        for screen in app.screens():
            watch(screen)
        app.screenAdded.connect(watch)

    @Property(bool, notify=alwaysOnTopChanged)
    def alwaysOnTop(self):
        return self._force_on_top or self.prefs.get("dock/alwaysOnTop")

    @Slot(bool)
    def setAlwaysOnTop(self, value):
        self.prefs.set("dock/alwaysOnTop", value)

    @Property(bool, notify=minimizedChanged)
    def minimized(self):
        return self.prefs.get("dock/minimized")

    @Slot(bool)
    def setMinimized(self, value):
        self.prefs.set("dock/minimized", value)

    @Property(str, notify=edgeChanged)
    def edge(self):
        return self.prefs.get("dock/edge")

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

    @Slot(result="QPointF")
    def cursorPos(self):
        """The pointer in window coordinates, wherever it is (hover events can be missed)."""
        return self.mapFromGlobal(QCursor.pos()).toPointF()

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


def overlay_window(dock: DockView, qml: str) -> QQuickView:
    """A frameless, transparent, topmost window on the dock's QML engine that never takes input."""
    view = QQuickView(dock.engine(), None)  # shares fonts, icon providers and context properties
    view.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint | Qt.WindowStaysOnTopHint
                  | Qt.WindowTransparentForInput)
    surface = view.format()
    surface.setAlphaBufferSize(8)
    view.setFormat(surface)
    view.setColor(QColor(Qt.transparent))
    view.setSource(QUrl.fromLocalFile(str(BASE / "qml" / qml)))
    if view.status() == QQuickView.Error:
        raise RuntimeError("\n".join(e.toString() for e in view.errors()))
    return view


class IslandView:
    """One island window on one screen."""

    def __init__(self, dock: DockView):
        self.view = overlay_window(dock, "Island.qml")
        self.view.setTitle("Glass Dock Island")
        self.view.rootObject().finished.connect(self.view.hide)

    def place(self, screen, align: str, offset: int):
        view = self.view
        if view.screen() is not screen:
            view.setScreen(screen)
        area = screen.availableGeometry()
        if align == "left":
            x = area.left() + 16
        elif align == "right":
            x = area.right() + 1 - view.width() - 16
        else:
            x = area.center().x() - view.width() // 2
        view.setPosition(QPoint(x, area.top() + offset))

    def notify(self, title, subtitle, tone, batteries):
        self.view.show()
        self.view.rootObject().show(title, subtitle, tone, batteries)


class IslandHub(QObject):
    """Shows an island on the screens the settings choose, one window per screen."""

    def __init__(self, dock: DockView, prefs: DockPrefs):
        super().__init__(dock)
        self.dock = dock
        self.prefs = prefs
        self.views: dict = {}
        QGuiApplication.instance().screenRemoved.connect(self._drop)

    def _drop(self, screen):
        island = self.views.pop(screen, None)
        if island is not None:
            island.view.hide()
            island.view.setSource(QUrl())
            island.view.deleteLater()

    def notify(self, title, subtitle, tone, batteries=None):
        align = self.prefs.get("island/align")
        offset = self.prefs.get("island/offset")
        for screen in self.prefs.island_screens():
            island = self.views.get(screen)
            if island is None:
                island = self.views[screen] = IslandView(self.dock)
            island.place(screen, align, offset)
            island.notify(title, subtitle, tone, batteries or [])

    def close(self):
        for island in self.views.values():
            island.view.setSource(QUrl())


class DockActions(QObject):
    """What the settings window can ask for besides changing a value."""

    def __init__(self, dock: DockView, hub: IslandHub, features: DockFeatures, devices, app: QApplication):
        super().__init__(dock)
        self.dock, self.hub, self.features, self.devices, self.app = dock, hub, features, devices, app
        self._identify: list[QQuickView] = []

    @Slot()
    def identifyScreens(self):
        """A big number on every screen for three seconds, matching the map in the settings."""
        for view in self._identify:
            view.hide()
            view.setSource(QUrl())
            view.deleteLater()
        self._identify = []
        for info, screen in zip(self.dock.prefs.screens, screens_in_order()):
            view = overlay_window(self.dock, "Identify.qml")
            view.setScreen(screen)
            root = view.rootObject()
            root.setProperty("number", info["number"])
            root.setProperty("label", info["model"] + (" · 주 화면" if info["primary"] else ""))
            area = screen.geometry()
            view.setPosition(QPoint(area.center().x() - view.width() // 2, area.center().y() - view.height() // 2))
            view.show()
            self._identify.append(view)
        QTimer.singleShot(3000, lambda: [view.hide() for view in self._identify])

    @Slot()
    def previewIsland(self):
        self.hub.notify(self.devices.state.get("name") or "AirPods", "연결됨", "connected",
                        list(self.devices.batteries))

    @Slot()
    def playAlert(self):
        self.features.play_alert()

    @Slot()
    def quit(self):
        self.app.quit()


class SettingsView(QQuickView):
    """The settings window: an ordinary window in the taskbar, built on the dock's engine."""

    def __init__(self, dock: DockView, actions: DockActions):
        super().__init__(dock.engine(), None)
        self.setTitle("Glass Dock 설정")
        self.setIcon(QIcon(str(PROJECT / "assets" / "app.ico")))
        self.setColor(QColor("#141418"))
        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.rootContext().setContextProperty("dockActions", actions)
        self.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "Settings.qml")))
        if self.status() == QQuickView.Error:
            raise RuntimeError("\n".join(e.toString() for e in self.errors()))
        self.resize(860, 640)
        self.setMinimumSize(QSize(760, 540))

    def open(self, page: str = ""):
        if page:
            self.rootObject().setProperty("page", page)
        if not self.isVisible():
            area = QGuiApplication.primaryScreen().availableGeometry()
            self.setPosition(area.center().x() - self.width() // 2, area.center().y() - self.height() // 2)
        self.show()
        self.raise_()
        self.requestActivate()


def make_tray(view: DockView, settings_view: SettingsView, actions: DockActions, prefs: DockPrefs,
              app: QApplication) -> QSystemTrayIcon:
    """Left click opens the settings; the menu keeps only the quick switches."""
    tray = QSystemTrayIcon(QIcon(str(PROJECT / "assets" / "app.ico")), app)
    tray.setToolTip("Glass Dock")
    menu = QMenu()
    menu.addAction("설정 열기").triggered.connect(lambda: settings_view.open())
    menu.addSeparator()
    switches = []
    for key, label in (("dock/minimized", "레일로 최소화"), ("dock/alwaysOnTop", "항상 위에 표시")):
        action = QAction(label, menu, checkable=True)
        action.setChecked(prefs.get(key))
        action.toggled.connect(lambda value, k=key: prefs.set(k, value))
        menu.addAction(action)
        switches.append((key, action))
    prefs.changed.connect(lambda key: [a.setChecked(prefs.get(k)) for k, a in switches if k == key])
    menu.addAction("아일랜드 미리 보기").triggered.connect(actions.previewIsland)
    menu.addSeparator()
    menu.addAction("종료").triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: settings_view.open() if reason == QSystemTrayIcon.Trigger else None)
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


def capture(view: DockView, hub: IslandHub, settings_view: SettingsView, prefs: DockPrefs, devices,
            app: QApplication, folder: Path) -> int:
    """Render dock states, settings pages and island moments to PNGs for review."""
    folder.mkdir(parents=True, exist_ok=True)
    root = view.rootObject()
    # (file name, forcedCard, minimized, forcedPointerY, forcedRailOpen, edge)
    states = [("summary", "", False, -1, -1, "right"), ("magnify-media", "", False, 330, -1, "right"),
              ("airpods", "airpods", False, -1, -1, "right"), ("media", "media", False, -1, -1, "right"),
              ("volume", "volume", False, -1, -1, "right"), ("output", "output", False, -1, -1, "right"),
              ("rail", "", True, -1, 0, "right"), ("rail-open", "", True, 300, 1, "right"),
              ("rail-airpods", "airpods", True, -1, 0, "right"),
              ("left-summary", "", False, -1, -1, "left"), ("left-media", "media", False, -1, -1, "left"),
              ("left-rail-open", "", True, 300, 1, "left"), ("raised-media", "media", False, -1, -1, "right")]
    pages = ["screen", "modules", "island", "airpods", "media", "general"]
    moments = [0.05, 0.3, 1.5, 3.5]
    tones = [("connected", "연결됨"), ("low", "배터리 부족 · 왼쪽 15%"), ("disconnected", "연결 해제됨")]
    shots = [(tone, sub, m) for tone, sub in tones for m in moments]
    hub.notify("AirPods Pro", "연결됨", "connected", list(devices.batteries))
    island = next(iter(hub.views.values())).view
    island_root = island.rootObject()

    def step(index=0):
        if index:
            view.grabWindow().save(str(folder / f"dock-{states[index - 1][0]}.png"))
        if index == len(states):
            prefs.set("dock/edge", "right")
            settings_view.show()
            QTimer.singleShot(400, page_step)
            return
        _, card, rail, pointer_y, rail_open, edge = states[index]
        prefs.set("dock/edge", edge)
        prefs.set("dock/position", 0.2 if states[index][0].startswith("raised") else 0.5)
        view.resize(WINDOW_WIDTH + 40, 760)
        view.setMinimized(rail)
        root.setProperty("forcedCard", card)
        root.setProperty("forcedPointerY", pointer_y)
        root.setProperty("forcedRailOpen", rail_open)
        QTimer.singleShot(900, lambda: step(index + 1))

    def page_step(index=0):
        if index:
            settings_view.grabWindow().save(str(folder / f"settings-{pages[index - 1]}.png"))
        if index == len(pages):
            settings_view.hide()
            QTimer.singleShot(300, island_step)
            return
        settings_view.rootObject().setProperty("page", pages[index])
        QTimer.singleShot(400, lambda: page_step(index + 1))

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
    prefs = DockPrefs(QSettings(str(Path(tempfile.mkdtemp(prefix="glass-dock-capture-")) / "dock.ini"),
                                QSettings.IniFormat) if previewing else dock_settings())
    # Sample data must not count towards the real in-ear time.
    usage_path = Path(tempfile.mkdtemp(prefix="glass-dock-usage-")) / "usage.json" if demo else None
    features = DockFeatures(devices, media, prefs, PROJECT / "assets" / "low_power_warning.mp3",
                            usage_path=usage_path)
    view = DockView(audio, media, devices, launcher, features, prefs, always_on_top=args.on_top,
                    preview_backdrop=previewing)
    hub = IslandHub(view, prefs)
    features.notice.connect(hub.notify)
    actions = DockActions(view, hub, features, devices, app)
    settings_view = SettingsView(view, actions)
    if previewing:
        view.resize(WINDOW_WIDTH + 40, 760)
        view.show()
        code = capture(view, hub, settings_view, prefs, devices, app, args.capture)
        hub.close()
        settings_view.setSource(QUrl())
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
    tray = make_tray(view, settings_view, actions, prefs, app)
    for owner in (audio, media, devices):
        if hasattr(owner, "stop"):
            app.aboutToQuit.connect(owner.stop)
    app.aboutToQuit.connect(tray.hide)
    app.aboutToQuit.connect(features.save)
    code = app.exec()
    hub.close()
    settings_view.setSource(QUrl())
    view.setSource(QUrl())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
