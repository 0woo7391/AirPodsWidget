"""AirPods features of the old widget, wired to the dock's backends.

Connect/disconnect/low-battery notices (island + warning sound), pause when a
bud leaves the ear and resume when both return, in-ear time, game-aware
suppression and start with Windows. Settings come from DockPrefs (prefs.py).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from services.game_detector import is_game_foreground
from services.startup_manager import set_start_with_windows
from services.usage_tracker import UsageTracker, format_duration

# Same defaults as the old widget (services/settings_store.py).
GAME_PROCESSES = ["League of Legends.exe", "LeagueClient.exe", "LeagueClientUx.exe",
                  "VALORANT-Win64-Shipping.exe"]
ESTIMATED_MAX_LISTENING_MINUTES = 8 * 60
PART_NAMES = {"L": "왼쪽", "R": "오른쪽", "CASE": "케이스", "C": "케이스"}


class DockFeatures(QObject):
    notice = Signal(str, str, str, "QVariantList")   # title, subtitle, tone, batteries -> island
    usageChanged = Signal()

    def __init__(self, devices, media, prefs, sound_file: Path, *, usage_path: Path | None = None, parent=None):
        super().__init__(parent)
        self.devices, self.media, self.prefs = devices, media, prefs
        self.settings = prefs.settings
        prefs.changed.connect(self._on_pref)
        self.sound_file = sound_file
        self._alert = None   # created on first use; QtMultimedia is slow to load
        self.usage = UsageTracker(usage_path) if usage_path else UsageTracker()
        self._connected = bool(devices.state.get("connected"))
        self._warned: set[str] = set()
        self._ear = self._ear_state()          # (any, both) or None when unknown
        self._ear_generation = 0
        self._paused_by_ear = False
        devices.changed.connect(self._on_device)
        devices.batteriesChanged.connect(self._on_batteries)
        self._usage_timer = QTimer(self)
        self._usage_timer.setInterval(30_000)
        self._usage_timer.timeout.connect(self._tick_usage)
        self._usage_timer.start()
        self._update_usage()
        self._apply_follow_any()

    # Settings ---------------------------------------------------------------
    def get(self, key):
        return self.prefs.get(key)

    def set(self, key, value):
        self.prefs.set(key, value)

    def _on_pref(self, key):
        if key == "system/startWithWindows":
            set_start_with_windows(self.get(key), app_name="GlassDock")
        elif key == "media/followAny":
            self._apply_follow_any()

    def _apply_follow_any(self):
        if hasattr(self.media, "setFollowAny"):   # the real backend; demo media has one fixed track
            self.media.setFollowAny(self.get("media/followAny"))

    def apply_startup(self):
        """Refresh the Run entry so it points at this executable after a move or update."""
        if self.get("system/startWithWindows"):
            set_start_with_windows(True, app_name="GlassDock")

    def game_active(self) -> bool:
        processes = self.settings.value("system/gameProcesses", GAME_PROCESSES)
        return is_game_foreground(processes if isinstance(processes, list) else [processes])

    def _notify(self, subtitle, tone, batteries, title=None):
        if self.get("island/suppressDuringGames") and self.game_active():
            return
        self.notice.emit(title or self.devices.state.get("name") or "AirPods", subtitle, tone, batteries)

    @Slot(bool)
    def on_mic(self, muted):
        """The microphone was switched (from the dock, a hotkey or another app)."""
        if self.get("island/mic"):
            self._notify("꺼짐" if muted else "켜짐", "micOff" if muted else "micOn", [], title="마이크")


    # Connection and battery -------------------------------------------------
    def _on_device(self):
        now = bool(self.devices.state.get("connected"))
        if now and not self._connected and self.get("island/connect"):
            self._notify("연결됨", "connected", list(self.devices.batteries))
        elif self._connected and not now:
            self._warned.clear()
            if self.get("island/disconnect"):
                self._notify("연결 해제됨", "disconnected", [])
        self._connected = now
        self._update_usage()

    def _on_batteries(self):
        self._check_low_battery()
        self._check_ear()
        self._update_usage()

    def _check_low_battery(self):
        """Warn once per part at or below the threshold; again only after charging or 10 points above it."""
        threshold = self.get("battery/threshold")
        low = []
        for part in self.devices.batteries:
            label, value, charging = part.get("label"), part.get("value", -1), part.get("charging")
            if value >= 0 and not charging and value <= threshold:
                if label not in self._warned:
                    self._warned.add(label)
                    low.append(f"{PART_NAMES.get(label, label)} {value}%")
            elif charging or value >= threshold + 10:
                self._warned.discard(label)
        if not low or not self._connected:
            return
        if self.get("battery/sound") and (self.get("battery/soundDuringGames") or not self.game_active()):
            self.play_alert()
        if self.get("island/lowBattery"):
            self._notify("배터리 부족 · " + ", ".join(low), "low", list(self.devices.batteries))

    @Slot()
    def play_alert(self):
        if not self.sound_file.exists():
            return  # the MP3 is user-supplied (README); no file, no sound
        if self._alert is None:
            from services.alert_service import AlertService
            self._alert = AlertService(self.sound_file, self)
        self._alert.set_volume(self.get("battery/soundVolume"))
        self._alert.play()

    # Ear detection ----------------------------------------------------------
    def _ear_state(self):
        buds = [p for p in self.devices.batteries if p.get("label") in ("L", "R")]
        if not any(p.get("quality") == "fresh" for p in buds):
            return None
        in_ear = [bool(p.get("inEar")) for p in buds]
        return any(in_ear), bool(in_ear) and all(in_ear)

    def _check_ear(self):
        previous, current = self._ear, self._ear_state()
        if current is None:
            return  # no fresh reading: neither removal nor return
        self._ear = current
        if previous is None or not self._connected:
            return
        self._ear_generation += 1
        generation = self._ear_generation
        if previous[0] and not current[0] and self.get("media/autoPause"):
            QTimer.singleShot(600, lambda: self._confirm_pause(generation))
        elif not previous[1] and current[1] and self._paused_by_ear and self.get("media/autoResume"):
            QTimer.singleShot(800, lambda: self._confirm_resume(generation))

    def _media_command(self, action):
        state = self.media.state
        self.media.command(action, state.get("token", ""), state.get("identity", ""))

    def _confirm_pause(self, generation):
        if generation == self._ear_generation and self._ear and not self._ear[0] and self.media.state.get("playing"):
            self._media_command("pause")
            self._paused_by_ear = True

    def _confirm_resume(self, generation):
        if generation == self._ear_generation and self._ear and self._ear[1] and self._paused_by_ear:
            self._media_command("play")
            self._paused_by_ear = False

    # In-ear time --------------------------------------------------------------
    def _update_usage(self):
        self.usage.update(self._connected and bool(self._ear and self._ear[0]))
        self.usageChanged.emit()

    def _tick_usage(self):
        self.usage.tick()
        self.usageChanged.emit()

    def save(self):
        self.usage.update(False)
        self.usage.save()

    @Property(str, notify=usageChanged)
    def todayUsage(self):
        return format_duration(self.usage.totals()[0])

    @Property(str, notify=usageChanged)
    def sessionUsage(self):
        return format_duration(self.usage.totals()[1])

    @Property(str, notify=usageChanged)
    def remainingUsage(self):
        values = [p.get("value", -1) for p in self.devices.batteries if p.get("label") in ("L", "R")]
        values = [v for v in values if v >= 0]
        if not values or not self._connected:
            return ""
        minutes = max(0, int(round(min(values) / 100 * ESTIMATED_MAX_LISTENING_MINUTES / 5) * 5))
        return format_duration(minutes * 60)
