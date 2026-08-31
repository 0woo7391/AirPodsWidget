import asyncio
from datetime import timedelta

from services.media_service import MediaService


class FakeProperties:
    title = "A Song"
    artist = "An Artist"


class FakeControls:
    is_previous_enabled = True
    is_next_enabled = False
    is_play_enabled = False
    is_pause_enabled = True
    is_play_pause_toggle_enabled = True
    is_playback_position_enabled = True


class FakePlayback:
    def __init__(self, status="playing"):
        self.controls = FakeControls()
        self.playback_status = status


class FakePlaybackStatus:
    PLAYING = "playing"
    PAUSED = "paused"


class FakeTimeline:
    start_time = timedelta(0)
    position = timedelta(seconds=42)
    end_time = timedelta(seconds=754)
    min_seek_time = timedelta(0)
    max_seek_time = timedelta(seconds=754)


class FakeSession:
    source_app_user_model_id = "Spotify.exe!Spotify"

    def __init__(self, status="playing"):
        self.calls = []
        self.playback_status = status

    async def try_get_media_properties_async(self):
        return FakeProperties()

    def get_playback_info(self):
        return FakePlayback(self.playback_status)

    def get_timeline_properties(self):
        return FakeTimeline()

    async def try_toggle_play_pause_async(self):
        self.calls.append("toggle")

    async def try_play_async(self):
        self.calls.append("play")

    async def try_pause_async(self):
        self.calls.append("pause")

    async def try_skip_previous_async(self):
        self.calls.append("previous")

    async def try_skip_next_async(self):
        self.calls.append("next")

    async def try_change_playback_position_async(self, ticks):
        self.calls.append(("seek", ticks))


class FakeSessionManager:
    def __init__(self, current, sessions):
        self.current = current
        self.sessions = sessions

    def get_current_session(self):
        return self.current

    def get_sessions(self):
        return self.sessions


def test_read_state_maps_media_properties_and_capabilities():
    state = asyncio.run(MediaService._read_state(FakeSession(), FakePlaybackStatus))

    assert state.available is True
    assert state.title == "A Song"
    assert state.artist == "An Artist"
    assert state.source_app == "Spotify"
    assert state.playing is True
    assert state.can_previous is True
    assert state.can_next is False
    assert state.can_play_pause is True
    assert state.position_seconds == 42
    assert state.duration_seconds == 754
    assert state.seekable is True


def test_commands_are_delivered_in_order():
    service = MediaService()
    session = FakeSession()
    service.toggle_play_pause()
    service.play()
    service.pause()
    service.previous()
    service.next()
    service.seek(42.5)

    asyncio.run(service._drain_commands(session))

    assert session.calls == [
        "toggle",
        "play",
        "pause",
        "previous",
        "next",
        ("seek", 425000000),
    ]


def test_toggle_uses_explicit_pause_for_a_playing_session():
    service = MediaService()
    session = FakeSession(status="playing")

    asyncio.run(service._drain_commands(session, FakePlaybackStatus))

    service.toggle_play_pause()
    asyncio.run(service._drain_commands(session, FakePlaybackStatus))

    assert session.calls == ["pause"]


def test_select_session_prefers_the_session_that_is_playing():
    stale = FakeSession(status="paused")
    active = FakeSession(status="playing")
    manager = FakeSessionManager(stale, [stale, active])

    selected = asyncio.run(MediaService._select_session(manager, FakePlaybackStatus))

    assert selected is active


def test_stopped_session_does_not_leave_old_media_visible():
    state = asyncio.run(MediaService._read_state(FakeSession(status="stopped"), FakePlaybackStatus))

    assert state.available is False
    assert state.title == ""


def test_media_identity_distinguishes_tabs_from_the_same_browser():
    first = asyncio.run(MediaService._read_state(FakeSession(), FakePlaybackStatus))
    second = asyncio.run(MediaService._read_state(FakeSession(), FakePlaybackStatus))
    second.title = "A Different Video"

    assert MediaService._media_identity(first) != MediaService._media_identity(second)
