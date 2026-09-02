from __future__ import annotations

import asyncio
import queue
import threading
from datetime import timedelta
from typing import Any

from PySide6.QtCore import QObject, Signal

from models import MediaState


class MediaService(QObject):
    stateReceived = Signal(object)
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._commands: queue.SimpleQueue[tuple[str, float | None]] = queue.SimpleQueue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="WindowsMedia", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def toggle_play_pause(self) -> None:
        self._commands.put(("toggle", None))

    def play(self) -> None:
        self._commands.put(("play", None))

    def pause(self) -> None:
        self._commands.put(("pause", None))

    def previous(self) -> None:
        self._commands.put(("previous", None))

    def next(self) -> None:
        self._commands.put(("next", None))

    def seek(self, position_seconds: float) -> None:
        self._commands.put(("seek", max(0.0, float(position_seconds))))

    def _thread_main(self) -> None:
        while not self._stop.is_set():
            try:
                asyncio.run(self._run())
            except Exception as exc:
                if not self._stop.is_set():
                    self.errorOccurred.emit(f"Media service: {exc}")
            if not self._stop.wait(5.0):
                continue

    async def _run(self) -> None:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as SessionManager,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
        )

        manager = await SessionManager.request_async()
        last_state: MediaState | None = None
        last_playing_media: tuple[str, str, str] | None = None
        last_session: Any = None
        while not self._stop.is_set():
            session = await self._select_session(
                manager,
                PlaybackStatus,
                preferred_session=last_session,
            )
            await self._drain_commands(session, PlaybackStatus)
            state = await self._read_state(session, PlaybackStatus)
            media_identity = self._media_identity(state)
            if state.playing:
                last_playing_media = media_identity
                last_session = session
            elif state.available and media_identity != last_playing_media:
                # Do not resurrect a paused browser tab that was already old
                # when the widget started. Browser tabs share one source-app
                # id, so source + title + artist identify the observed media.
                state = MediaState()
            elif state.available:
                # Keep the last playing session as the control target while it
                # is paused. Some browser builds temporarily stop returning a
                # paused session from GetCurrentSession().
                last_session = session
            elif session is None:
                last_session = None
            if state != last_state:
                last_state = state
                self.stateReceived.emit(state)
            await asyncio.sleep(0.35)

    @staticmethod
    def _media_identity(state: MediaState) -> tuple[str, str, str]:
        return (state.source_app, state.title, state.artist)

    @staticmethod
    async def _select_session(
        manager: Any,
        playback_status_type: Any,
        preferred_session: Any = None,
    ) -> Any:
        """Prefer the session that is actually playing over stale current metadata.

        Windows can keep a paused or stopped browser session as
        ``get_current_session()`` while another app is actively playing. It can
        also briefly return no paused browser session after a pause command. The
        media widget follows the active session and uses the last known session
        as a paused fallback without resurrecting an unrelated old tab.
        """
        try:
            current = manager.get_current_session()
        except Exception:
            current = None

        try:
            sessions = list(manager.get_sessions())
        except Exception:
            sessions = []

        candidates = []
        if current is not None:
            candidates.append(current)
        if preferred_session is not None and preferred_session is not current:
            candidates.append(preferred_session)
        candidates.extend(session for session in sessions if session is not current)

        playing = []
        paused_preferred = None
        paused_current = None
        paused_status = getattr(playback_status_type, "PAUSED", None)
        for session in candidates:
            try:
                status = session.get_playback_info().playback_status
            except Exception:
                continue
            if status == playback_status_type.PLAYING:
                playing.append(session)
            elif paused_status is not None and status == paused_status:
                if session is preferred_session:
                    paused_preferred = session
                if session is current:
                    paused_current = session

        if playing:
            return playing[0]
        return paused_preferred or paused_current

    async def _drain_commands(self, session: Any, playback_status_type: Any = None) -> None:
        while True:
            try:
                command, value = self._commands.get_nowait()
            except queue.Empty:
                break
            if session is None:
                continue
            try:
                if command == "toggle":
                    result = await self._toggle_play_pause(session, playback_status_type)
                elif command == "play":
                    result = await session.try_play_async()
                elif command == "pause":
                    result = await session.try_pause_async()
                elif command == "previous":
                    result = await session.try_skip_previous_async()
                elif command == "next":
                    result = await session.try_skip_next_async()
                elif command == "seek" and value is not None:
                    result = await session.try_change_playback_position_async(
                        _seconds_to_ticks(value)
                    )
                else:
                    continue
                if result is False:
                    self.errorOccurred.emit(
                        f"Media command '{command}' was rejected by the active session"
                    )
            except Exception as exc:
                self.errorOccurred.emit(f"Media command '{command}': {exc}")

    @staticmethod
    async def _toggle_play_pause(session: Any, playback_status_type: Any) -> Any:
        """Use the explicit play/pause command when a session exposes it.

        Some browser sessions advertise only one side of the toggle capability.
        Sending the matching explicit command is more reliable than always using
        TryTogglePlayPauseAsync, while the test/source fallback still supports
        older projections that do not expose playback status types.
        """
        if playback_status_type is None:
            return await session.try_toggle_play_pause_async()
        playback = session.get_playback_info()
        controls = playback.controls
        if (
            playback.playback_status == playback_status_type.PLAYING
            and getattr(controls, "is_pause_enabled", False)
        ):
            return await session.try_pause_async()
        if (
            playback.playback_status != playback_status_type.PLAYING
            and getattr(controls, "is_play_enabled", False)
        ):
            return await session.try_play_async()
        return await session.try_toggle_play_pause_async()

    @staticmethod
    async def _read_state(session: Any, playback_status_type: Any) -> MediaState:
        if session is None:
            return MediaState()
        try:
            playback = session.get_playback_info()
            playback_status = playback.playback_status
            is_playing = playback_status == playback_status_type.PLAYING
            paused_status = getattr(playback_status_type, "PAUSED", None)
            is_paused = paused_status is not None and playback_status == paused_status
            if not (is_playing or is_paused):
                return MediaState()

            properties = await session.try_get_media_properties_async()
            if properties is None:
                return MediaState()
            controls = playback.controls
            try:
                timeline = session.get_timeline_properties()
            except Exception:
                timeline = None

            position_seconds = 0.0
            duration_seconds = 0.0
            seekable = False
            if timeline is not None:
                start = _timespan_seconds(timeline.start_time)
                position = _timespan_seconds(timeline.position)
                end = _timespan_seconds(timeline.end_time)
                min_seek = _timespan_seconds(timeline.min_seek_time)
                max_seek = _timespan_seconds(timeline.max_seek_time)
                duration_seconds = max(0.0, end - start)
                position_seconds = max(
                    0.0, min(duration_seconds, position - start)
                )
                seekable = bool(
                    getattr(controls, "is_playback_position_enabled", True)
                    and duration_seconds > 0
                    and max_seek > min_seek
                )

            source = session.source_app_user_model_id or ""
            source = source.rsplit("!", 1)[-1].replace(".exe", "")
            return MediaState(
                available=bool(properties.title or properties.artist) and (is_playing or is_paused),
                title=properties.title or "",
                artist=properties.artist or "",
                source_app=source,
                playing=is_playing,
                can_previous=bool(controls.is_previous_enabled),
                can_next=bool(controls.is_next_enabled),
                can_play_pause=bool(
                    getattr(controls, "is_play_enabled", False)
                    or getattr(controls, "is_pause_enabled", False)
                    or getattr(controls, "is_play_pause_toggle_enabled", False)
                ),
                position_seconds=position_seconds,
                duration_seconds=duration_seconds,
                seekable=seekable,
            )
        except Exception:
            return MediaState()


def _timespan_seconds(value: Any) -> float:
    if isinstance(value, timedelta):
        return max(0.0, value.total_seconds())
    if hasattr(value, "total_seconds"):
        return max(0.0, float(value.total_seconds()))
    if hasattr(value, "duration"):
        return max(0.0, float(value.duration) / 10_000_000.0)
    if hasattr(value, "ticks"):
        return max(0.0, float(value.ticks) / 10_000_000.0)
    return 0.0


def _seconds_to_ticks(seconds: float) -> int:
    return int(max(0.0, seconds) * 10_000_000)
