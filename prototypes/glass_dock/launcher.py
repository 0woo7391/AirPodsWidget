"""Quick-launch module: a short, user-curated list of apps, files or folders."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QFileInfo, QObject, Property, QSettings, QSize, QStandardPaths, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QImage
from PySide6.QtQuick import QQuickImageProvider

MAX_APPS = 12


def display_name(path: str) -> str:
    name = Path(path).stem or path
    return name.replace("_", " ").replace("-", " ").strip() or path


class LauncherBackend(QObject):
    appsChanged = Signal()

    def __init__(self, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "launcher.ini"),
            QSettings.IniFormat)
        self._apps = self._load()

    def _load(self) -> list[dict]:
        try:
            values = json.loads(self.settings.value("launcher/apps", "[]"))
        except (TypeError, ValueError):
            return []
        if not isinstance(values, list):
            return []
        return [dict(name=str(v["name"]), path=str(v["path"])) for v in values
                if isinstance(v, dict) and isinstance(v.get("path"), str) and v.get("name")][:MAX_APPS]

    def _save(self) -> None:
        self.settings.setValue("launcher/apps", json.dumps(self._apps, ensure_ascii=False))
        self.settings.sync()
        self.appsChanged.emit()

    @Property("QVariantList", notify=appsChanged)
    def apps(self):
        return [dict(app, index=i, hasIcon=os.path.exists(app["path"])) for i, app in enumerate(self._apps)]

    @Slot(int)
    def launch(self, index: int) -> None:
        if 0 <= index < len(self._apps):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._apps[index]["path"]))

    @Slot("QVariantList", result=int)
    def addUrls(self, urls) -> int:
        """Add dropped files; returns how many were added."""
        added = 0
        known = {app["path"].casefold() for app in self._apps}
        for value in urls:
            path = QUrl(str(value)).toLocalFile() if not isinstance(value, QUrl) else value.toLocalFile()
            if not path or path.casefold() in known or len(self._apps) >= MAX_APPS:
                continue
            self._apps.append(dict(name=display_name(path), path=os.path.normpath(path)))
            known.add(path.casefold())
            added += 1
        if added:
            self._save()
        return added

    @Slot(int)
    def remove(self, index: int) -> None:
        if 0 <= index < len(self._apps):
            del self._apps[index]
            self._save()


class AppIconProvider(QQuickImageProvider):
    """image://appicon/<index> — the shell icon of a launcher entry; empty when unavailable."""

    def __init__(self, launcher: LauncherBackend):
        super().__init__(QQuickImageProvider.Image)
        self.launcher = launcher
        self._icons = None

    def requestImage(self, request: str, size: QSize, requested_size: QSize) -> QImage:
        side = requested_size.width() if requested_size.width() > 0 else 64
        try:
            path = self.launcher._apps[int(request.split("?", 1)[0])]["path"]
        except (ValueError, IndexError):
            return QImage()
        if not os.path.exists(path):
            return QImage()
        if self._icons is None:
            from PySide6.QtWidgets import QFileIconProvider
            self._icons = QFileIconProvider()
        icon = self._icons.icon(QFileInfo(path))
        image = icon.pixmap(side, side).toImage() if not icon.isNull() else QImage()
        if not image.isNull():
            image = image.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image
