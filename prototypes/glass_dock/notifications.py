"""Instagram DMs from Windows notifications.

Reads the toasts Windows shows (UserNotificationListener; Windows asks the user
once to allow it) and passes on the ones from Instagram: the Instagram app, or
instagram.com notifications from a browser. Nothing logs in to Instagram.
Polls every two seconds; toasts already there when it starts are not news.
"""
from __future__ import annotations

import asyncio
import threading
import time

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

BROWSERS = ("chrome", "msedge", "edge", "whale", "brave", "opera", "firefox", "vivaldi")
POLL_SECONDS = 2.0
MAX_RECENT = 20
INBOX_URL = "https://www.instagram.com/direct/inbox/"


def instagram_message(app: str, texts: list[str]):
    """(sender, content) when a toast is an Instagram message, else None.

    Browser toasts carry [title, body, "instagram.com"]; the title is the sender, or
    "Instagram" with the body as "sender: message".
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
    if title.lower() == "instagram" and ":" in body:
        sender, _, content = body.partition(":")
        return sender.strip() or "Instagram", content.strip()
    return title, body


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
        self._found.connect(self.add)

    @Slot(str, str)
    def add(self, sender, content):
        self._messages.insert(0, dict(sender=sender, content=content, time=time.time() * 1000))
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

    @Slot()
    def openInbox(self):
        self.markRead()
        QDesktopServices.openUrl(QUrl(INBOX_URL))

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

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
        self._set_status("알림 읽는 중")
        seen = None
        while not self._stop.is_set():
            try:
                items = await listener.get_notifications_async(NotificationKinds.TOAST)
                self._set_status("알림 읽는 중")
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
                        if found:
                            self._found.emit(*found)
                seen = set(current)
            except Exception as exc:  # keep polling; a single failed read is not fatal
                self._set_status(f"알림 읽기 오류 ({type(exc).__name__})")
            await asyncio.sleep(POLL_SECONDS)
