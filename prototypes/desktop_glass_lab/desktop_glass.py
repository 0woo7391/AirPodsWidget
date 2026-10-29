"""Live desktop-texture refraction experiment; no audio, BLE, or saved settings."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from collections import deque
from pathlib import Path
import sys
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QPoint, QRect, QSize, QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage
from PySide6.QtQuick import QQuickImageProvider, QQuickView, QSGRendererInterface

BASE = Path(__file__).resolve().parent
SIZE = QSize(440, 260)
EXCLUDE = 0x11


def display_affinity(window, value):
    if sys.platform != "win32" or sys.getwindowsversion().build < 19041:
        raise RuntimeError("Windows 10 2004 or newer required for capture exclusion")
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    api.SetWindowDisplayAffinity.restype = wintypes.BOOL
    api.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.GetWindowDisplayAffinity.restype = wintypes.BOOL
    handle = int(window.winId())
    if not api.SetWindowDisplayAffinity(handle, value):
        raise ctypes.WinError(ctypes.get_last_error())
    actual = wintypes.DWORD()
    if not api.GetWindowDisplayAffinity(handle, ctypes.byref(actual)):
        raise ctypes.WinError(ctypes.get_last_error())
    if actual.value != value:
        raise RuntimeError("Capture exclusion did not retain requested value")
    # Wait for this process's composition changes before sampling the desktop.
    ctypes.WinDLL("dwmapi").DwmFlush()
    return actual.value


def fit_position(point, area, size=SIZE):
    return QPoint(max(area.left(), min(point.x(), area.right() - size.width() + 1)),
                  max(area.top(), min(point.y(), area.bottom() - size.height() + 1)))


class DesktopFrames(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage(1, 1, QImage.Format_RGBA8888)
        self.image.fill(Qt.transparent)

    def requestImage(self, name, size, requested_size):
        size.setWidth(self.image.width())
        size.setHeight(self.image.height())
        return self.image


class Capture(QObject):
    changed = Signal()

    def __init__(self, view, provider):
        super().__init__(view)
        self.view, self.provider = view, provider
        self.serial = 0
        self.frozen = False
        self.dragging = False
        self.failure = ""
        self.affinity = EXCLUDE
        self.capture_ms = deque(maxlen=240)
        self.intervals_ms = deque(maxlen=240)
        self.last_capture = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.capture)
        self.settle = QTimer(self)
        self.settle.setSingleShot(True)
        self.settle.setInterval(120)
        self.settle.timeout.connect(self.settled)

    @Property(int, notify=changed)
    def frame(self):
        return self.serial

    @Property(QSize, notify=changed)
    def sourceSize(self):
        image = self.provider.image
        ratio = image.devicePixelRatio()
        return QSize(round(image.width() / ratio), round(image.height() / ratio))

    @Property(bool, notify=changed)
    def paused(self):
        return self.frozen

    @Property(bool, notify=changed)
    def moving(self):
        return self.dragging

    @Property(str, notify=changed)
    def error(self):
        return self.failure

    def fail(self, error):
        self.timer.stop()
        self.settle.stop()
        self.failure = str(error)
        try:
            self.affinity = display_affinity(self.view, 0)
        except (OSError, RuntimeError):
            pass
        self.changed.emit()

    def capture(self):
        if (self.frozen or self.dragging or self.failure or not self.view.isVisible()
                or not self.view.isExposed() or self.view.windowState() == Qt.WindowMinimized):
            return
        try:
            if self.affinity != EXCLUDE:
                raise RuntimeError("Capture stopped: own window is not excluded")
            region = QRect(self.view.position(), self.view.size())
            screen = QGuiApplication.screenAt(region.center())
            if screen is None or not screen.geometry().contains(region):
                self.moved()
                return
            local = region.topLeft() - screen.geometry().topLeft()
            start = time.perf_counter()
            image = screen.grabWindow(0, local.x(), local.y(), region.width(), region.height()).toImage()
            if image.isNull():
                raise RuntimeError("Desktop capture returned an empty image")
            self.capture_ms.append((time.perf_counter() - start) * 1000)
            if self.last_capture is not None:
                self.intervals_ms.append((start - self.last_capture) * 1000)
            self.last_capture = start
            self.provider.image = image
            self.serial += 1
            self.changed.emit()
            # shortcut: CPU readback/texture upload prototype, not 60fps GPU capture.
            # Slow captures reduce polling instead of continuously blocking the GUI.
            self.timer.setInterval(max(50, min(500, round(self.capture_ms[-1] * 3))))
        except (OSError, RuntimeError) as error:
            self.fail(error)

    def moved(self, *args):
        self.dragging = True
        self.timer.stop()
        self.changed.emit()
        self.settle.start()

    @Slot()
    def settled(self):
        if getattr(self.view, "mouse_drag", False) or self.view.rootObject().property("transitioning"):
            self.settle.start()
            return
        screen = QGuiApplication.screenAt(self.view.geometry().center()) or self.view.screen()
        point = fit_position(self.view.position(), screen.availableGeometry(), self.view.size())
        if point != self.view.position():
            self.view.setPosition(point)
            self.settle.start()
            return
        self.dragging = False
        self.last_capture = None
        self.changed.emit()
        if not self.frozen and not self.failure:
            self.capture()
            self.timer.start()

    @Slot()
    def togglePause(self):
        if self.failure:
            return
        self.timer.stop()
        self.settle.stop()
        try:
            if not self.frozen:
                # Stop capture BEFORE becoming visible to remote/recording software.
                self.frozen = True
                self.affinity = display_affinity(self.view, 0)
                self.changed.emit()
            else:
                self.affinity = display_affinity(self.view, EXCLUDE)
                self.frozen = False
                self.moved()
        except (OSError, RuntimeError) as error:
            self.fail(error)


class GlassView(QQuickView):
    def __init__(self):
        super().__init__()
        self.mouse_drag = False
        self.drag_origin = QPoint()
        self.window_origin = QPoint()
        self.capture = None
        self.setTitle("Desktop Glass Lab — live refraction / F8 freeze")
        # Normal window keeps this lab discoverable in Alt-Tab/remote app lists.
        self.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setColor(Qt.transparent)
        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.resize(SIZE)
        self.setMinimumSize(SIZE)
        self.setMaximumSize(SIZE)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and 20 <= event.position().y() <= 80 and event.position().x() < 310:
            self.mouse_drag = True
            self.drag_origin = event.globalPosition().toPoint()
            self.window_origin = self.position()
            self.capture.moved()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mouse_drag and event.buttons() & Qt.LeftButton:
            self.setPosition(self.window_origin + event.globalPosition().toPoint() - self.drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mouse_drag and event.button() == Qt.LeftButton:
            self.mouse_drag = False
            self.capture.moved()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F8:
            self.capture.togglePause()
        elif event.key() == Qt.Key_R:
            root = self.rootObject()
            root.setProperty("refract", not root.property("refract"))
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.capture:
            self.capture.timer.stop()
            self.capture.settle.stop()
        super().closeEvent(event)


def create_view():
    view = GlassView()
    frames = DesktopFrames()
    view.engine().addImageProvider("desktop", frames)
    view.frames = frames
    view.capture = Capture(view, frames)
    view.rootContext().setContextProperty("desktopCapture", view.capture)
    view.warnings = []
    view.engine().warnings.connect(lambda issues: view.warnings.extend(x.toString() for x in issues))
    view.setSource(QUrl.fromLocalFile(str(BASE / "DesktopGlass.qml")))
    if view.status() == QQuickView.Error:
        raise RuntimeError("\n".join(x.toString() for x in view.errors()))
    view.create()
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    view.setPosition(fit_position(screen.availableGeometry().center() - QPoint(220, 130), screen.availableGeometry()))
    view.xChanged.connect(view.capture.moved)
    view.yChanged.connect(view.capture.moved)
    view.screenChanged.connect(view.capture.moved)

    def renderer_ready():
        if view.rendererInterface().graphicsApi() == QSGRendererInterface.Software:
            view.capture.fail("Shader-capable renderer required; software cannot refract")

    view.sceneGraphInitialized.connect(renderer_ready, Qt.QueuedConnection)
    try:
        view.capture.affinity = display_affinity(view, EXCLUDE)
    except (OSError, RuntimeError) as error:
        view.capture.fail(error)
    QTimer.singleShot(180, view.capture.settled)
    return view


def main():
    app = QGuiApplication(sys.argv[:1])
    view = create_view()
    view.show()
    view.requestActivate()
    if "--snapshot" in sys.argv:
        def snapshot_when_ready():
            if view.capture.failure:
                return
            if view.capture.serial:
                view.capture.togglePause()
            else:
                QTimer.singleShot(80, snapshot_when_ready)
        QTimer.singleShot(250, snapshot_when_ready)
    QTimer.singleShot(700, lambda: print("Desktop Glass Lab:", {"visible": view.isVisible(),
                      "frames": view.capture.serial, "error": view.capture.failure,
                      "affinity": view.capture.affinity}, flush=True))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
