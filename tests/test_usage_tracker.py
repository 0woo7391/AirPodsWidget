from pathlib import Path

from services.usage_tracker import UsageTracker, format_duration


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def test_tracks_active_time_and_persists(tmp_path: Path):
    clock = Clock()
    tracker = UsageTracker(tmp_path / "usage.json", clock=clock)
    tracker.update(True)
    clock.value = 125
    today, session = tracker.totals()
    assert today == 125
    assert session == 125
    tracker.update(False)
    assert tracker.totals() == (125, 125)


def test_format_duration():
    assert format_duration(59) == "0 min"
    assert format_duration(61) == "1 min"
    assert format_duration(3660) == "1h 01m"


def test_periodically_persists_active_usage(tmp_path: Path):
    clock = Clock()
    path = tmp_path / "usage.json"
    tracker = UsageTracker(path, clock=clock)
    tracker.update(True)
    clock.value = 59
    tracker.tick()
    assert not path.exists()
    clock.value = 60
    tracker.tick()
    loaded = UsageTracker(path, clock=clock)
    assert loaded.totals()[0] == 60
