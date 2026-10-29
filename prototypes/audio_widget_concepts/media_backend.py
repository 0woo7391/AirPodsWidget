"""Opt-in media bridge; never starts the legacy controller or controls unselected apps."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import queue
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, Property, QSettings, QStandardPaths, Signal, Slot, Qt
from PySide6.QtGui import QImageReader

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from services.media_service import MediaService


def empty_state():
    return dict(available=False, token="", identity="", title="", artist="", sourceName="",
                artwork="", playing=False, canPrevious=False, canNext=False, canPlay=False,
                pending=False, error="", status="허용 앱을 선택하세요")


def app_name(source):
    return source.rsplit("!", 1)[-1].removesuffix(".exe") or source


def image_url(data):
    """Validate and downsample off the UI thread; no artwork files accumulate."""
    if not data or len(data) > 4 * 1024 * 1024:
        return ""
    buffer = QBuffer()
    buffer.setData(QByteArray(data))
    buffer.open(QIODevice.ReadOnly)
    reader = QImageReader(buffer)
    size = reader.size()
    if not size.isValid() or size.width() > 4096 or size.height() > 4096:
        return ""
    if size.width() > 512 or size.height() > 512:
        reader.setScaledSize(size.scaled(512, 512, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return ""
    output = QBuffer()
    output.open(QIODevice.WriteOnly)
    if not image.save(output, "PNG"):
        return ""
    return "data:image/png;base64," + base64.b64encode(bytes(output.data())).decode("ascii")


async def read_artwork(reference):
    if reference is None:
        return ""
    from winrt.windows.storage.streams import DataReader
    stream = await asyncio.wait_for(reference.open_read_async(), 1)
    reader = None
    try:
        size = stream.size
        if not 0 < size <= 4 * 1024 * 1024:
            return ""
        reader = DataReader(stream)
        if await asyncio.wait_for(reader.load_async(size), 1) != size:
            return ""
        data = bytearray(size)
        reader.read_bytes(data)
        return image_url(data)
    finally:
        if reader is not None:
            reader.detach_stream()
            reader.close()
        stream.close()


class SelectedMediaService(MediaService):
    frameReceived = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._revision = 0
        self._policy = ((), "", "")
        self._inspect = False
        self._requests = queue.SimpleQueue()
        self._records = []
        self._serial = 0
        self._bound_revision = -1
        self._bound = ""
        self._ever_bound = False
        self._art_identity = ""
        self._artwork = ""
        self._art_deadline = 0
        self._loop = self._task = None

    def configure(self, allowed, source, token=""):
        with self._lock:
            self._revision += 1
            self._policy = (tuple(allowed), source, token)
            return self._revision

    def inspect(self, enabled):
        with self._lock:
            self._inspect = enabled

    def submit(self, request):
        self._requests.put(request)

    def _thread_main(self):
        try:
            super()._thread_main()
        except asyncio.CancelledError:
            pass

    def stop(self):
        self._stop.set()
        loop, task = self._loop, self._task
        if loop is not None and task is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass  # The worker may have finished between the check and scheduling.
        super().stop()

    async def _run(self):
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as SessionManager,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
        )
        self._loop, self._task = asyncio.get_running_loop(), asyncio.current_task()
        try:
            manager = await asyncio.wait_for(SessionManager.request_async(), 2)
            while not self._stop.is_set():
                self.frameReceived.emit(await self.tick(manager, PlaybackStatus))
                await asyncio.sleep(.35)
        finally:
            self._loop = self._task = None

    def _snapshot(self):
        with self._lock:
            return self._revision, self._policy, self._inspect

    def _sessions(self, manager):
        records = []
        for session in manager.get_sessions():
            source = session.source_app_user_model_id or ""
            if not isinstance(source, str) or not source or len(source) > 1024:
                continue
            prior = next((record for record in self._records if record[1] == session), None)
            if prior is None:
                self._serial += 1
                prior = (f"session-{self._serial}", session, source)
            records.append(prior)
        self._records = records
        return records

    async def _read_target(self, record, playback_status):
        state = empty_state()
        if record is None:
            return state
        token, session, source = record
        properties = await asyncio.wait_for(session.try_get_media_properties_async(), 1.5)
        if properties is None:
            return state
        media = await self._read_state(session, playback_status, properties)
        if not media.available:
            return state
        identity = token + ":" + hashlib.sha256(
            json.dumps([source, media.title, media.artist], ensure_ascii=False).encode()).hexdigest()
        if identity != self._art_identity:
            self._art_identity, self._artwork, self._art_deadline = identity, "", 0
        if time.monotonic() >= self._art_deadline:
            try:
                self._artwork = await read_artwork(getattr(properties, "thumbnail", None))
            except Exception:
                self._artwork = ""
            self._art_deadline = time.monotonic() + 5
        state.update(available=True, token=token, identity=identity, title=media.title,
                     artist=media.artist, sourceName=app_name(source), artwork=self._artwork,
                     playing=media.playing, canPrevious=media.can_previous,
                     canNext=media.can_next, canPlay=media.can_play_pause, status="선택한 미디어")
        return state

    async def tick(self, manager, playback_status):
        revision, (allowed, source, chosen), inspect = self._snapshot()
        records = self._sessions(manager)
        eligible = [record for record in records if record[2] == source and source in allowed]
        if self._bound_revision != revision:
            self._bound_revision, self._bound, self._ever_bound = revision, chosen, bool(chosen)
        if not self._bound and not self._ever_bound and len(eligible) == 1:
            self._bound, self._ever_bound = eligible[0][0], True
        target = next((record for record in eligible if record[0] == self._bound), None)
        state = await self._read_target(target, playback_status)
        if not state["available"]:
            state["status"] = ("허용 앱을 선택하세요" if not allowed else
                               "조작 대상을 선택하세요" if not source else
                               "여러 세션 중 대상을 선택하세요" if not self._bound and len(eligible) > 1 else
                               "선택한 미디어 없음")
        completed = 0
        while not self._requests.empty():
            request = self._requests.get_nowait()
            completed = request["id"]
            capability = {"toggle": "canPlay", "previous": "canPrevious", "next": "canNext"}.get(request["action"])
            current_revision = self._snapshot()[0]
            if (request["revision"] != revision or revision != current_revision
                    or request["token"] != state["token"] or request["identity"] != state["identity"]
                    or not state["available"] or not capability or not state[capability]
                    or not any(session == target[1] for session in manager.get_sessions())):
                state["error"] = "대상 또는 곡이 변경되어 조작을 취소함"
                continue
            try:
                if request["action"] == "toggle":
                    result = await asyncio.wait_for(self._toggle_play_pause(target[1], playback_status), 1.5)
                else:
                    method = (target[1].try_skip_previous_async if request["action"] == "previous"
                              else target[1].try_skip_next_async)
                    result = await asyncio.wait_for(method(), 1.5)
                if result is False:
                    state["error"] = "미디어 앱이 조작을 거부함"
                else:
                    confirmed = True
                    if request["action"] == "toggle":
                        wanted = not state["playing"]
                        deadline = time.monotonic() + 1.5
                        while (target[1].get_playback_info().playback_status == playback_status.PLAYING) != wanted:
                            if time.monotonic() >= deadline:
                                confirmed = False
                                break
                            await asyncio.sleep(.05)
                    state = await self._read_target(target, playback_status)
                    if not confirmed:
                        state["error"] = "재생 상태 변경을 확인하지 못함"
            except Exception as exc:
                state["error"] = f"미디어 조작 실패: {exc}"
        sessions = []
        for token, session, app_id in records:
            if app_id not in allowed:
                continue
            title = state["title"] if token == state["token"] else ""
            if inspect and token != state["token"]:
                try:
                    properties = await asyncio.wait_for(session.try_get_media_properties_async(), .5)
                    title = properties.title if properties else ""
                except Exception:
                    pass
            sessions.append(dict(token=token, sourceId=app_id, name=app_name(app_id), title=title))
        apps = sorted({record[2] for record in records})
        return dict(revision=revision, state=state, apps=apps, sessions=sessions, completed=completed)


class MediaBackend(QObject):
    changed = Signal()
    contentChanged = Signal()
    appsChanged = Signal()
    sessionsChanged = Signal()
    preferencesChanged = Signal()

    def __init__(self, service=None, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "media.ini"),
            QSettings.IniFormat)
        self._preferences = {"allowed": [], "sourceId": ""}
        try:
            saved = json.loads(self.settings.value("media/selection", "{}"))
            allowed = saved.get("allowed", [])
            if isinstance(allowed, list) and all(isinstance(value, str) and 0 < len(value) <= 1024 for value in allowed):
                self._preferences = {"allowed": list(dict.fromkeys(allowed)),
                                     "sourceId": saved.get("sourceId", "") if saved.get("sourceId", "") in allowed else ""}
        except (ValueError, TypeError, AttributeError):
            pass
        self._state, self._content = empty_state(), {}
        self._apps = [dict(id=value, name=app_name(value), present=False)
                      for value in self._preferences["allowed"]]
        self._sessions = []
        self._pending = self._command_serial = 0
        self._action_error = ""
        self._stopped = False
        self.service = service if service is not None else SelectedMediaService()
        self.service.frameReceived.connect(self._received)
        self.service.errorOccurred.connect(self._failed)
        self._revision = self.service.configure(self._preferences["allowed"], self._preferences["sourceId"])
        self._publish_content()
        self.service.start()

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state)

    @Property("QVariantMap", notify=contentChanged)
    def content(self):
        return dict(self._content)

    @Property("QVariantList", notify=appsChanged)
    def apps(self):
        return self._apps

    @Property("QVariantList", notify=sessionsChanged)
    def sessions(self):
        return self._sessions

    @Property("QVariantMap", notify=preferencesChanged)
    def preferences(self):
        return dict(self._preferences)

    def _publish_content(self):
        content = {key: self._state[key] for key in
                   ("available", "token", "identity", "title", "artist", "sourceName", "artwork")}
        if content != self._content:
            self._content = content
            self.contentChanged.emit()

    @Slot(object)
    def _received(self, frame):
        if self._stopped or frame["revision"] != self._revision:
            return
        old_token = self._state["token"]
        self._state = dict(frame["state"])
        if self._state["error"]:
            self._action_error = self._state["error"]
        elif old_token != self._state["token"]:
            self._action_error = ""
        self._state["error"] = self._action_error
        if frame["completed"] == self._pending or old_token != self._state["token"]:
            self._pending = 0
        self._state["pending"] = bool(self._pending)
        apps = [dict(id=value, name=app_name(value), present=value in frame["apps"])
                for value in sorted(set(frame["apps"]) | set(self._preferences["allowed"]))]
        if apps != self._apps:
            self._apps = apps
            self.appsChanged.emit()
        if frame["sessions"] != self._sessions:
            self._sessions = frame["sessions"]
            self.sessionsChanged.emit()
        self._publish_content()
        self.changed.emit()

    @Slot(str)
    def _failed(self, message):
        if self._stopped:
            return
        self._pending = 0
        self._action_error = ""
        while not self.service._requests.empty():
            self.service._requests.get_nowait()
        self._state = {**empty_state(), "status": "미디어 확인 필요", "error": message}
        if self._sessions:
            self._sessions = []
            self.sessionsChanged.emit()
        self._publish_content()
        self.changed.emit()

    @Slot(bool)
    def inspectSessions(self, enabled):
        self.service.inspect(enabled)

    @Slot("QVariantList", str, str, result=bool)
    def saveSelection(self, allowed, source, token):
        known = {app["id"] for app in self._apps} | set(self._preferences["allowed"])
        if (not all(isinstance(value, str) and value in known for value in allowed)
                or (source and source not in allowed)
                or (token and not any(item["token"] == token and item["sourceId"] == source
                                      for item in self._sessions))):
            self._action_error = self._state["error"] = "목록이 바뀌었음 · 대상을 다시 선택하세요"
            self.changed.emit()
            return False
        preference = {"allowed": list(dict.fromkeys(allowed)), "sourceId": source}
        previous = self.settings.value("media/selection", None)
        self.settings.setValue("media/selection", json.dumps(preference, ensure_ascii=False))
        self.settings.sync()
        if self.settings.status() != QSettings.NoError:
            if previous is None:
                self.settings.remove("media/selection")
            else:
                self.settings.setValue("media/selection", previous)
            self.settings.sync()
            self._action_error = self._state["error"] = "미디어 선택을 저장하지 못함 · 기존 설정 유지"
            self.changed.emit()
            return False
        self._preferences = preference
        self._revision = self.service.configure(preference["allowed"], source, token)
        self._pending = 0
        self._action_error = ""
        self._state = {**empty_state(), "status": "선택한 미디어 확인 중" if source else "허용 앱을 선택하세요"}
        self._publish_content()
        self.preferencesChanged.emit()
        self.changed.emit()
        return True

    @Slot(str, str, str)
    def command(self, action, token, identity):
        capability = {"toggle": "canPlay", "previous": "canPrevious", "next": "canNext"}.get(action)
        if (self._stopped or self._pending or not self._state["available"] or not capability
                or not self._state[capability] or token != self._state["token"]
                or identity != self._state["identity"]):
            return
        self._command_serial += 1
        self._pending = self._command_serial
        self._action_error = ""
        self._state.update(pending=True, error="")
        self.changed.emit()
        self.service.submit(dict(id=self._pending, revision=self._revision, action=action,
                                 token=token, identity=identity))

    @Slot()
    def stop(self):
        if not self._stopped:
            self._stopped = True
            self.service.stop()
