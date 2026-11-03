"""Instagram DMs from Windows notifications.

Reads the toasts Windows shows (UserNotificationListener; Windows asks the user
once to allow it) and passes on the ones from Instagram: the Instagram app, or
instagram.com notifications from a browser. Nothing logs in to Instagram.
Polls every two seconds; toasts already there when it starts are not news.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

BROWSERS = ("chrome", "msedge", "edge", "whale", "brave", "opera", "firefox", "vivaldi")
# Short, so a browser's own banner is gone almost as soon as the island takes over.
POLL_SECONDS = 0.5
MAX_RECENT = 20
# Follow-up DMs arrive as just "Instagram" + the text; the sender is the one named
# chat of the last few minutes, if there is exactly one.
SENDER_MEMORY_MS = 15 * 60 * 1000
# Instagram re-posts the same notification while it updates; the same sender and text
# again this soon is the same message.
DUPLICATE_MS = 30 * 1000
INBOX_URL = "https://www.instagram.com/direct/inbox/"
# Chromium browsers keep site permissions in each profile's Preferences file.
BROWSER_PROFILES = {"Chrome": r"Google\Chrome\User Data", "Edge": r"Microsoft\Edge\User Data",
                    "Whale": r"Naver\Naver Whale\User Data"}


def blocked_browsers() -> list[str]:
    """Browsers whose profile blocks instagram.com notifications (setting 2): no toast, so nothing to read."""
    blocked = []
    base = Path(os.environ.get("LOCALAPPDATA", ""))
    for name, folder in BROWSER_PROFILES.items():
        for prefs in (base / folder).glob("*/Preferences"):
            try:
                data = json.loads(prefs.read_text(encoding="utf-8"))
                sites = data["profile"]["content_settings"]["exceptions"]["notifications"]
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if any("instagram.com" in site and isinstance(v, dict) and v.get("setting") == 2 for site, v in sites.items()):
                blocked.append(name)
                break
    return blocked


def instagram_message(app: str, texts: list[str]):
    """(sender, content) when a toast is an Instagram message, else None.

    Browser toasts carry [title, body, "instagram.com"]; the title is the sender, or
    "Instagram" with the sender inside the body ("sender: message", "sender님이 ...",
    "sender sent ...", "sender · message"). An unrecognised body keeps "Instagram"
    as the sender (see format_shape for logging what it looked like).
    """
    lowered = [t.lower() for t in texts]
    app = app.lower()
    from_app = "instagram" in app
    from_web = any(b in app for b in BROWSERS) and any("instagram" in t for t in lowered)
    if not (from_app or from_web):
        return None
    lines = [t for t in texts if t and "instagram.com" not in t.lower()]
    if not lines:
        return None
    title, body = lines[0].strip(), " ".join(lines[1:]).strip()
    if title.lower() == "instagram":
        for pattern in SENDER_PATTERNS:
            match = pattern.match(body)
            if match and match.group("sender").strip():
                content = match.groupdict().get("content")
                return match.group("sender").strip(), (content if content is not None else body).strip()
    return title, body


# How Instagram puts the sender in the body when the title is just "Instagram".
SENDER_PATTERNS = [
    re.compile(r"^(?P<sender>[^:\n]{1,60}?)\s*:\s*(?P<content>.*)$", re.S),
    re.compile(r"^(?P<sender>.{1,60}?)\s*님(?:이|께서)\s"),
    re.compile(r"^(?P<sender>.{1,60}?)\s+(?:sent|replied|reacted|liked|mentioned)\b", re.I),
    re.compile(r"^(?P<sender>.{1,60}?)\s+[·•]\s+(?P<content>.*)$", re.S),
]


def format_shape(text: str) -> str:
    """The text with its letters masked (가 / a / 0, other symbols ◆): the format, not the content."""
    keep = set(" :·•-,.!?()[]'\"/@")
    out = []
    for ch in text:
        if "가" <= ch <= "힣":
            out.append("가")
        elif ch.isascii() and ch.isalpha():
            out.append("a")
        elif ch.isdigit():
            out.append("0")
        else:
            out.append(ch if ch in keep else "◆")
    return "".join(out)


class NotificationWatcher(QObject):
    """Finds Instagram DMs and keeps the recent ones (in memory only) for the dock's card."""
    message = Signal(str, str)        # sender, content
    statusChanged = Signal()
    messagesChanged = Signal()
    _found = Signal(str, str)         # worker thread -> GUI thread

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "꺼짐"
        self._stop = threading.Event()
        self._thread = None
        self._messages: list[dict] = []   # newest first
        self._unread = 0
        # Take over Instagram toasts: remove the browser's notification once read, so only the
        # island shows it (set from the settings).
        self.replace_toasts = True
        self._found.connect(self.add)

    @Slot(str, str)
    def add(self, sender, content):
        now = time.time() * 1000
        if sender == "Instagram":
            named = {m["sender"] for m in self._messages
                     if m["sender"] != "Instagram" and now - m["time"] < SENDER_MEMORY_MS}
            if len(named) == 1:
                sender = named.pop()
        if any(m["sender"] == sender and m["content"] == content and now - m["time"] < DUPLICATE_MS
               for m in self._messages):
            return
        self._messages.insert(0, dict(sender=sender, content=content, time=now))
        del self._messages[MAX_RECENT:]
        self._unread += 1
        self.messagesChanged.emit()
        self.message.emit(sender, content)

    @Property("QVariantList", notify=messagesChanged)
    def messages(self):
        return list(self._messages)

    @Property(int, notify=messagesChanged)
    def unread(self):
        return self._unread

    @Slot()
    def markRead(self):
        if self._unread:
            self._unread = 0
            self.messagesChanged.emit()

    @staticmethod
    def _log_shape(app, texts):
        """Record an unrecognised Instagram toast's format (masked, no names or text) for fixing the parser."""
        log = Path(os.environ.get("LOCALAPPDATA", ".")) / "GlassDock" / "instagram-formats.log"
        try:
            lines = log.read_text(encoding="utf-8").splitlines()[-49:] if log.exists() else []
            lines.append(f"{time.strftime('%Y-%m-%d %H:%M')} {app.split()[0] if app else '?'} | "
                         + " | ".join(format_shape(t) for t in texts))
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    @Slot()
    def openInbox(self):
        self.markRead()
        QDesktopServices.openUrl(QUrl(INBOX_URL))

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=statusChanged)
    def blocked(self):
        return "차단" in self._status

    def _set_status(self, text):
        if text != self._status:
            self._status = text
            self.statusChanged.emit()   # queued to the GUI thread by Qt

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=lambda: asyncio.run(self._run()), name="Notifications", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()

    async def _run(self):
        try:
            from winrt.windows.ui.notifications import KnownNotificationBindings, NotificationKinds
            from winrt.windows.ui.notifications.management import UserNotificationListener
            listener = UserNotificationListener.current
            if int(await listener.request_access_async()) != 1:   # UserNotificationListenerAccessStatus.ALLOWED
                self._set_status("Windows 설정에서 알림 액세스를 허용해야 합니다")
                return
        except Exception as exc:  # no WinRT bindings or an old Windows
            self._set_status(f"알림을 읽을 수 없음 ({type(exc).__name__})")
            return
        seen = None
        checked = 0.0
        while not self._stop.is_set():
            try:
                items = await listener.get_notifications_async(NotificationKinds.TOAST)
                # A browser that blocks instagram.com never makes a toast; say so instead of
                # looking healthy. Checked once a minute (a small file read).
                if time.monotonic() - checked > 60:
                    checked = time.monotonic()
                    blocked = blocked_browsers()
                self._set_status(f"{', '.join(blocked)}에서 instagram.com 알림이 차단돼 있습니다" if blocked
                                 else "알림 읽는 중")
                current = {}
                for item in items:
                    current[item.id] = item
                if seen is not None:
                    for key in current.keys() - seen:
                        item = current[key]
                        app = ""
                        if item.app_info:
                            app = f"{item.app_info.display_info.display_name} {item.app_info.app_user_model_id}"
                        binding = item.notification.visual.get_binding(KnownNotificationBindings.toast_generic)
                        texts = [t.text or "" for t in binding.get_text_elements()] if binding else []
                        found = instagram_message(app, texts)
                        if found and found[0] == "Instagram":
                            self._log_shape(app, texts)
                        if found:
                            self._found.emit(*found)
                            if self.replace_toasts:
                                try:
                                    listener.remove_notification(key)
                                except Exception:
                                    pass  # already dismissed by the user; nothing to take over
                seen = set(current)
            except Exception as exc:  # keep polling; a single failed read is not fatal
                self._set_status(f"알림 읽기 오류 ({type(exc).__name__})")
            await asyncio.sleep(POLL_SECONDS)
