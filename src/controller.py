from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from models import AirPodsState, MediaState
from services.alert_service import AlertService
from services.audio_output import (
    AudioOutput,
    AudioOutputError,
    active_outputs,
    current_volume,
    current_output,
    find_airpods,
    find_headphones,
    find_speaker,
    known_outputs,
    set_default_output,
    set_volume,
)
from services.ble_service import BleService
from services.bluetooth_status import find_airpods_status
from services.game_detector import is_game_foreground
from services.low_battery import LowBatteryPolicy
from services.media_service import MediaService
from services.settings_store import SettingsStore
from services.startup_manager import set_start_with_windows
from services.usage_tracker import UsageTracker, format_duration
from services.windows_material import apply_window_material, apply_window_shape

LOGGER = logging.getLogger(__name__)
ESTIMATED_MAX_LISTENING_MINUTES = 8 * 60


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


class AppController(QObject):
    airpodsChanged = Signal()
    mediaChanged = Signal()
    usageChanged = Signal()
    settingsChanged = Signal()
    testPlayingChanged = Signal()
    scannerRunningChanged = Signal()
    audioChanged = Signal()
    gameChanged = Signal()

    showTrayPopupRequested = Signal(int, int)
    showSettingsRequested = Signal(int, int)
    showConnectionPopupRequested = Signal(int, int)
    showLowBatteryPopupRequested = Signal(int, int)

    def __init__(self, app: QApplication, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self.settings = SettingsStore()
        self._airpods = AirPodsState()
        self._media = MediaState()
        self._connected_device_name = ""
        self._test_playing = False
        self._scanner_running = False
        self._popup_title = ""
        self._popup_message = ""
        self._popup_detail = ""
        self._ear_generation = 0
        self._paused_by_ear_detection = False
        self._connection_popup_pending = False
        self._bluetooth_present_polls = 0
        self._bluetooth_missing_polls = 0
        self._audio_output_id = ""
        self._audio_output_name = "오디오 출력 확인 중"
        self._audio_output_is_airpods = False
        self._audio_output_available = False
        self._audio_target_id = ""
        self._audio_target_name = ""
        self._audio_outputs: list[AudioOutput] = []
        self._audio_known_outputs: list[AudioOutput] = []
        self._airpods_paired = False
        self._audio_button_configs: list[dict[str, str]] | None = None
        self._audio_volume = -1
        self._audio_volume_available = False
        self._audio_devices_signature: tuple[tuple[str, str], ...] = ()
        self._audio_feedback = ""
        self._demo_mode = "--demo" in sys.argv
        self._demo_step = 0
        self._game_foreground = False

        if not self._demo_mode:
            try:
                paired_status = find_airpods_status()
                self._airpods_paired = bool(
                    paired_status is not None and paired_status.paired
                )
            except OSError:
                # Systems without an available Bluetooth radio can still use
                # the widget's media, volume, and wired-output features.
                self._airpods_paired = False

        self.usage = UsageTracker()
        battery_threshold = int(self.settings.get("battery", "threshold", 10))
        self.low_battery = LowBatteryPolicy(
            threshold=battery_threshold,
            reset_threshold=max(20, battery_threshold + 10),
        )
        self.alerts = AlertService(resource_path("assets/low_power_warning.mp3"), self)
        self.alerts.set_volume(int(self.settings.get("battery", "volume", 60)))
        self.alerts.playingChanged.connect(self._set_test_playing)
        self.alerts.playbackError.connect(LOGGER.warning)

        self.ble = BleService(rssi_min=int(self.settings.get("system", "rssi_min", -85)), parent=self)
        self.ble.stateReceived.connect(self._on_airpods_state)
        self.ble.deviceLost.connect(self._on_airpods_lost)
        self.ble.errorOccurred.connect(LOGGER.warning)
        self.ble.scannerRunningChanged.connect(self._set_scanner_running)

        self.media = MediaService(self)
        self.media.stateReceived.connect(self._on_media_state)
        self.media.errorOccurred.connect(LOGGER.warning)

        self._usage_timer = QTimer(self)
        self._usage_timer.setInterval(5000)
        self._usage_timer.timeout.connect(self._tick_usage)

        self._bluetooth_timer = QTimer(self)
        self._bluetooth_timer.setInterval(2000)
        self._bluetooth_timer.timeout.connect(self._poll_bluetooth_connection)

        self._audio_timer = QTimer(self)
        self._audio_timer.setInterval(3000)
        self._audio_timer.timeout.connect(self._refresh_audio_output)

        self._audio_volume_timer = QTimer(self)
        self._audio_volume_timer.setInterval(500)
        self._audio_volume_timer.timeout.connect(self._refresh_audio_volume)

        self._audio_feedback_timer = QTimer(self)
        self._audio_feedback_timer.setSingleShot(True)
        self._audio_feedback_timer.setInterval(1400)
        self._audio_feedback_timer.timeout.connect(self._clear_audio_feedback)

        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(300)
        self._settings_save_timer.timeout.connect(self.settings.save)

        self._ensure_widget_position_visible()
        self._tray = self._create_tray()
        self._refresh_audio_output()

    def start(self) -> None:
        self._usage_timer.start()
        self._tray.show()
        if self._demo_mode:
            self._start_demo()
            return
        self._audio_timer.start()
        self._audio_volume_timer.start()
        self.ble.start()
        self.media.start()
        self._bluetooth_timer.start()
        self._poll_bluetooth_connection()

    def shutdown(self) -> None:
        self._usage_timer.stop()
        self._bluetooth_timer.stop()
        self._audio_timer.stop()
        self._audio_volume_timer.stop()
        self._audio_feedback_timer.stop()
        self.usage.update(False)
        self.usage.save()
        self._settings_save_timer.stop()
        self.settings.save()
        if not self._demo_mode:
            self.ble.stop()
            self.media.stop()
        self._tray.hide()

    # --- AirPods properties -------------------------------------------------
    @Property(str, notify=airpodsChanged)
    def deviceName(self) -> str:
        return self._connected_device_name or self._airpods.device_name or "AirPods Pro 3"

    @Property(bool, notify=airpodsChanged)
    def connected(self) -> bool:
        return self._airpods.connected

    @Property(bool, notify=airpodsChanged)
    def detected(self) -> bool:
        return self._airpods.detected

    @Property(str, notify=airpodsChanged)
    def connectionLabel(self) -> str:
        if self._airpods.connected:
            return "연결됨"
        if self._airpods.detected:
            return "근처에서 감지됨"
        return "연결 안 됨"

    @Property(int, notify=airpodsChanged)
    def leftBattery(self) -> int:
        return self._airpods.left.battery.percent if self._airpods.left.battery.percent is not None else -1

    @Property(int, notify=airpodsChanged)
    def rightBattery(self) -> int:
        return self._airpods.right.battery.percent if self._airpods.right.battery.percent is not None else -1

    @Property(int, notify=airpodsChanged)
    def caseBattery(self) -> int:
        return self._airpods.case.battery.percent if self._airpods.case.battery.percent is not None else -1

    @Property(bool, notify=airpodsChanged)
    def leftInEar(self) -> bool:
        return self._airpods.left.in_ear

    @Property(bool, notify=airpodsChanged)
    def rightInEar(self) -> bool:
        return self._airpods.right.in_ear

    @Property(bool, notify=airpodsChanged)
    def leftCharging(self) -> bool:
        return self._airpods.left.battery.charging

    @Property(bool, notify=airpodsChanged)
    def rightCharging(self) -> bool:
        return self._airpods.right.battery.charging

    @Property(bool, notify=airpodsChanged)
    def caseCharging(self) -> bool:
        return self._airpods.case.battery.charging

    # --- Audio output -------------------------------------------------------
    @Property(str, notify=audioChanged)
    def audioOutputName(self) -> str:
        return self._audio_output_name

    @Property(bool, notify=audioChanged)
    def audioOutputIsAirPods(self) -> bool:
        return self._audio_output_is_airpods

    @Property(bool, notify=audioChanged)
    def audioOutputAvailable(self) -> bool:
        return self._audio_output_available

    @Property(str, notify=audioChanged)
    def audioOutputAction(self) -> str:
        if self._audio_output_available:
            return "스피커로" if self._audio_output_is_airpods else "AirPods로"
        if self._audio_output_is_airpods:
            return "스피커 없음"
        return "AirPods 필요"

    @Property(str, notify=audioChanged)
    def audioOutputFeedback(self) -> str:
        return self._audio_feedback

    @Property(list, notify=audioChanged)
    def audioOutputDevices(self) -> list[dict[str, str]]:
        return [{"deviceId": "", "name": "장치 선택"}] + [
            {"deviceId": item.device_id, "name": item.name}
            for item in self._selectable_audio_outputs()
        ]

    @Property(list, notify=audioChanged)
    def audioOutputButtons(self) -> list[dict[str, object]]:
        if self._audio_button_configs is None:
            return []
        outputs = {item.device_id: item for item in self._audio_known_outputs}
        active_ids = {item.device_id for item in self._audio_outputs}
        buttons: list[dict[str, object]] = []
        for index, config in enumerate(self._audio_button_configs):
            device_id = config.get("device_id", "")
            output = outputs.get(device_id)
            name = output.name if output else config.get("name", "")
            kind = output.kind if output else config.get("kind", "speaker")
            paired_airpods = kind == "airpods" and self._airpods_paired
            buttons.append(
                {
                    "index": index,
                    "deviceId": device_id,
                    "name": name or "장치 선택",
                    "kind": kind,
                    "available": bool(
                        device_id
                        and (device_id in active_ids or paired_airpods)
                    ),
                    "current": bool(output and device_id == self._audio_output_id),
                }
            )
        return buttons

    @Property(int, notify=audioChanged)
    def audioVolume(self) -> int:
        return self._audio_volume

    @Property(bool, notify=audioChanged)
    def audioVolumeAvailable(self) -> bool:
        return self._audio_volume_available

    # --- Usage --------------------------------------------------------------
    @Property(str, notify=usageChanged)
    def todayUsage(self) -> str:
        return format_duration(self.usage.totals()[0])

    @Property(str, notify=usageChanged)
    def sessionUsage(self) -> str:
        return format_duration(self.usage.totals()[1])

    @Property(str, notify=airpodsChanged)
    def estimatedRemainingUsage(self) -> str:
        minutes = self._estimated_remaining_minutes()
        if minutes is None:
            return "—"
        hours, remainder = divmod(minutes, 60)
        if hours:
            return f"{hours}h {remainder:02d}m"
        return f"{remainder}m"

    # --- Media --------------------------------------------------------------
    @Property(bool, notify=mediaChanged)
    def mediaAvailable(self) -> bool:
        return self._media.available and bool(self.settings.get("media", "visible", True))

    @Property(str, notify=mediaChanged)
    def mediaTitle(self) -> str:
        return self._media.title

    @Property(str, notify=mediaChanged)
    def mediaSubtitle(self) -> str:
        pieces = [part for part in (self._media.artist, self._media.source_app) if part]
        return " · ".join(pieces)

    @Property(bool, notify=mediaChanged)
    def mediaPlaying(self) -> bool:
        return self._media.playing

    @Property(bool, notify=mediaChanged)
    def canPrevious(self) -> bool:
        return self._media.can_previous

    @Property(bool, notify=mediaChanged)
    def canNext(self) -> bool:
        return self._media.can_next

    @Property(bool, notify=mediaChanged)
    def canPlayPause(self) -> bool:
        return self._media.can_play_pause

    @Property(float, notify=mediaChanged)
    def mediaPosition(self) -> float:
        return self._media.position_seconds

    @Property(float, notify=mediaChanged)
    def mediaDuration(self) -> float:
        return self._media.duration_seconds

    @Property(bool, notify=mediaChanged)
    def mediaSeekable(self) -> bool:
        return self._media.seekable

    @Slot(QObject)
    def applyWindowMaterial(self, window: QObject) -> None:
        apply_window_material(window, self.theme == "dark")

    @Slot(QObject)
    def updateWindowShape(self, window: QObject) -> None:
        apply_window_shape(window)

    # --- Settings -----------------------------------------------------------
    @Property(bool, notify=settingsChanged)
    def widgetVisible(self) -> bool:
        return bool(self.settings.get("widget", "visible", True))

    @Property(bool, notify=settingsChanged)
    def widgetLocked(self) -> bool:
        return bool(self.settings.get("widget", "locked", False))

    @Property(bool, notify=settingsChanged)
    def widgetAlwaysOnTop(self) -> bool:
        # Demo previews should remain visible while being inspected, without
        # changing the user's persisted stacking preference.
        return self._demo_mode or bool(self.settings.get("widget", "always_on_top", False))

    @Property(float, notify=settingsChanged)
    def widgetOpacity(self) -> float:
        return float(self.settings.get("widget", "opacity", 0.90))

    @Property(float, notify=settingsChanged)
    def widgetScale(self) -> float:
        return float(self.settings.get("widget", "scale", 1.0))

    @Property(bool, notify=gameChanged)
    def gameActive(self) -> bool:
        return self._game_foreground

    @Property(int, notify=settingsChanged)
    def widgetX(self) -> int:
        return int(self.settings.get("widget", "x", 72))

    @Property(int, notify=settingsChanged)
    def widgetY(self) -> int:
        return int(self.settings.get("widget", "y", 72))

    @Property(str, notify=settingsChanged)
    def theme(self) -> str:
        if self._demo_mode and "--demo-light" in sys.argv:
            return "light"
        return str(self.settings.get("widget", "theme", "dark"))

    @Property(bool, notify=settingsChanged)
    def batteryAlertEnabled(self) -> bool:
        return bool(self.settings.get("battery", "alert_enabled", True))

    @Property(int, notify=settingsChanged)
    def batteryThreshold(self) -> int:
        return int(self.settings.get("battery", "threshold", 10))

    @Property(int, notify=settingsChanged)
    def alertVolume(self) -> int:
        return int(self.settings.get("battery", "volume", 60))


    @Property(bool, notify=settingsChanged)
    def mediaVisibleSetting(self) -> bool:
        return bool(self.settings.get("media", "visible", True))

    @Property(bool, notify=settingsChanged)
    def autoPause(self) -> bool:
        return bool(self.settings.get("media", "auto_pause", True))

    @Property(bool, notify=settingsChanged)
    def autoResume(self) -> bool:
        return bool(self.settings.get("media", "auto_resume", False))

    @Property(bool, notify=settingsChanged)
    def connectionPopupEnabled(self) -> bool:
        return bool(self.settings.get("popup", "connection_enabled", True))

    @Property(bool, notify=settingsChanged)
    def suppressPopupsDuringGames(self) -> bool:
        return bool(self.settings.get("popup", "suppress_during_games", True))

    @Property(bool, notify=settingsChanged)
    def startWithWindows(self) -> bool:
        return bool(self.settings.get("system", "start_with_windows", False))

    @Property(bool, notify=testPlayingChanged)
    def testPlaying(self) -> bool:
        return self._test_playing

    @Property(bool, notify=scannerRunningChanged)
    def scannerRunning(self) -> bool:
        return self._scanner_running

    @Property(str, notify=airpodsChanged)
    def popupTitle(self) -> str:
        return self._popup_title

    @Property(str, notify=airpodsChanged)
    def popupMessage(self) -> str:
        return self._popup_message

    @Property(str, notify=airpodsChanged)
    def popupDetail(self) -> str:
        return self._popup_detail

    # --- UI commands --------------------------------------------------------
    @Slot()
    def togglePlayPause(self) -> None:
        if self._demo_mode:
            self._media.playing = not self._media.playing
            self.mediaChanged.emit()
            return
        self.media.toggle_play_pause()

    @Slot()
    def previousTrack(self) -> None:
        if self._demo_mode:
            self._media.title = "Ditto"
            self._media.artist = "NewJeans"
            self.mediaChanged.emit()
            return
        self.media.previous()

    @Slot()
    def nextTrack(self) -> None:
        if self._demo_mode:
            self._media.title = "The Adults Are Talking — A Very Long Track Title for Marquee Preview"
            self._media.artist = "The Strokes"
            self._media.position_seconds = 0.0
            self.mediaChanged.emit()
            return
        self.media.next()

    @Slot(float)
    def seekMedia(self, position_seconds: float) -> None:
        if not self.mediaSeekable and not self._demo_mode:
            return
        if self._demo_mode:
            self._media.position_seconds = max(
                0.0, min(self._media.duration_seconds, float(position_seconds))
            )
            self.mediaChanged.emit()
            return
        self.media.seek(position_seconds)

    @Slot()
    def showSettings(self) -> None:
        popup_x, popup_y = self._centered_popup_position(480, 700)
        self.showSettingsRequested.emit(popup_x, popup_y)

    @Slot()
    def toggleAudioOutput(self) -> None:
        if self._demo_mode:
            self._audio_output_is_airpods = not self._audio_output_is_airpods
            self._audio_output_name = "AirPods Pro 3 (데모)" if self._audio_output_is_airpods else "스피커 (데모)"
            self._audio_feedback = "출력 전환됨"
            self._audio_feedback_timer.start()
            self.audioChanged.emit()
            return

        try:
            outputs = active_outputs()
            current = current_output()
            if current.is_airpods:
                target = find_speaker(outputs, exclude_id=current.device_id)
            else:
                target = find_airpods(outputs)
            if target is None:
                self._set_audio_feedback("전환할 장치 없음")
                return
            set_default_output(target.device_id)
            self._set_audio_feedback("출력 전환됨")
            self._refresh_audio_output()
        except AudioOutputError as exc:
            LOGGER.warning("Audio output switch failed: %s", exc)
            self._set_audio_feedback("전환하지 못함")
        except Exception:
            LOGGER.exception("Unexpected audio output switch failure")
            self._set_audio_feedback("전환하지 못함")

    @Slot(str)
    def selectAudioOutput(self, device_id: str) -> None:
        if not device_id:
            return
        if self._demo_mode:
            output = next((item for item in self._audio_known_outputs if item.device_id == device_id), None)
            if output is None:
                return
            self._audio_output_id = output.device_id
            self._audio_output_name = output.name
            self._audio_output_is_airpods = output.is_airpods
            self._audio_output_available = True
            self._audio_volume_available = True
            self._set_audio_feedback("출력 전환됨")
            self.audioChanged.emit()
            return

        try:
            output = next(
                (item for item in self._audio_known_outputs if item.device_id == device_id),
                None,
            )
            config = next(
                (
                    item
                    for item in (self._audio_button_configs or [])
                    if item.get("device_id") == device_id
                ),
                None,
            )
            paired_airpods = bool(
                config
                and config.get("kind") == "airpods"
                and self._airpods_paired
            )
            if output is None and not paired_airpods:
                self._set_audio_feedback("연결되지 않음")
                return
            set_default_output(output.device_id if output is not None else device_id)
            self._set_audio_feedback("출력 전환됨")
            self._refresh_audio_output()
        except AudioOutputError as exc:
            LOGGER.warning("Audio output switch failed: %s", exc)
            self._set_audio_feedback("전환하지 못함")
        except Exception:
            LOGGER.exception("Unexpected audio output switch failure")
            self._set_audio_feedback("전환하지 못함")

    @Slot(int)
    def setAudioVolume(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        if not self._audio_volume_available:
            return
        if self._demo_mode:
            self._audio_volume = value
            self.audioChanged.emit()
            return
        try:
            set_volume(value)
            self._audio_volume = value
            self.audioChanged.emit()
        except Exception:
            LOGGER.exception("Audio volume update failed")

    @Slot(int, str)
    def setAudioOutputButton(self, index: int, device_id: str) -> None:
        if self._audio_button_configs is None or not 0 <= index < len(self._audio_button_configs):
            return
        output = next((item for item in self._audio_known_outputs if item.device_id == device_id), None)
        previous = self._audio_button_configs[index]
        if output is None:
            self._audio_button_configs[index] = {
                "device_id": "",
                "name": "",
                "kind": previous.get("kind", "speaker"),
            }
        else:
            self._audio_button_configs[index] = {
                "device_id": output.device_id,
                "name": output.name,
                "kind": output.kind,
            }
        self._save_audio_button_configs()

    @Slot()
    def addAudioOutputButton(self) -> None:
        if self._audio_button_configs is None:
            self._audio_button_configs = []
        if len(self._audio_button_configs) >= 3:
            return
        self._audio_button_configs.append({"device_id": "", "name": "", "kind": "speaker"})
        self._save_audio_button_configs()

    @Slot(int)
    def removeAudioOutputButton(self, index: int) -> None:
        if self._audio_button_configs is None or not 0 <= index < len(self._audio_button_configs):
            return
        self._audio_button_configs.pop(index)
        self._save_audio_button_configs()

    @Slot()
    def toggleWidget(self) -> None:
        self.settings.set("widget", "visible", not self.widgetVisible)
        self.settingsChanged.emit()

    @Slot(bool)
    def setWidgetVisible(self, value: bool) -> None:
        self.settings.set("widget", "visible", value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setWidgetLocked(self, value: bool) -> None:
        self.settings.set("widget", "locked", value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setWidgetAlwaysOnTop(self, value: bool) -> None:
        self.settings.set("widget", "always_on_top", bool(value))
        self.settingsChanged.emit()

    @Slot(float)
    def setWidgetOpacity(self, value: float) -> None:
        self.settings.set("widget", "opacity", round(max(0.55, min(1.0, value)), 2), save=False)
        self._schedule_settings_save()
        self.settingsChanged.emit()

    @Slot(float)
    def setWidgetScale(self, value: float) -> None:
        self.settings.set("widget", "scale", round(max(0.7, min(1.5, value)), 2), save=False)
        self._schedule_settings_save()
        self.settingsChanged.emit()

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value not in {"dark", "light"}:
            return
        self.settings.set("widget", "theme", value)
        self.settingsChanged.emit()

    @Slot(int, int)
    def saveWidgetPosition(self, x: int, y: int) -> None:
        self.settings.set("widget", "x", x, save=False)
        self.settings.set("widget", "y", y, save=True)

    @Slot(bool)
    def setBatteryAlertEnabled(self, value: bool) -> None:
        self.settings.set("battery", "alert_enabled", value)
        self.settingsChanged.emit()

    @Slot(int)
    def setBatteryThreshold(self, value: int) -> None:
        value = max(10, min(30, value))
        self.settings.set("battery", "threshold", value, save=False)
        self._schedule_settings_save()
        self.low_battery.threshold = value
        self.low_battery.reset_threshold = min(100, value + 10)
        self.settings.set("battery", "reset_threshold", self.low_battery.reset_threshold, save=False)
        self.low_battery.reset()
        self.settingsChanged.emit()

    @Slot(int)
    def setAlertVolume(self, value: int) -> None:
        value = max(0, min(100, value))
        self.settings.set("battery", "volume", value, save=False)
        self._schedule_settings_save()
        self.alerts.set_volume(value)
        self.settingsChanged.emit()

    @Slot()
    def testAlert(self) -> None:
        self.alerts.set_volume(self.alertVolume)
        self.alerts.play()

    @Slot(bool)
    def setMediaVisible(self, value: bool) -> None:
        self.settings.set("media", "visible", value)
        self.settingsChanged.emit()
        self.mediaChanged.emit()

    @Slot(bool)
    def setAutoPause(self, value: bool) -> None:
        self.settings.set("media", "auto_pause", value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setAutoResume(self, value: bool) -> None:
        self.settings.set("media", "auto_resume", value)
        self.settingsChanged.emit()


    @Slot(bool)
    def setConnectionPopupEnabled(self, value: bool) -> None:
        self.settings.set("popup", "connection_enabled", value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setSuppressPopupsDuringGames(self, value: bool) -> None:
        self.settings.set("popup", "suppress_during_games", value)
        self.settingsChanged.emit()

    @Slot(bool)
    def setStartWithWindows(self, value: bool) -> None:
        set_start_with_windows(value)
        self.settings.set("system", "start_with_windows", value)
        self.settingsChanged.emit()

    @Slot()
    def quit(self) -> None:
        self._app.quit()

    # --- Internal -----------------------------------------------------------
    def _save_audio_button_configs(self) -> None:
        self.settings.set(
            "audio",
            "buttons",
            self._audio_button_configs or [],
            save=False,
        )
        self._schedule_settings_save()
        self.audioChanged.emit()

    def _ensure_audio_button_configs(self, outputs: list[AudioOutput]) -> None:
        if self._audio_button_configs is not None:
            return

        stored = self.settings.get("audio", "buttons", None)
        if stored is None:
            configs: list[dict[str, str]] = []
            candidates = [
                find_airpods(outputs),
                find_speaker(outputs),
                find_headphones(outputs),
            ]
            seen: set[str] = set()
            for output in candidates:
                if output is not None and output.device_id not in seen:
                    configs.append(
                        {
                            "device_id": output.device_id,
                            "name": output.name,
                            "kind": output.kind,
                        }
                    )
                    seen.add(output.device_id)
            if not configs and outputs:
                output = outputs[0]
                configs.append(
                    {"device_id": output.device_id, "name": output.name, "kind": output.kind}
                )
            self._audio_button_configs = configs
            self.settings.set("audio", "buttons", configs, save=False)
            self._schedule_settings_save()
            return

        configs = []
        if isinstance(stored, list):
            for item in stored:
                if isinstance(item, str):
                    configs.append({"device_id": item, "name": "", "kind": "speaker"})
                elif isinstance(item, dict):
                    configs.append(
                        {
                            "device_id": str(item.get("device_id", "")),
                            "name": str(item.get("name", "")),
                            "kind": str(item.get("kind", "speaker")),
                        }
                    )
        self._audio_button_configs = configs

    def _refresh_audio_output(self) -> None:
        if self._demo_mode:
            return
        try:
            current = current_output()
            outputs = active_outputs()
            remembered_outputs = known_outputs()
            self._audio_outputs = outputs
            self._audio_known_outputs = remembered_outputs
            setup_outputs = list(outputs)
            paired_airpods = find_airpods(remembered_outputs)
            if (
                self._airpods_paired
                and paired_airpods is not None
                and all(item.device_id != paired_airpods.device_id for item in setup_outputs)
            ):
                setup_outputs.append(paired_airpods)
            self._ensure_audio_button_configs(setup_outputs)
            volume = current_volume()
            device_signature = tuple(
                (item.device_id, item.name) for item in remembered_outputs
            )
            if current.is_airpods:
                target = find_speaker(outputs, exclude_id=current.device_id)
            else:
                target = find_airpods(outputs)
            values = (
                current.device_id,
                current.name,
                current.is_airpods,
                target.device_id if target else "",
                target.name if target else "",
                volume,
                device_signature,
            )
            previous = (
                self._audio_output_id,
                self._audio_output_name,
                self._audio_output_is_airpods,
                self._audio_target_id,
                self._audio_target_name,
                self._audio_volume,
                self._audio_devices_signature,
            )
            (
                self._audio_output_id,
                self._audio_output_name,
                self._audio_output_is_airpods,
                self._audio_target_id,
                self._audio_target_name,
                self._audio_volume,
                self._audio_devices_signature,
            ) = values
            self._audio_output_available = True
            self._audio_volume_available = True
            if values != previous:
                self.audioChanged.emit()
        except Exception:
            LOGGER.exception("Audio output refresh failed")
            if (
                self._audio_output_name != "오디오 출력 확인 불가"
                or self._audio_output_available
                or self._audio_volume_available
            ):
                self._audio_output_name = "오디오 출력 확인 불가"
                self._audio_output_available = False
                self._audio_volume_available = False
                self._audio_outputs = []
                self._audio_known_outputs = []
                self._audio_target_id = ""
                self._audio_target_name = ""
                self.audioChanged.emit()

    def _refresh_audio_volume(self) -> None:
        """Refresh only the scalar volume without re-enumerating endpoints."""
        if self._demo_mode or not self._audio_volume_available:
            return
        try:
            volume = current_volume()
        except Exception:
            return
        if volume != self._audio_volume:
            self._audio_volume = volume
            self.audioChanged.emit()

    def _selectable_audio_outputs(self) -> list[AudioOutput]:
        """Keep settings useful without exposing every stale Windows endpoint."""
        selected_ids = {
            str(item.get("device_id", ""))
            for item in (self._audio_button_configs or [])
            if item.get("device_id")
        }
        active_ids = {item.device_id for item in self._audio_outputs}
        airpods = find_airpods(self._audio_known_outputs) if self._airpods_paired else None
        allowed_ids = active_ids | selected_ids
        if airpods is not None:
            allowed_ids.add(airpods.device_id)

        result: list[AudioOutput] = []
        seen: set[str] = set()
        for item in [*self._audio_outputs, *self._audio_known_outputs]:
            if item.device_id in allowed_ids and item.device_id not in seen:
                result.append(item)
                seen.add(item.device_id)
        return result

    def _set_audio_feedback(self, text: str) -> None:
        self._audio_feedback = text
        self._audio_feedback_timer.start()
        self.audioChanged.emit()

    def _clear_audio_feedback(self) -> None:
        if self._audio_feedback:
            self._audio_feedback = ""
            self.audioChanged.emit()

    def _on_airpods_state(self, state: AirPodsState) -> None:
        state.connected = self._airpods.connected
        state.device_name = self._connected_device_name or state.model_name
        previous_any = self._airpods.any_in_ear
        previous_both = self._airpods.both_in_ear
        self._airpods = state
        self.airpodsChanged.emit()
        self._handle_ear_detection(previous_any, previous_both)
        self._update_usage_active()
        self._handle_low_battery()
        if state.connected and self._connection_popup_pending:
            self._connection_popup_pending = False
            self._maybe_show_connection_popup()

    def _on_airpods_lost(self) -> None:
        # BLE advertisement loss is not a Bluetooth connection loss. Keep the
        # last known battery/ear state so a scan gap does not flash empty data
        # or look like a fresh connection when advertisements resume.
        if self._airpods.detected:
            self._airpods.detected = False
            self.airpodsChanged.emit()
        self._update_usage_active()

    def _on_media_state(self, state: MediaState) -> None:
        self._media = state
        self.mediaChanged.emit()

    def _handle_ear_detection(self, previous_any: bool, previous_both: bool) -> None:
        current_any = self._airpods.any_in_ear
        self._ear_generation += 1
        generation = self._ear_generation

        if previous_any and not current_any and self.settings.get("media", "auto_pause", True):
            QTimer.singleShot(600, lambda: self._confirm_auto_pause(generation))
        elif (
            not previous_both
            and self._airpods.both_in_ear
            and self.settings.get("media", "auto_resume", False)
            and self._paused_by_ear_detection
        ):
            QTimer.singleShot(800, lambda: self._confirm_auto_resume(generation))

    def _confirm_auto_pause(self, generation: int) -> None:
        if generation == self._ear_generation and not self._airpods.any_in_ear and self._media.playing:
            self.media.pause()
            self._paused_by_ear_detection = True

    def _confirm_auto_resume(self, generation: int) -> None:
        if (
            generation == self._ear_generation
            and self._airpods.both_in_ear
            and self._paused_by_ear_detection
        ):
            self.media.play()
            self._paused_by_ear_detection = False

    def _handle_low_battery(self) -> None:
        if not self.batteryAlertEnabled or not self._airpods.connected:
            return
        triggered = self.low_battery.evaluate(self._airpods)
        if not triggered:
            return

        game_active = is_game_foreground(self.settings.get("system", "game_processes", []))
        if not game_active or self.settings.get("battery", "sound_during_games", True):
            self.alerts.play()

        popup_allowed = self.settings.get("battery", "popup_enabled", True) and (
            not game_active or self.settings.get("battery", "popup_during_games", False)
        )
        if popup_allowed:
            labels = {"left": "왼쪽", "right": "오른쪽", "case": "케이스"}
            summary = " · ".join(f"{labels[name]} {value}%" for name, value in triggered)
            self._popup_title = "AirPods 배터리 부족"
            self._popup_message = summary
            self._popup_detail = "충전이 필요합니다"
            self.airpodsChanged.emit()
            popup_x, popup_y = self._notification_position(346, 118)
            self.showLowBatteryPopupRequested.emit(popup_x, popup_y)

    def _poll_bluetooth_connection(self) -> None:
        self._refresh_game_foreground()
        device_status = find_airpods_status()
        paired = device_status is not None and device_status.paired
        if paired != self._airpods_paired:
            self._airpods_paired = paired
            self.audioChanged.emit()

        device = (
            device_status
            if device_status is not None and device_status.connected
            else None
        )
        if device is not None:
            self._bluetooth_present_polls += 1
            self._bluetooth_missing_polls = 0
            if not self._airpods.connected and self._bluetooth_present_polls < 2:
                return
        else:
            self._bluetooth_missing_polls += 1
            self._bluetooth_present_polls = 0
            if self._airpods.connected and self._bluetooth_missing_polls < 3:
                return

        connected = device is not None
        was_connected = self._airpods.connected
        self._connected_device_name = device.name if device else self._connected_device_name
        if connected != was_connected or (device and self._airpods.device_name != device.name):
            self._airpods.connected = connected
            if device:
                self._airpods.device_name = device.name
            self.airpodsChanged.emit()
            self._update_usage_active()

        if connected and not was_connected:
            self._connection_popup_pending = True
            self._handle_low_battery()
            if self._airpods.detected:
                self._connection_popup_pending = False
                self._maybe_show_connection_popup()
        elif not connected and was_connected:
            self._connection_popup_pending = False
            self._paused_by_ear_detection = False
            self.usage.reset_session()
            self.usageChanged.emit()

    def _refresh_game_foreground(self) -> None:
        active = is_game_foreground(self.settings.get("system", "game_processes", []))
        if active != self._game_foreground:
            self._game_foreground = active
            self.gameChanged.emit()

    def _maybe_show_connection_popup(self) -> None:
        if not self.settings.get("popup", "connection_enabled", True):
            return
        game_active = is_game_foreground(self.settings.get("system", "game_processes", []))
        if game_active and self.settings.get("popup", "suppress_during_games", True):
            return
        values = [
            f"L {self.leftBattery}%" if self.leftBattery >= 0 else "L —",
            f"R {self.rightBattery}%" if self.rightBattery >= 0 else "R —",
            f"Case {self.caseBattery}%" if self.caseBattery >= 0 else "Case —",
        ]
        self._popup_title = self.deviceName
        self._popup_message = " · ".join(values)
        self._popup_detail = "연결됨"
        self.airpodsChanged.emit()
        popup_x, popup_y = self._notification_position(346, 118)
        self.showConnectionPopupRequested.emit(popup_x, popup_y)

    def _update_usage_active(self) -> None:
        self.usage.update(self._airpods.connected and self._airpods.any_in_ear)
        self.usageChanged.emit()

    def _tick_usage(self) -> None:
        self.usage.tick()
        self.usageChanged.emit()

    def _set_test_playing(self, value: bool) -> None:
        if self._test_playing != value:
            self._test_playing = value
            self.testPlayingChanged.emit()

    def _set_scanner_running(self, value: bool) -> None:
        if self._scanner_running != value:
            self._scanner_running = value
            self.scannerRunningChanged.emit()

    def _estimated_remaining_minutes(self) -> int | None:
        percentages = [
            value
            for value in (self.leftBattery, self.rightBattery)
            if value >= 0
        ]
        if not percentages:
            return None
        raw_minutes = min(percentages) / 100.0 * ESTIMATED_MAX_LISTENING_MINUTES
        return max(0, int(round(raw_minutes / 5.0) * 5))

    def _schedule_settings_save(self) -> None:
        self._settings_save_timer.start()

    def _start_demo(self) -> None:
        self._airpods = AirPodsState(
            model_id=0x2027,
            model_name="AirPods Pro 3",
            device_name="AirPods Pro 3",
            detected=True,
            connected=True,
        )
        self._airpods.left.battery.percent = 87
        self._airpods.right.battery.percent = 82
        self._airpods.case.battery.percent = 64
        self._airpods.left.in_ear = True
        self._airpods.right.in_ear = True
        self._airpods.case.battery.charging = True
        self._media = MediaState(
            available=True,
            title="The Adults Are Talking — A Very Long Track Title for Marquee Preview",
            artist="The Strokes",
            source_app="Spotify",
            playing=True,
            can_previous=True,
            can_next=True,
            can_play_pause=True,
            position_seconds=42.0,
            duration_seconds=754.0,
            seekable=True,
        )
        self._audio_outputs = [
            AudioOutput("demo-airpods", "AirPods Pro 3"),
            AudioOutput("demo-speaker", "스피커"),
            AudioOutput("demo-headphones", "헤드폰"),
        ]
        self._audio_known_outputs = list(self._audio_outputs)
        self._airpods_paired = True
        self._audio_button_configs = [
            {"device_id": "demo-airpods", "name": "AirPods Pro 3", "kind": "airpods"},
            {"device_id": "demo-speaker", "name": "스피커", "kind": "speaker"},
            {"device_id": "demo-headphones", "name": "헤드폰", "kind": "headphones"},
        ]
        self._audio_output_id = "demo-speaker"
        self._audio_output_name = "스피커 (데모)"
        self._audio_output_is_airpods = False
        self._audio_output_available = True
        self._audio_volume = 62
        self._audio_volume_available = True
        self._audio_feedback = ""
        self.airpodsChanged.emit()
        self.mediaChanged.emit()
        self.audioChanged.emit()
        self._update_usage_active()
        timer = QTimer(self)
        timer.setInterval(5000)
        timer.timeout.connect(self._advance_demo)
        timer.start()
        self._demo_timer = timer

    def _advance_demo(self) -> None:
        self._demo_step += 1
        if self._demo_step % 2:
            self._airpods.left.battery.percent = max(0, (self._airpods.left.battery.percent or 0) - 1)
            self._media.playing = not self._media.playing
        else:
            self._airpods.right.battery.percent = max(0, (self._airpods.right.battery.percent or 0) - 1)
            self._media.title = (
                "Ditto" if self._media.title.startswith("The Adults")
                else "The Adults Are Talking — A Very Long Track Title for Marquee Preview"
            )
            self._media.artist = "NewJeans" if self._media.title == "Ditto" else "The Strokes"
        if self._media.playing:
            self._media.position_seconds = min(
                self._media.duration_seconds,
                self._media.position_seconds + 5.0,
            )
        self.airpodsChanged.emit()
        self.mediaChanged.emit()

    def _create_tray(self) -> QSystemTrayIcon:
        icon = self._make_tray_icon()
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip("AirPods Widget")
        tray.activated.connect(self._on_tray_activated)
        menu = QMenu()
        menu.addAction("위젯 표시/숨기기", self.toggleWidget)
        menu.addAction("설정", self.showSettings)
        menu.addSeparator()
        menu.addAction("종료", self.quit)
        tray.setContextMenu(menu)
        return tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            height = 528 if self.mediaAvailable else 394
            popup_x, popup_y = self._tray_popup_position(360, height)
            self.showTrayPopupRequested.emit(popup_x, popup_y)

    @staticmethod
    def _screen_geometry_at_cursor():
        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        return point, screen.availableGeometry()

    @classmethod
    def _tray_popup_position(cls, width: int, height: int) -> tuple[int, int]:
        point, geometry = cls._screen_geometry_at_cursor()
        x = max(geometry.left() + 10, min(point.x() - width + 16, geometry.right() - width - 10))
        y = max(geometry.top() + 10, min(point.y() - height - 14, geometry.bottom() - height - 10))
        return x, y

    @classmethod
    def _notification_position(cls, width: int, height: int) -> tuple[int, int]:
        _point, geometry = cls._screen_geometry_at_cursor()
        return geometry.right() - width - 24, geometry.bottom() - height - 24

    @classmethod
    def _centered_popup_position(cls, width: int, height: int) -> tuple[int, int]:
        _point, geometry = cls._screen_geometry_at_cursor()
        x = geometry.left() + max(10, (geometry.width() - width) // 2)
        y = geometry.top() + max(10, (geometry.height() - height) // 2)
        return x, y

    def _ensure_widget_position_visible(self) -> None:
        x = int(self.settings.get("widget", "x", 72))
        y = int(self.settings.get("widget", "y", 72))
        point = QPoint(x, y)
        if any(screen.availableGeometry().contains(point) for screen in QGuiApplication.screens()):
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.settings.set("widget", "x", geometry.left() + 72, save=False)
        self.settings.set("widget", "y", geometry.top() + 72, save=True)

    @staticmethod
    def _make_tray_icon() -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("#F5F5F7"))
        painter.setBrush(QColor("#151517"))
        painter.drawRoundedRect(5, 5, 54, 54, 16, 16)
        painter.setPen(QColor("#F5F5F7"))
        painter.setBrush(QColor("#F5F5F7"))
        painter.drawRoundedRect(17, 20, 30, 5, 2.5, 2.5)
        painter.drawRoundedRect(17, 30, 23, 5, 2.5, 2.5)
        painter.drawRoundedRect(17, 40, 16, 5, 2.5, 2.5)
        painter.end()
        return QIcon(pixmap)
