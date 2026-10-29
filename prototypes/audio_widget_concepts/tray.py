"""Native tray access to the existing widget and its existing audio/media owners."""
from __future__ import annotations

import logging

from PySide6.QtCore import QByteArray, QObject, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPixmap, QWindow
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def make_icon(provider):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#383431"))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 15, 15)
    renderer = QSvgRenderer(QByteArray(provider.svg("headphones?color=%23F1F2ED")))
    renderer.render(painter, QRectF(11, 11, 42, 42))
    painter.end()
    return QIcon(pixmap)


class TrayController(QObject):
    def __init__(self, view, audio=None, media=None, app=None,
                 tray_factory=QSystemTrayIcon, availability=None):
        super().__init__(view)
        self.view, self.audio, self.media = view, audio, media
        self.app = app if app is not None else QApplication.instance()
        self._availability = availability or QSystemTrayIcon.isSystemTrayAvailable
        self.active = False
        self._stopped = self._quitting = False
        self._devices = None
        self.output_actions = {}
        self.tray = tray_factory(self)
        self.tray.setIcon(make_icon(view.icons))
        self.tray.setToolTip("오디오 위젯")
        self.menu = QMenu()
        self.menu.setToolTipsVisible(True)
        self.show_action = self.menu.addAction("위젯 표시", self.toggleView)
        self.menu.addSeparator()
        self.mute_action = self.menu.addAction("출력 음소거")
        self.mute_action.setCheckable(True)
        if audio is not None:
            self.mute_action.triggered.connect(audio.toggleMute)
            audio.changed.connect(self.sync)
        self.outputs = self.menu.addMenu("출력 장치")
        self.menu.addSeparator()
        self.topmost_action = self.menu.addAction("항상 위에 표시")
        self.topmost_action.setCheckable(True)
        self.topmost_action.triggered.connect(view.setAlwaysOnTop)
        self.settings_action = self.menu.addAction("미디어 설정", view.openMediaSettings)
        self.settings_action.setEnabled(media is not None)
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction("종료", self.quit)
        self.menu.aboutToShow.connect(self.sync)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._activated)
        view.visibleChanged.connect(self.sync)
        view.visibilityChanged.connect(self.sync)
        view.alwaysOnTopChanged.connect(self.sync)
        view.quitRequested.connect(self.quit)
        self.app.aboutToQuit.connect(self.stop)
        self._watch = QTimer(self)
        self._watch.setInterval(2000)
        self._watch.timeout.connect(self.refreshAvailability)
        self.refreshAvailability()
        self._watch.start()
        self.sync()

    def refreshAvailability(self):
        if self._stopped:
            return
        available = False
        try:
            available = bool(self._availability())
            if available:
                if not self.tray.isVisible():
                    self.tray.show()
                # shortcut: Qt visibility cannot confirm Explorer registration; inspect Shell if icon access fails.
                available = self.tray.isVisible()
            else:
                self.tray.hide()
        except Exception as exc:
            available = False
            logging.getLogger(__name__).warning("Tray unavailable; keeping window access: %s", exc)
        previous, self.active = self.active, available
        self.view.setTrayMode(available)
        self.app.setQuitOnLastWindowClosed(not available)
        if previous and not available:
            self.view.showFromTray()
        self.sync()

    def _activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggleView()

    def toggleView(self):
        if self._stopped:
            return
        self.refreshAvailability()
        if not self.active:
            self.view.showFromTray()
        elif self.view.isVisible() and self.view.visibility() != QWindow.Minimized:
            self.view.hideForTray()
        else:
            self.view.showFromTray()
        self.sync()

    def sync(self):
        if self._stopped:
            return
        shown = self.view.isVisible() and self.view.visibility() != QWindow.Minimized
        self.show_action.setText("위젯 숨기기" if shown else "위젯 표시")
        self.topmost_action.setChecked(self.view.alwaysOnTop)
        state = self.audio.state if self.audio is not None else {}
        ready = bool(state.get("available")) and not state.get("pendingId")
        self.mute_action.setEnabled(ready)
        self.mute_action.setChecked(bool(state.get("muted")))
        devices = self.audio.devices if self.audio is not None else []
        if devices != self._devices:
            self._devices = list(devices)
            self.outputs.clear()
            self.output_actions = {}
            metrics = QFontMetrics(self.menu.font())
            for device in devices:
                action = self.outputs.addAction(metrics.elidedText(device["name"], Qt.ElideRight, 360))
                action.setToolTip(device["name"])
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False, device_id=device["id"]: self.audio.selectOutput(device_id))
                self.output_actions[device["id"]] = action
        self.outputs.setEnabled(bool(devices))
        for device in devices:
            action = self.output_actions[device["id"]]
            action.setChecked(device["id"] == state.get("currentId"))
            action.setEnabled(bool(device.get("available")) and not state.get("pendingId"))
        self.tray.setToolTip("오디오 위젯" + (" · " + state["error"] if state.get("error") else ""))

    def quit(self):
        if self._quitting:
            return
        self._quitting = True
        self.view.hideForTray()
        self.stop()
        self.app.quit()

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self._watch.stop()
        self.view.flushPlacement()
        self.menu.close()
        self.tray.hide()
