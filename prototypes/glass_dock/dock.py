"""Glass dock: a column of glass cards on the right edge of the desktop.

Each card shows a summary and expands into its detail while hovered. The window
spans the dock column plus room for an expanded card, and its mask is kept to
the cards themselves so the rest of the window lets clicks through to the desktop.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Property, QObject, QPoint, QRectF, QSettings, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QFontDatabase, QIcon, QPainterPath, QRegion
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

BASE = Path(__file__).resolve().parent
PROTOTYPES = BASE.parent
PROJECT = PROTOTYPES.parent
CONCEPT = PROTOTYPES / "audio_widget_concepts"
for path in (CONCEPT, PROTOTYPES / "glass_audio_widget", PROJECT / "src", BASE):
    sys.path.insert(0, str(path))

from preview import LucianProvider  # noqa: E402
from launcher import AppIconProvider, LauncherBackend  # noqa: E402
from optical import IconMetrics  # noqa: E402

WINDOW_WIDTH = 340
EDGE_MARGIN = 12


class DockView(QQuickView):
    alwaysOnTopChanged = Signal()
    nativeGlassChanged = Signal()

    def __init__(self, audio, media, devices, launcher, *, always_on_top=False, preview_backdrop=False):
        super().__init__()
        self.setTitle("Glass Dock")
        self._always_on_top = always_on_top
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
        context.setContextProperty("previewBackdrop", preview_backdrop)
        self.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "GlassDock.qml")))
        if self.status() == QQuickView.Error:
            raise RuntimeError("\n".join(e.toString() for e in self.errors()))
        self.placeOnRightEdge()

    def _flags(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        return flags | (Qt.WindowStaysOnTopHint if self._always_on_top else Qt.WindowStaysOnBottomHint)

    def placeOnRightEdge(self):
        area = self.screen().availableGeometry()
        self.resize(WINDOW_WIDTH, area.height())
        self.setPosition(QPoint(area.right() - WINDOW_WIDTH + 1, area.top()))

    @Property(bool, notify=alwaysOnTopChanged)
    def alwaysOnTop(self):
        return self._always_on_top

    @Slot(bool)
    def setAlwaysOnTop(self, value):
        if value == self._always_on_top:
            return
        self._always_on_top = value
        visible = self.isVisible()
        self.setFlags(self._flags())
        if visible:
            self.show()
        self.alwaysOnTopChanged.emit()

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
        """Only the cards take input; the transparent rest of the window passes clicks through."""
        if not self._masking:
            return
        region = QRegion()
        for x, y, w, h, radius in rects:
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
            region = region.united(QRegion(path.toFillPolygon().toPolygon()))
        self.setMask(region)


def make_tray(view: DockView, app: QApplication) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(QIcon(str(PROJECT / "assets" / "app.ico")), app)
    tray.setToolTip("Glass Dock")
    menu = QMenu()
    on_top = QAction("항상 위에 표시", menu, checkable=True)
    on_top.setChecked(view.alwaysOnTop)
    on_top.toggled.connect(view.setAlwaysOnTop)
    quit_action = QAction("종료", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(on_top)
    menu.addSeparator()
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
    return AudioBackend(), MediaBackend(), DeviceBackend(), LauncherBackend()


def capture(view: DockView, app: QApplication, folder: Path) -> int:
    """Render the summary and each card's detail to PNGs for review."""
    folder.mkdir(parents=True, exist_ok=True)
    root = view.rootObject()
    states = ["", "airpods", "media", "volume", "output", "launcher"]

    def step(index=0):
        if index:
            name = states[index - 1] or "summary"
            view.grabWindow().save(str(folder / f"dock-{name}.png"))
        if index == len(states):
            app.quit()
            return
        root.setProperty("forcedCard", states[index])
        QTimer.singleShot(600, lambda: step(index + 1))

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
    view = DockView(audio, media, devices, launcher, always_on_top=args.on_top,
                    preview_backdrop=args.capture is not None)
    if args.capture is not None:
        view.resize(WINDOW_WIDTH + 40, 760)
        view.show()
        code = capture(view, app, args.capture)
        view.setSource(QUrl())  # release QML before the backends go away
        if view.qml_warnings:
            print("\n".join(view.qml_warnings), file=sys.stderr)
            return 1
        return code

    view.show()
    view.applyNativeGlass()
    tray = make_tray(view, app)
    for owner in (audio, media, devices):
        if hasattr(owner, "stop"):
            app.aboutToQuit.connect(owner.stop)
    app.aboutToQuit.connect(tray.hide)
    code = app.exec()
    view.setSource(QUrl())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
