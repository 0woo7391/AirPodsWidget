"""Output-only bridge. No tray, BLE scanner, media watcher or startup hook."""
from __future__ import annotations

import json
import queue
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSettings, QStandardPaths, QThread, QTimer, Signal, Slot


class _OutputWorker(QThread):
    completed = Signal(object)

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.commands = queue.Queue()

    def read_state(self):
        service = self.service
        outputs = service.active_outputs()
        current = service.current_output()
        first = service.find_airpods(outputs) or current
        second = service.find_speaker(outputs, exclude_id=first.device_id)
        if second is None:
            second = next((item for item in outputs if item.device_id != first.device_id), None)
        volume = service.current_volume(device_id=current.device_id)
        muted = service.current_mute(device_id=current.device_id)
        if service.current_output().device_id != current.device_id:
            raise RuntimeError("출력 장치가 변경됨 · 다시 확인 중")
        return {"available": True, "currentId": current.device_id, "name": current.name, "kind": current.kind,
                "volume": volume, "muted": muted,
                "suggestedIds": [first.device_id] + ([second.device_id] if second else []),
                "devices": [{"id": item.device_id, "name": item.name, "kind": item.kind,
                             "available": True} for item in outputs]}

    def run(self):
        while True:
            command = self.commands.get()
            if command is None:
                return
            error, state = "", None
            try:
                target = command.get("id", "")
                if command["kind"] == "select":
                    if target not in {item.device_id for item in self.service.active_outputs()}:
                        raise RuntimeError("현재 사용할 수 없는 출력 장치")
                    if self.service.current_output().device_id != target:
                        self.service.set_default_output(target)
                    deadline = time.monotonic() + 1.5
                    while self.service.current_output().device_id != target:
                        if time.monotonic() >= deadline:
                            raise RuntimeError("출력 전환을 확인하지 못함")
                        time.sleep(.05)
                elif command["kind"] == "write":
                    # Target the endpoint itself, never whichever device became default later.
                    if self.service.current_output().device_id != target:
                        raise RuntimeError("출력 장치가 바뀌어 이전 조작을 취소함")
                    if "volume" in command:
                        self.service.set_volume(command["volume"], device_id=target)
                    self.service.set_mute(command["muted"], device_id=target)
                state = self.read_state()
                if command["kind"] == "select" and state["currentId"] != target:
                    raise RuntimeError("출력 전환을 확인하지 못함")
            except Exception as exc:
                error = str(exc)
                try:
                    state = self.read_state()
                except Exception:
                    pass
            self.completed.emit({"command": command, "state": state, "error": error})


class AudioBackend(QObject):
    changed = Signal()
    devicesChanged = Signal()
    quickOutputsChanged = Signal()

    def __init__(self, service=None, settings=None, parent=None):
        super().__init__(parent)
        if service is None:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
            from services import audio_output as service
        self.settings = settings if settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
                / "output.ini"), QSettings.IniFormat)
        try:
            stored = json.loads(self.settings.value("output/shortcuts", "[]"))
            self._shortcuts = [item for item in stored if isinstance(item, dict)
                               and isinstance(item.get("id"), str)
                               and isinstance(item.get("name"), str)][:2]
        except (ValueError, TypeError):
            self._shortcuts = []
        self._state = {"available": False, "currentId": "", "name": "", "kind": "speaker", "volume": 0,
                       "muted": False, "devices": [], "quickOutputs": [], "pendingId": "",
                       "error": "", "status": "출력 확인 중"}
        self._busy = False
        self._action_error = False
        self._published_devices = []
        self._published_quick = []
        self._select = ""
        self._write = None
        self._stopped = False
        self._worker = _OutputWorker(service)
        self._worker.completed.connect(self._completed)
        self._worker.start()
        self._write_timer = QTimer(self)
        self._write_timer.setSingleShot(True)
        self._write_timer.setInterval(35)
        self._write_timer.timeout.connect(self._dispatch)
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(self._dispatch)
        self._poll.start()
        self._dispatch()

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state)

    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        return self._state["devices"]

    @Property("QVariantList", notify=quickOutputsChanged)
    def quickOutputs(self):
        return self._state["quickOutputs"]

    def _publish(self):
        available = {item["id"]: item for item in self._state["devices"]}
        if not self._shortcuts and available:
            self._shortcuts = [available[key] for key in self._state["suggestedIds"] if key in available][:2]
        self._state["quickOutputs"] = [available.get(item["id"], {**item, "available": False})
                                       for item in self._shortcuts]
        # Volume/state notifications must not rebuild list delegates or restart their motion.
        if self._published_devices != self._state["devices"]:
            self._published_devices = self._state["devices"]
            self.devicesChanged.emit()
        if self._published_quick != self._state["quickOutputs"]:
            self._published_quick = self._state["quickOutputs"]
            self.quickOutputsChanged.emit()
        self.changed.emit()

    @Slot(int)
    def setVolume(self, value):
        if not self._state["available"] or self._state["pendingId"]:
            return
        value = max(0, min(100, value))
        self._write = {"kind": "write", "id": self._state["currentId"],
                       "volume": value, "muted": False}
        self._state.update(volume=value, muted=False, error="")
        self._publish()
        # A trailing restart would starve writes during a continuous drag.
        if not self._write_timer.isActive():
            self._write_timer.start()

    @Slot()
    def toggleMute(self):
        if not self._state["available"] or self._state["pendingId"]:
            return
        muted = not self._state["muted"]
        self._write = {**(self._write or {}), "kind": "write",
                       "id": self._state["currentId"], "muted": muted}
        self._state.update(muted=muted, error="")
        self._publish()
        self._dispatch()

    @Slot(str)
    def selectOutput(self, device_id):
        if self._state["pendingId"]:
            return
        if device_id not in {item["id"] for item in self._state["devices"]}:
            return
        self._write = None
        self._write_timer.stop()
        self._select = device_id
        self._state.update(pendingId=device_id, error="", status="출력 전환 중")
        self._publish()
        self._dispatch()

    @Slot()
    def _dispatch(self):
        if self._busy or self._stopped:
            return
        if self._select:
            command = {"kind": "select", "id": self._select}
            self._select = ""
        elif self._write:
            command, self._write = self._write, None
        else:
            command = {"kind": "poll"}
        self._busy = True
        self._worker.commands.put(command)

    @Slot(object)
    def _completed(self, result):
        if self._stopped:
            return
        self._busy = False
        command, state, error = result["command"], result["state"], result["error"]
        if state:
            self._state.update(state)
        else:
            self._state.update(available=False, currentId="", name="", devices=[])
        if self._write and self._write["id"] != self._state["currentId"]:
            self._write = None
        if self._write:
            self._state.update({key: self._write[key] for key in ("volume", "muted")
                                if key in self._write})
        if command["kind"] != "select" and (self._select or self._write):
            error = ""  # A superseded operation must not replace newer interaction feedback.
        if command["kind"] == "select":
            self._state["pendingId"] = ""
            if not error and state and state["currentId"] == command["id"]:
                chosen = next((item for item in state["devices"] if item["id"] == command["id"]),
                              {"id": state["currentId"], "name": state["name"], "kind": "speaker"})
                if command["id"] not in {item["id"] for item in self._shortcuts}:
                    self._shortcuts = [chosen] + self._shortcuts[-1:]
                self.settings.setValue("output/preferred_id", command["id"])
                self.settings.setValue("output/shortcuts", json.dumps(self._shortcuts, ensure_ascii=False))
                self.settings.sync()
                if self.settings.status() != QSettings.NoError:
                    error = "출력은 전환됐지만 선호 장치를 저장하지 못함"
        if error:
            self._action_error = command["kind"] != "poll"
            self._state.update(error=error, status="출력 확인 필요")
        elif command["kind"] != "poll" or not self._action_error:
            self._action_error = False
            self._state["error"] = ""
            self._state["status"] = "시스템 출력" if state else "출력 없음"
        if self._state["pendingId"]:
            self._state["status"] = "출력 전환 중"
        self._publish()
        if self._select or self._write:
            self._dispatch()

    @Slot()
    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self._poll.stop()
        self._write_timer.stop()
        self._worker.commands.put(None)
        self._worker.wait()
