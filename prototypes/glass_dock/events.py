"""Calendar events for the clock module: kept on this PC, with reminders on the island.

An event: {id, date "YYYY-MM-DD", end (its last day, the same as date for one day),
time "HH:MM" ("" for all day), title, color, remind}.
`remind` is minutes before the start (-1 none; all-day events start at 09:00). A reminder
fires once: the fired ones are saved with the events, so a restart does not repeat them,
and one missed while the dock was off is shown at start only if it is under 10 min late.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

COLORS = ["#8FD0FF", "#7EE2A0", "#FFC861", "#FF7A70", "#C9A2FF", "#B8B8C4"]
ALL_DAY_AT = "09:00"
LATE_LIMIT = timedelta(minutes=10)
CHECK_MS = 15000
WEEKDAYS = "월화수목금토일"


def start_of(event: dict) -> datetime:
    return datetime.strptime(event["date"] + " " + (event.get("time") or ALL_DAY_AT), "%Y-%m-%d %H:%M")


def fire_time(event: dict) -> datetime | None:
    remind = int(event.get("remind", -1))
    return None if remind < 0 else start_of(event) - timedelta(minutes=remind)


def clean(values: dict) -> dict | None:
    """A valid event from user input, or None."""
    title = str(values.get("title", "")).strip()
    date = str(values.get("date", ""))
    end = str(values.get("end") or date)
    time = str(values.get("time", "")).strip()
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
        if time:
            time = datetime.strptime(time, "%H:%M").strftime("%H:%M")
        remind = int(values.get("remind", -1))
    except (ValueError, TypeError):
        return None
    color = str(values.get("color", COLORS[0]))
    if not title or remind < -1 or end < date:
        return None
    return dict(date=date, end=end, time=time, title=title[:80], color=color if color in COLORS else COLORS[0],
                remind=remind)


def span_text(event: dict) -> str:
    """"11/4–11/8" for an event over several days, "" for one day."""
    if event["end"] == event["date"]:
        return ""
    start, end = (datetime.strptime(d, "%Y-%m-%d") for d in (event["date"], event["end"]))
    return f"{start.month}/{start.day}–{end.month}/{end.day}"


def when_text(event: dict, now: datetime) -> str:
    """"오늘 14:30", "내일 하루 종일", "11월 7일 (금) 09:00"."""
    day = start_of(event).date()
    days = (day - now.date()).days
    label = "오늘" if days == 0 else "내일" if days == 1 else f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})"
    return label + " " + (event["time"] or span_text(event) or "하루 종일")


def due_text(event: dict, now: datetime) -> str:
    """Island subtitle: "10분 후 · 14:30", "지금 · 14:30", "내일 · 하루 종일"."""
    start = start_of(event)
    minutes = round((start - now).total_seconds() / 60)
    if not event["time"]:
        lead = "오늘" if start.date() == now.date() else "내일" if (start.date() - now.date()).days == 1 else when_text(event, now)
        return lead + " · 하루 종일"
    if minutes <= 0:
        lead = "지금"
    elif minutes < 60:
        lead = f"{minutes}분 후"
    elif minutes < 24 * 60:
        lead = f"{minutes // 60}시간{' ' + str(minutes % 60) + '분' if minutes % 60 else ''} 후"
    else:
        lead = when_text(event, now)
    return lead + " · " + event["time"]


class EventStore(QObject):
    changed = Signal()
    reminder = Signal(str, str, str)   # title, subtitle, color

    def __init__(self, path: Path, parent=None, *, clock=datetime.now, start=True):
        super().__init__(parent)
        self.path = Path(path)
        self.clock = clock
        self._events, self._fired = self._load()
        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_MS)
        self._timer.timeout.connect(self.check)
        if start:
            self._timer.start()
            QTimer.singleShot(2000, self.check)

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return [], set()
        events = []
        for raw in data.get("events", []) if isinstance(data, dict) else []:
            event = clean(raw) if isinstance(raw, dict) else None
            if event:
                events.append(dict(event, id=str(raw.get("id") or uuid.uuid4().hex[:12])))
        return events, set(data.get("fired", [])) if isinstance(data, dict) else set()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ids = {e["id"] for e in self._events}
        self._fired = {key for key in self._fired if key.split("@")[0] in ids}
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(dict(events=self._events, fired=sorted(self._fired)), ensure_ascii=False, indent=1),
                        encoding="utf-8")
        os.replace(temp, self.path)
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def colors(self):
        return COLORS

    @Property("QVariantMap", notify=changed)
    def marks(self):
        """{"YYYY-MM-DD": [color, ...]}: the calendar's dots for one-day events."""
        result: dict = {}
        for event in sorted(self._events, key=start_of):
            if event["end"] == event["date"]:
                result.setdefault(event["date"], []).append(event["color"])
        return result

    @Property("QVariantList", notify=changed)
    def ranges(self):
        """Events over several days, for the calendar's bars: [{id, date, end, color, title}]."""
        return [dict(e) for e in sorted(self._events, key=lambda e: (e["date"], e["end"])) if e["end"] != e["date"]]

    @Property("QVariantMap", notify=changed)
    def next(self):
        """The next event still to come (an all-day one counts for its whole day), with its "when" text."""
        now = self.clock()
        later = [e for e in self._events
                 if (start_of(e) >= now if e["time"] else start_of(e).date() >= now.date())]
        if not later:
            return {}
        event = min(later, key=start_of)
        return dict(event, when=when_text(event, now))

    @Slot(str, result="QVariantList")
    def forDay(self, date: str):
        """Events on `date`, an event over several days on each of them (with its "span" text)."""
        return sorted((dict(e, span=span_text(e)) for e in self._events if e["date"] <= date <= e["end"]),
                      key=lambda e: (e["date"] == e["end"], e["time"] != "", e["time"]))

    @Slot("QVariantMap", result=str)
    def save(self, values) -> str:
        """Add an event, or replace the one with values["id"]; returns its id ("" when invalid)."""
        event = clean(dict(values))
        if event is None:
            return ""
        event_id = str(values.get("id") or "")
        for index, old in enumerate(self._events):
            if old["id"] == event_id:
                self._events[index] = dict(event, id=event_id)
                break
        else:
            event_id = uuid.uuid4().hex[:12]
            self._events.append(dict(event, id=event_id))
        # A reminder moved into the future may fire again.
        fire = fire_time(event)
        if fire and fire > self.clock():
            self._fired.discard(f"{event_id}@{fire:%Y-%m-%d %H:%M}")
        self._save()
        return event_id

    @Slot(str)
    def remove(self, event_id: str):
        before = len(self._events)
        self._events = [e for e in self._events if e["id"] != event_id]
        if len(self._events) != before:
            self._save()

    @Slot()
    def check(self):
        now = self.clock()
        fired = False
        for event in sorted(self._events, key=start_of):
            fire = fire_time(event)
            key = f"{event['id']}@{fire:%Y-%m-%d %H:%M}" if fire else ""
            if not fire or key in self._fired or fire > now:
                continue
            self._fired.add(key)
            fired = True
            if now - fire <= LATE_LIMIT:
                self.reminder.emit(event["title"], due_text(event, now), event["color"])
        if fired:
            self._save()

    def stop(self):
        self._timer.stop()
