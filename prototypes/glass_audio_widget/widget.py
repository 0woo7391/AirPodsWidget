"""Separate glass widget; reuses audio/media owners and the tested native host."""
from __future__ import annotations

import argparse
from ctypes import wintypes
from pathlib import Path
import sys

from PySide6.QtCore import QTimer, Slot, Qt, QMetaObject, QPoint
from PySide6.QtQuick import QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QWindow

BASE = Path(__file__).resolve().parent
CONCEPT = BASE.parent / "audio_widget_concepts"
sys.path.insert(0, str(CONCEPT))
sys.path.insert(0, str(BASE.parent / "desktop_glass_lab"))
# This entrypoint is named widget.py too, so import the existing host explicitly.
import importlib.util
spec = importlib.util.spec_from_file_location("audio_widget_host", CONCEPT / "widget.py")
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
from preview import load_scene
from desktop_glass import Capture, DesktopFrames, EXCLUDE, display_affinity
from device_backend import DeviceBackend
from preferences import Preferences


class GlassWidget(host.WidgetView):
    def __init__(self, audio=None, media=None, window_settings=None, compact=False, device_backend=None):
        self.capture = None
        self._device_backend = device_backend
        self.mouse_drag = False
        super().__init__("glass", compact, audio, window_settings, media,
                         scene_file=str(BASE / "GlassWidget.qml"), expanded_height=360, surface_radius=28)
        self.setTitle("Glass Audio Widget")
        self.create()
        self.xChanged.connect(self.capture.moved)
        self.yChanged.connect(self.capture.moved)
        self.screenChanged.connect(self.capture.moved)
        self.flagsChanged.connect(self.captureFlagsChanged)
        self.sceneGraphInitialized.connect(self.rendererReady, Qt.QueuedConnection)
        self.captureFlagsChanged()
        self.devices.connectionHint.connect(self.showConnectionNotice)

    def loadScene(self, design, scene_file, audio_backend, media_backend):
        self.frames = DesktopFrames()
        self.engine().addImageProvider("desktop", self.frames)
        self.capture = Capture(self, self.frames)
        self.devices = self._device_backend if self._device_backend is not None else DeviceBackend(settings=self.window_settings,start=False)
        self.preferences = Preferences(self.window_settings)
        self.rootContext().setContextProperty("deviceBackend",self.devices)
        self.rootContext().setContextProperty("widgetPreferences",self.preferences)
        self.rootContext().setContextProperty("desktopCapture", self.capture)
        self.engine().addImportPath(str(CONCEPT / "qml"))
        return load_scene(self, design, scene_file, audio_backend, media_backend)

    @Slot()
    def showConnectionNotice(self):
        QMetaObject.invokeMethod(self.rootObject(),"offerConnection",Qt.DirectConnection)

    @Slot(QWindow)
    def positionNotice(self,window):
        icon=getattr(self,"tray_icon",None)
        geometry=icon.geometry() if icon is not None else None
        from PySide6.QtGui import QGuiApplication
        screen=QGuiApplication.screenAt(geometry.center()) if geometry and geometry.isValid() else self.screen()
        screen=screen or self.screen()
        area=screen.availableGeometry(); window.setScreen(screen)
        window.setPosition(QPoint(area.right()-window.width()-11,area.bottom()-window.height()-11))

    @Slot()
    def rendererReady(self):
        if self.rendererInterface().graphicsApi() == QSGRendererInterface.Software:
            self.capture.fail("현재 렌더러는 굴절을 지원하지 않음")

    @Slot()
    def captureFlagsChanged(self, *args):
        self.capture.timer.stop()
        try:
            self.capture.affinity = display_affinity(self, 0 if self.capture.frozen else EXCLUDE)
            self.capture.moved()
        except (OSError, RuntimeError) as error:
            self.capture.fail(error)

    @Slot(result=bool)
    def beginMove(self):
        # Some platforms run the native move loop before startSystemMove returns.
        self.mouse_drag = True
        self.capture.moved()
        result = super().beginMove()
        if not result:
            self.mouse_drag = False
            self.capture.moved()
        return result

    def nativeEvent(self, event_type, message):
        event = wintypes.MSG.from_address(int(message))
        if self.capture and event.message in (0x0231, 0x0232):
            self.mouse_drag = event.message == 0x0231
            self.capture.moved()
        return super().nativeEvent(event_type, message)

    @Slot()
    def prepareTransition(self):
        self._transition_origin = self.position()
        self.capture.moved()
        super().prepareTransition()

    @Slot(float)
    def fitTransitionHeight(self, height):
        from PySide6.QtGui import QGuiApplication
        origin = getattr(self, "_transition_origin", self.position())
        screen = QGuiApplication.screenAt(origin + QPoint(408, 38)) or self.screen()
        area = screen.availableGeometry()
        self.setPosition(QPoint(
            max(area.left(), min(origin.x(), area.right()-self.width()+1)),
            max(area.top(), min(origin.y(), area.bottom()-round(height)+1))))

    @Slot(bool)
    def finishTransition(self, compact):
        super().finishTransition(compact)
        self.capture.moved()

    @Slot()
    def showFromTray(self):
        super().showFromTray()
        self.captureFlagsChanged()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="store_true", help="Real desktop snapshot, visible remotely; F8 resumes live.")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("GlassAudioWidget")
    QQuickStyle.setStyle("Basic")
    from audio_backend import AudioBackend
    from media_backend import MediaBackend
    from glass_tray import GlassTray
    audio, media = AudioBackend(), MediaBackend()
    devices=DeviceBackend()
    view = GlassWidget(audio, media, device_backend=devices)
    tray = GlassTray(view, audio, media)
    view.tray_icon=tray.tray
    app.aboutToQuit.connect(view.flushPlacement)
    app.aboutToQuit.connect(audio.stop)
    app.aboutToQuit.connect(media.stop)
    app.aboutToQuit.connect(devices.stop)
    app.aboutToQuit.connect(view.preferences.flush)
    app.aboutToQuit.connect(view.capture.timer.stop)
    app.aboutToQuit.connect(view.capture.settle.stop)
    view.show()
    if args.snapshot:
        def freeze():
            if view.capture.failure:
                return
            if view.capture.serial:
                view.capture.togglePause()
            else:
                QTimer.singleShot(100, freeze)
        QTimer.singleShot(300, freeze)
    QTimer.singleShot(800, lambda: print({"visible": view.isVisible(), "tray": tray.active,
                      "frames": view.capture.serial, "capture_error": view.capture.failure,
                      "qml_warnings": view.qml_warnings}, flush=True))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
