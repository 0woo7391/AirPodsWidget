"""Quick-launch module: a short, user-curated list of apps, files, folders or websites.

A website's own icon and name are fetched from the site itself when it is added (its
apple-touch-icon or largest <link rel=icon>, else /favicon.ico) and cached as a PNG
next to the settings, so no third-party icon service sees the list.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from PySide6.QtCore import QFileInfo, QObject, Property, QSettings, QSize, QStandardPaths, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QImage
from PySide6.QtQuick import QQuickImageProvider

MAX_APPS = 12
ICON_SIDE = 128
FETCH_TIMEOUT = 8
FETCH_LIMIT = 1024 * 1024
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")


def extract_icon(path: str, side: int) -> QImage:
    """The file's own icon at `side` px (crisp, no shortcut arrow); null when it has none.

    shortcut: always icon index 0 of the file, not a shortcut's custom IconLocation;
    read it with IShellLink if a shortcut ever shows the wrong picture.
    """
    if os.name != "nt":
        return QImage()
    import ctypes
    from ctypes import wintypes
    shell32 = ctypes.WinDLL("shell32")
    shell32.SHDefExtractIconW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, wintypes.UINT,
                                          ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.HICON), wintypes.UINT]
    icon = wintypes.HICON()
    if shell32.SHDefExtractIconW(path, 0, 0, ctypes.byref(icon), None, side) != 0 or not icon.value:
        return QImage()
    try:
        return QImage.fromHICON(icon.value)
    finally:
        ctypes.WinDLL("user32").DestroyIcon(icon)


def display_name(path: str) -> str:
    name = Path(path).stem or path
    return name.replace("_", " ").replace("-", " ").strip() or path


# ---- websites -------------------------------------------------------------------------

def normalize_url(text: str) -> str:
    """"naver.com" -> "https://naver.com"; "" when it is not a web address."""
    text = (text or "").strip()
    if not text or any(c.isspace() for c in text):
        return ""
    if "://" not in text:
        text = "https://" + text
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname or "." not in parts.hostname:
        return ""
    return urllib.parse.urlunsplit(parts)


def site_name(url: str) -> str:
    """The main label of the host: "www.instagram.com" -> "Instagram", "m.naver.com" -> "Naver"."""
    host = (urllib.parse.urlsplit(url).hostname or url).split(".")
    labels = [h for h in host if h not in ("www", "m")]
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in ("co", "or", "go", "ac", "ne", "com"):
        labels = labels[:-1]        # naver.co.kr -> naver
    main = labels[-2] if len(labels) >= 2 else labels[0]
    return main[:1].upper() + main[1:]


def internet_shortcut_url(path: str) -> str:
    """The URL inside a .url (internet shortcut) file."""
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().upper().startswith("URL="):
                return normalize_url(line.split("=", 1)[1])
    except OSError:
        pass
    return ""


class _IconLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.icons: list[tuple[int, str]] = []   # (rank, href); higher rank is better
        self.name = ""
        self.title = ""
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_starttag(self, tag, attrs):
        values = {k.lower(): (v or "") for k, v in attrs}
        self._in_title = tag == "title" and not self.title
        if tag == "link" and values.get("href"):
            rel = values.get("rel", "").lower().split()
            if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
                self.icons.append((1000, values["href"]))
            elif "icon" in rel:
                sizes = [int(n) for s in values.get("sizes", "").lower().split() for n in s.split("x")[:1] if n.isdigit()]
                self.icons.append((max(sizes, default=32) - (500 if values["href"].endswith(".svg") else 0), values["href"]))
        elif tag == "meta" and values.get("property", values.get("name", "")).lower() in ("og:site_name", "application-name"):
            self.name = self.name or values.get("content", "").strip()


def _get(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ko,en;q=0.8"})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
        return response.read(FETCH_LIMIT), response.geturl()


def fetch_site(url: str) -> tuple[QImage, str]:
    """(icon, the site's own short name) — a null image / "" for what could not be found."""
    links = _IconLinks()
    base = url
    try:
        page, base = _get(url)
        links.feed(page.decode("utf-8", "replace"))
    except Exception:
        pass
    candidates = [href for _, href in sorted(links.icons, key=lambda item: -item[0])] + ["/favicon.ico"]
    for href in candidates:
        try:
            data, _ = _get(urllib.parse.urljoin(base, href))
        except Exception:
            continue
        image = QImage.fromData(data)
        if not image.isNull():
            if max(image.width(), image.height()) > ICON_SIDE:
                image = image.scaled(ICON_SIDE, ICON_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return image, links.name or links.title.strip()
    return QImage(), links.name or links.title.strip()


class LauncherBackend(QObject):
    appsChanged = Signal()
    _fetched = Signal(str, str, str)   # url, icon file, name

    def __init__(self, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "launcher.ini"),
            QSettings.IniFormat)
        self.icon_folder = Path(self.settings.fileName()).parent / "webicons"
        self._apps = self._load()
        self._fetched.connect(self._apply_fetch)
        for app in self._apps:   # a site added while offline gets its icon on the next start
            if app.get("url") and not os.path.exists(app.get("icon", "")):
                self._fetch(app["url"])

    def _load(self) -> list[dict]:
        try:
            values = json.loads(self.settings.value("launcher/apps", "[]"))
        except (TypeError, ValueError):
            return []
        if not isinstance(values, list):
            return []
        apps = []
        for v in values:
            if not isinstance(v, dict) or not v.get("name"):
                continue
            if isinstance(v.get("url"), str) and normalize_url(v["url"]):
                apps.append(dict(name=str(v["name"]), url=v["url"], icon=str(v.get("icon", "")),
                                 named=bool(v.get("named"))))
            elif isinstance(v.get("path"), str):
                apps.append(dict(name=str(v["name"]), path=v["path"]))
        return apps[:MAX_APPS]

    def _save(self) -> None:
        self.settings.setValue("launcher/apps", json.dumps(self._apps, ensure_ascii=False))
        self.settings.sync()
        self.appsChanged.emit()

    @Property("QVariantList", notify=appsChanged)
    def apps(self):
        return [dict(app, index=i, path=app.get("path", app.get("url", "")),
                     hasIcon=os.path.exists(app.get("icon") or app.get("path") or ""),
                     iconKey=app.get("icon") or app.get("path", ""))
                for i, app in enumerate(self._apps)]

    @Slot(int)
    def launch(self, index: int) -> None:
        if not 0 <= index < len(self._apps):
            return
        app = self._apps[index]
        # The packaged dock points the DLL search path at its own folder (SetDllDirectory), and
        # launched apps inherit it: they would load the dock's DLLs and lock its files. Launch
        # with the default search path, then put the dock's back.
        frozen = os.name == "nt" and getattr(sys, "frozen", False)
        if frozen:
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            QDesktopServices.openUrl(QUrl(app["url"]) if app.get("url") else QUrl.fromLocalFile(app["path"]))
        finally:
            if frozen:
                ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)

    def _known(self) -> set[str]:
        return {(app.get("url") or app.get("path", "")).casefold() for app in self._apps}

    @Slot("QVariantList", result=int)
    def addUrls(self, urls) -> int:
        """Add dropped files, web links or internet shortcuts; returns how many were added."""
        added = 0
        for value in urls:
            url = value if isinstance(value, QUrl) else QUrl(str(value))
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith(".url") and internet_shortcut_url(path):
                    added += self._add_site(internet_shortcut_url(path))
                    continue
                if not path or path.casefold() in self._known() or len(self._apps) >= MAX_APPS:
                    continue
                self._apps.append(dict(name=display_name(path), path=os.path.normpath(path)))
                added += 1
            else:
                added += self._add_site(normalize_url(url.toString()), save=False)
        if added:
            self._save()
        return added

    @Slot(str, result=bool)
    def addWebsite(self, text: str) -> bool:
        return bool(self._add_site(normalize_url(text)))

    def _add_site(self, url: str, save: bool = True) -> int:
        if not url or url.casefold() in self._known() or len(self._apps) >= MAX_APPS:
            return 0
        self._apps.append(dict(name=site_name(url), url=url, icon="", named=False))
        if save:
            self._save()
        self._fetch(url)
        return 1

    def _fetch(self, url: str) -> None:
        def run():
            image, name = fetch_site(url)
            icon = ""
            if not image.isNull():
                self.icon_folder.mkdir(parents=True, exist_ok=True)
                icon = str(self.icon_folder / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".png"))
                if not image.save(icon, "PNG"):
                    icon = ""
            self._fetched.emit(url, icon, name)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str, str, str)
    def _apply_fetch(self, url: str, icon: str, name: str) -> None:
        for app in self._apps:
            if app.get("url") == url:
                app["icon"] = icon or app.get("icon", "")
                # A short site name ("Instagram", "NAVER") beats the host label; long titles don't.
                if name and not app.get("named") and len(name) <= 16:
                    app["name"], app["named"] = name, True
                self._save()
                return

    @Slot(int, int)
    def move(self, source: int, target: int) -> None:
        if source != target and 0 <= source < len(self._apps) and 0 <= target < len(self._apps):
            self._apps.insert(target, self._apps.pop(source))
            self._save()

    @Slot(int)
    def remove(self, index: int) -> None:
        if 0 <= index < len(self._apps):
            del self._apps[index]
            self._save()


class ExeIconProvider(QQuickImageProvider):
    """image://exeicon/<url-encoded path> — a program's own icon, for the per-app volume module."""

    def __init__(self):
        super().__init__(QQuickImageProvider.Image)

    def requestImage(self, request: str, size: QSize, requested_size: QSize) -> QImage:
        from urllib.parse import unquote
        side = requested_size.width() if requested_size.width() > 0 else 32
        image = extract_icon(unquote(request), side)
        if image.isNull():   # no icon to show: a blank, so the card simply has no picture
            image = QImage(side, side, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


class AppIconProvider(QQuickImageProvider):
    """image://appicon/<index> — the shell icon of a launcher entry, or a site's cached icon; empty when unavailable."""

    def __init__(self, launcher: LauncherBackend):
        super().__init__(QQuickImageProvider.Image)
        self.launcher = launcher
        self._icons = None

    def requestImage(self, request: str, size: QSize, requested_size: QSize) -> QImage:
        side = requested_size.width() if requested_size.width() > 0 else 64
        try:
            app = self.launcher._apps[int(request.split("?", 1)[0])]
        except (ValueError, IndexError):
            return QImage()
        if app.get("url"):
            image = QImage(app.get("icon", ""))
        else:
            image = self._file_icon(app["path"], side)
        if not image.isNull():
            image = image.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image

    def _file_icon(self, path: str, side: int) -> QImage:
        if not os.path.exists(path):
            return QImage()
        if self._icons is None:
            from PySide6.QtWidgets import QFileIconProvider
            self._icons = QFileIconProvider()
        # A shortcut's own icon carries the shell's arrow overlay; use its target's icon instead,
        # extracted at full size (the shell's cached one for an .exe is small and blurry).
        info = QFileInfo(path)
        target = info.symLinkTarget() if info.isSymLink() else ""
        if target and os.path.exists(target):
            info = QFileInfo(target)
        image = extract_icon(info.absoluteFilePath(), side) if info.isFile() else QImage()
        if image.isNull():
            icon = self._icons.icon(info)
            image = icon.pixmap(side, side).toImage() if not icon.isNull() else QImage()
        return image
