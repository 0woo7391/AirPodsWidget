from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, QMetaObject, QSettings, QStandardPaths, QTimer, Property, Signal, Slot, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainterPath, QRegion, QWindow
from PySide6.QtQuick import QQuickView, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from preview import load_scene


def fit_position(position, size, area):
    right = area.right() - size.width() + 1
    bottom = area.bottom() - size.height() + 1
    return QPoint(max(area.left(), min(position.x(), right)) if size.width() <= area.width() else right,
                  max(area.top(), min(position.y(), bottom)))


class WidgetView(QQuickView):
    """One frameless card; native services are optional for isolated tests."""

    alwaysOnTopChanged = Signal()
    windowPreferenceErrorChanged = Signal()
    trayModeChanged = Signal()
    quitRequested = Signal()

    def __init__(self, design: str, compact: bool = False, audio_backend=None, window_settings=None, media_backend=None,
                 *, scene_file="DesktopWidget.qml", expanded_height=None, surface_radius=None):
        super().__init__()
        self.expanded_height = expanded_height or (474 if design == "paper" else 448)
        self._surface_radius = surface_radius
        self.setTitle(f"Audio Widget — {design} · " +
                      ("시스템 출력" if audio_backend is not None else "예시 데이터"))
        self.window_settings = window_settings if window_settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "window.ini"),
            QSettings.IniFormat)
        self._window_error = ""
        self._preference_errors = {}
        self._tray_mode = False
        self._suppress_position = False
        self._placement_key = f"window/placement/{design}"
        self._last_placement = self._saved_placement = None
        self._position_timer = QTimer(self)
        self._position_timer.setSingleShot(True)
        self._position_timer.setInterval(250)
        self._position_timer.timeout.connect(self.flushPlacement)
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.window_settings.value("window/always_on_top", True, type=bool):
            flags |= Qt.WindowStaysOnTopHint
        self.setFlags(flags)
        self.flagsChanged.connect(lambda _: self.alwaysOnTopChanged.emit())
        surface_format = self.format()
        surface_format.setAlphaBufferSize(8)
        self.setFormat(surface_format)
        self.setColor(QColor(Qt.transparent))
        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.rootContext().setContextProperty("widgetHost", self)
        self.rootContext().setContextProperty("initialCompact", compact)
        self.icons, self.qml_warnings = self.loadScene(design, scene_file, audio_backend, media_backend)
        self.setMinimumSize(QSize(440, 76))
        self.setMaximumSize(QSize(440, self.expanded_height))
        self.resize(440, 76 if compact else self.expanded_height)
        self.rootObject().bodyWidthChanged.connect(self.updateMask)
        self.rootObject().bodyHeightChanged.connect(self.updateMask)
        self.updateMask()
        area = self.screen().availableGeometry()
        self.setPosition(QPoint(area.center().x() - 220,
                                area.top() + max(16, (area.height() - self.expanded_height) // 3)))
        self.restorePlacement()
        self.xChanged.connect(self._positionChanged)
        self.yChanged.connect(self._positionChanged)
        self.screenChanged.connect(self._positionChanged)
        self.visibleChanged.connect(self._capturePlacement)

    def loadScene(self, design, scene_file, audio_backend, media_backend):
        return load_scene(self, design, scene_file, audio_backend, media_backend)

    def restorePlacement(self):
        try:
            saved = json.loads(self.window_settings.value(self._placement_key, "{}"))
            if (not isinstance(saved, dict) or not isinstance(saved.get("screen"), str)
                    or not all(type(saved.get(key)) is int and abs(saved[key]) < 2 ** 30 for key in ("x", "y"))):
                return
            screen = next((screen for screen in QGuiApplication.screens() if screen.name() == saved["screen"]),
                          QGuiApplication.primaryScreen())
            self.setScreen(screen)
            self.setPosition(fit_position(QPoint(saved["x"], saved["y"]), self.size(), screen.availableGeometry()))
            self._saved_placement = saved
        except (ValueError, TypeError):
            pass

    @Slot()
    def _capturePlacement(self):
        if (self._suppress_position or not self.isVisible() or self.visibility() == QWindow.Minimized
                or self.rootObject().property("transitioning")):
            return False
        position = self.position()
        if not any(screen.availableGeometry().intersects(QRect(position, self.size()))
                   for screen in QGuiApplication.screens()):
            return False
        self._last_placement = {"x": position.x(), "y": position.y(), "screen": self.screen().name()}
        return True

    @Slot()
    def _positionChanged(self):
        if self._capturePlacement():
            self._position_timer.start()

    @Slot()
    def flushPlacement(self):
        self._position_timer.stop()
        self._capturePlacement()
        if self._last_placement is None or self._last_placement == self._saved_placement:
            return
        self.window_settings.setValue(self._placement_key, json.dumps(self._last_placement, ensure_ascii=False))
        self.window_settings.sync()
        error = "위치는 바뀌었지만 마지막 위치를 저장하지 못함"
        if self.window_settings.status() == QSettings.NoError:
            self._saved_placement = dict(self._last_placement)
            error = ""
        self._setPreferenceError("position", error)

    def _setPreferenceError(self, kind, message):
        if message:
            self._preference_errors[kind] = message
        else:
            self._preference_errors.pop(kind, None)
        error = " · ".join(self._preference_errors.values())
        if error != self._window_error:
            self._window_error = error
            self.windowPreferenceErrorChanged.emit()

    @Property(bool, notify=trayModeChanged)
    def trayMode(self):
        return self._tray_mode

    def setTrayMode(self, enabled):
        if self._tray_mode == enabled:
            return
        geometry = self.geometry()
        self._suppress_position = True
        try:
            kind = Qt.Tool if enabled else Qt.Window
            self.setFlags((self.flags() & ~Qt.WindowType_Mask) | kind)
            if self.geometry() != geometry:
                self.setGeometry(geometry)
            self.updateMask()
            self._tray_mode = enabled
        finally:
            self._suppress_position = False
        self.trayModeChanged.emit()

    @Slot()
    def hideForTray(self):
        self.flushPlacement()
        self.hide()
        QMetaObject.invokeMethod(self.rootObject(), "settleHiddenTransition", Qt.DirectConnection)

    @Slot()
    def showFromTray(self):
        anchor = self.position() + QPoint(408, 38)
        if not any(screen.availableGeometry().contains(anchor) for screen in QGuiApplication.screens()):
            position = (QPoint(self._last_placement["x"], self._last_placement["y"])
                        if self._last_placement else self.position())
            self.setPosition(fit_position(position, self.size(), self.screen().availableGeometry()))
        if self.visibility() == QWindow.Minimized:
            self.showNormal()
        else:
            self.show()
        if QGuiApplication.platformName() != "offscreen":
            self.raise_()
            self.requestActivate()

    @Slot()
    def openMediaSettings(self):
        self.showFromTray()
        QMetaObject.invokeMethod(self.rootObject(), "openMediaSettings", Qt.DirectConnection)

    @Slot()
    def requestQuit(self):
        self.quitRequested.emit()

    def closeEvent(self, event):
        self.flushPlacement()
        if self.trayMode:
            event.ignore()
            self.hideForTray()
        else:
            super().closeEvent(event)

    def surfaceRegion(self) -> QRegion:
        root = self.rootObject()
        x, width, height = (float(root.property(key))
                            for key in ("bodyX", "bodyWidth", "bodyHeight"))
        radius = self._surface_radius or (12 if root.property("expandedHeight") == 474 else 24)
        path = QPainterPath()
        # Leave the antialiased visual edge intact, but exclude transparent corners.
        path.addRoundedRect(QRectF(x, 0, width, height), radius - 1, radius - 1)
        return QRegion(path.toFillPolygon().toPolygon())

    @Property(bool, notify=alwaysOnTopChanged)
    def alwaysOnTop(self):
        return bool(self.flags() & Qt.WindowStaysOnTopHint)

    @Property(str, notify=windowPreferenceErrorChanged)
    def windowPreferenceError(self):
        return self._window_error

    @Slot(bool)
    def setAlwaysOnTop(self, enabled: bool):
        geometry = self.geometry()
        self._suppress_position = True
        self.setFlag(Qt.WindowStaysOnTopHint, enabled)
        # No hide/show/raise/requestActivate: a stacking change is not a new window.
        if self.geometry() != geometry:
            self.setGeometry(geometry)
        self.updateMask()
        self._suppress_position = False
        self.window_settings.setValue("window/always_on_top", self.alwaysOnTop)
        self.window_settings.sync()
        self._setPreferenceError("topmost", "" if self.window_settings.status() == QSettings.NoError
                                 else "고정 상태는 바뀌었지만 저장하지 못함")

    @Slot()
    def updateMask(self):
        if QGuiApplication.platformName() != "offscreen":
            self.setMask(self.surfaceRegion())

    @Slot()
    def prepareTransition(self):
        # Native geometry stays fixed while QML morphs; resize only at phase boundaries.
        self.resize(440, self.expanded_height)

    @Slot(bool)
    def finishTransition(self, compact: bool):
        self.resize(440, 76 if compact else self.expanded_height)
        self.updateMask()

    @Slot(result=bool)
    def beginMove(self) -> bool:
        return self.startSystemMove()

    @Slot(QWindow)
    def positionSettings(self, window):
        screen = self.screen()
        area = screen.availableGeometry()
        center = self.geometry().center()
        window.setScreen(screen)
        window.create()
        frame = window.frameMargins()
        window.resize(min(416, area.width() - frame.left() - frame.right()),
                      min(552, area.height() - frame.top() - frame.bottom()))
        window.setPosition(QPoint(
            max(area.left() + frame.left(), min(center.x() - window.width() // 2,
                                               area.right() - window.width() - frame.right() + 1)),
            max(area.top() + frame.top(), min(center.y() - window.height() // 2,
                                             area.bottom() - window.height() - frame.bottom() + 1))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone widget with Windows output control.")
    parser.add_argument("--design", choices=("rose", "paper"), default="rose")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Fixtures only; no Windows audio access.")
    args = parser.parse_args()
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    app = QApplication(sys.argv[:1])
    app.setApplicationName("AudioWidgetConcept")
    QQuickStyle.setStyle("Basic")
    QQuickWindow.setDefaultAlphaBuffer(True)
    backend = media = None
    if not args.demo:
        from audio_backend import AudioBackend
        backend = AudioBackend()
        from media_backend import MediaBackend
        media = MediaBackend()
    view = WidgetView(args.design, args.compact, backend, media_backend=media)
    from tray import TrayController
    tray = TrayController(view, backend, media)
    app.aboutToQuit.connect(view.flushPlacement)
    if backend is not None:
        app.aboutToQuit.connect(backend.stop)
        app.aboutToQuit.connect(media.stop)
    app.aboutToQuit.connect(lambda: print(
        json.dumps({"design": args.design, "event": "application_quit"}), flush=True))
    view.show()
    QTimer.singleShot(500, lambda: print(json.dumps({
        "design": args.design, "platform": app.platformName(),
        "visible": view.isVisible(), "exposed": view.isExposed(),
        "geometry": view.geometry().getRect(),
        "tray_mode": tray.active,
        "qml_warnings": view.qml_warnings, "icon_failures": view.icons.failures,
    }, ensure_ascii=False), flush=True))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
