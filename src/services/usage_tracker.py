from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Callable

from services.settings_store import app_data_dir


class UsageTracker:
    """Track in-ear time. A session runs while at least one pod is in ear and connected."""

    def __init__(self, path: Path | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.path = path or app_data_dir() / "usage.json"
        self.clock = clock
        self.day = date.today().isoformat()
        self.persisted_seconds = 0.0
        self.session_seconds = 0.0
        self.active_since: float | None = None
        self._last_saved_at = self.clock()
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("date") == self.day:
                self.persisted_seconds = float(data.get("today_seconds", 0.0))
        except (OSError, ValueError, TypeError):
            pass

    def update(self, active: bool) -> None:
        self._roll_day_if_needed()
        now = self.clock()
        if active and self.active_since is None:
            self.active_since = now
        elif not active and self.active_since is not None:
            elapsed = max(0.0, now - self.active_since)
            self.persisted_seconds += elapsed
            self.session_seconds += elapsed
            self.active_since = None
            self.save()

    def tick(self) -> None:
        self._roll_day_if_needed()
        now = self.clock()
        if self.active_since is not None and now - self._last_saved_at >= 60.0:
            self.save()
            self._last_saved_at = now

    def totals(self) -> tuple[float, float]:
        running = 0.0 if self.active_since is None else max(0.0, self.clock() - self.active_since)
        return self.persisted_seconds + running, self.session_seconds + running

    def reset_session(self) -> None:
        self.session_seconds = 0.0
        if self.active_since is not None:
            self.active_since = self.clock()

    def save(self) -> None:
        today_seconds, _ = self.totals()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"date": self.day, "today_seconds": round(today_seconds, 3)}, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
        self._last_saved_at = self.clock()

    def _roll_day_if_needed(self) -> None:
        current_day = date.today().isoformat()
        if current_day == self.day:
            return
        self.day = current_day
        self.persisted_seconds = 0.0
        self.session_seconds = 0.0
        self.active_since = self.clock() if self.active_since is not None else None
        self.save()


def format_duration(seconds: float) -> str:
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes} min"
