"""Explicit remembered-device owner and opt-in BLE battery sources.

Classic paired addresses identify the connection target. Random BLE addresses
cannot authenticate that target: the user must explicitly select battery sources.
"""
from __future__ import annotations

import json
from pathlib import Path
import queue
import re
import sys
import threading
import time

from PySide6.QtCore import QObject, Property, QSettings, QStandardPaths, QTimer, Signal, Slot

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from services import bluetooth_status
from services.ble_service import BleService
from services.state_manager import AirPodsStateManager


def address_key(value):
    return f"{int(value):012X}"


class DeviceBackend(QObject):
    changed = Signal()
    devicesChanged = Signal()
    candidatesChanged = Signal()
    batteriesChanged = Signal()
    connectionHint = Signal()
    _result = Signal(object)

    def __init__(self, service=bluetooth_status, scanner=None, settings=None, *, start=True, clock=time.monotonic):
        super().__init__()
        self.service, self.clock = service, clock
        self.settings = settings if settings is not None else QSettings(
            str(Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "devices.ini"), QSettings.IniFormat)
        self.target = self.settings.value("bluetooth/target", "")
        if not isinstance(self.target,str) or not re.fullmatch(r"[0-9A-F]{12}", self.target):
            self.target = ""
        self.sources = self._load_sources()
        self._devices, self._candidates, self._nearby = [], [], {}
        self._state = dict(targetId=self.target, name=self.settings.value("bluetooth/name", ""),
                           paired=False, connected=False, pending=False, error="", status="등록 장치를 선택하세요")
        self._batteries = self._empty_batteries()
        self._manager = AirPodsStateManager()
        self._valid_at = {}
        self._query_error = ""
        self._scanner_error = ""
        self._last_hint = -float("inf")
        self._hinted = False
        self._stop = threading.Event()
        self._commands = queue.Queue()
        self._thread = None
        self._result.connect(self._received)
        self.scanner = scanner if scanner is not None else BleService()
        self.scanner.advertisementReceived.connect(self._advertisement)
        self.scanner.errorOccurred.connect(self._scan_error)
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self.refresh)
        if start:
            self.scanner.start()
            self._tick.start()
            self._thread = threading.Thread(target=self._run, name="SelectedBluetooth", daemon=True)
            self._thread.start()

    def _load_sources(self):
        try:
            values = json.loads(self.settings.value("battery/sources", "[]"))
            if not isinstance(values, list) or len(values) > 2:
                return []
            return [v for v in values if isinstance(v, dict) and isinstance(v.get("address"), str)
                    and re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", v["address"])
                    and type(v.get("model")) is int]
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _empty_batteries():
        return [dict(label=label, value=-1, charging=False, quality="unknown") for label in ("L", "R", "CASE")]

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state, error=" · ".join(filter(None, (
            self._state["error"], self._query_error, self._scanner_error))))

    @Property("QVariantList", notify=devicesChanged)
    def devices(self): return self._devices

    @Property("QVariantList", notify=candidatesChanged)
    def candidates(self): return self._candidates

    @Property("QVariantList", notify=batteriesChanged)
    def batteries(self): return self._batteries

    @Property("QVariantList", notify=candidatesChanged)
    def batterySources(self): return [v["address"] for v in self.sources]

    def _save(self, values):
        old = {key: self.settings.value(key, None) for key in values}
        for key, value in values.items(): self.settings.setValue(key, value)
        self.settings.sync()
        if self.settings.status() == QSettings.NoError:
            return True
        for key, value in old.items():
            if value is None: self.settings.remove(key)
            else: self.settings.setValue(key, value)
        self.settings.sync()
        self._state["error"] = "장치 설정을 저장하지 못함 · 기존 선택 유지"
        self.changed.emit()
        return False

    @Slot(str, result=bool)
    def selectDevice(self, target):
        if self._state["pending"] or (target and not any(d["id"] == target for d in self._devices)):
            return False
        if target == self.target: return True
        device = next((d for d in self._devices if d["id"] == target), {})
        if not self._save({"bluetooth/target": target, "bluetooth/name": device.get("name", ""), "battery/sources": "[]"}):
            return False
        self.target, self.sources = target, []
        self._manager.reset(); self._valid_at.clear(); self._hinted = False
        self._state.update(targetId=target, name=device.get("name", ""), paired=bool(device),
                           connected=device.get("connected", False), error="",
                           status="연결됨" if device.get("connected") else "등록됨 · 미연결")
        self.changed.emit(); self.candidatesChanged.emit(); self.refresh()
        return True

    @Slot("QVariantList", result=bool)
    def bindSources(self, addresses):
        known = {v["address"]: v for v in self._candidates}
        if (not isinstance(addresses,list) or any(not isinstance(a,str) for a in addresses)
                or not self.target or self._state["pending"] or len(addresses) > 2 or len(set(addresses)) != len(addresses)):
            return False
        if any(not isinstance(a, str) or a not in known for a in addresses): return False
        models = {known[a]["model"] for a in addresses}
        if len(models) > 1: return False
        selected = [dict(address=a, model=known[a]["model"]) for a in addresses]
        if not self._save({"battery/sources": json.dumps(selected)}): return False
        self.sources = selected
        self._manager.reset(); self._valid_at.clear()
        self._state["error"] = ""
        self.candidatesChanged.emit(); self.changed.emit(); self.refresh()
        return True

    @Slot()
    def connectDevice(self):
        if (not self.target or not self._state["paired"] or self._state["connected"]
                or self._state["pending"] or self._stop.is_set()): return
        self._state.update(pending=True, error="", status="연결 중")
        self.changed.emit()
        self._commands.put(self.target)

    def _run(self):
        while not self._stop.is_set():
            try:
                command = self._commands.get(timeout=3)
                if command is None: return
            except queue.Empty:
                command = ""
            try:
                records = self.service.paired_devices()
                if command:
                    device = next((d for d in records if address_key(d.address) == command and d.paired), None)
                    if device is None: raise RuntimeError("저장한 장치가 등록 목록에 없음")
                    if not device.connected:
                        self.service.reconnect_paired_audio(device)
                    deadline = self.clock() + 12
                    while not self._stop.is_set():
                        records = self.service.paired_devices()
                        if any(address_key(d.address) == command and d.connected for d in records): break
                        if self.clock() >= deadline: raise RuntimeError("연결 확인 시간 초과 · 장치 전원/거리를 확인하세요")
                        if self._stop.wait(.4): return
                if not self._stop.is_set(): self._result.emit(dict(records=records, command=command, error=""))
            except Exception as error:
                if not self._stop.is_set(): self._result.emit(dict(records=None, command=command, error=str(error)))

    @Slot(object)
    def _received(self, result):
        if self._stop.is_set(): return
        records = result["records"]
        previous = self._state["connected"]
        if records is not None:
            self._query_error = ""
            devices = [dict(id=address_key(d.address), name=d.name, connected=d.connected) for d in records if d.paired]
            if devices != self._devices:
                self._devices = devices; self.devicesChanged.emit()
            selected = next((d for d in devices if d["id"] == self.target), None)
            self._state.update(paired=selected is not None, connected=bool(selected and selected["connected"]))
            if selected: self._state["name"] = selected["name"]
        else:
            # A failed status read is unknown, not evidence of disconnection.
            if not result["command"]: self._query_error = result["error"]
        if result["command"]:
            self._state["pending"] = False
            self._state["error"] = result["error"]
        if not self._state["pending"]:
            self._state["status"] = "연결됨" if self._state["connected"] else "등록됨 · 미연결" if self._state["paired"] else "등록 장치 미감지"
        if previous and not self._state["connected"]: self._hinted = False
        self.changed.emit()
        if (records is not None and self.target and self._state["paired"] and not self._state["connected"]
                and not self._state["pending"] and not self._hinted and self.clock() - self._last_hint > 90):
            self._hinted = True; self._last_hint = self.clock(); self.connectionHint.emit()

    @Slot(object)
    def _advertisement(self, advertisement):
        if self._stop.is_set() or advertisement.rssi < -85: return
        if self._scanner_error:
            self._scanner_error = ""
            self.changed.emit()
        address = advertisement.address.upper()
        self._nearby[address] = dict(address=address, model=advertisement.model_id,
                                     name=advertisement.state.model_name, seen=self.clock())
        if not self.target or not any(v["address"] == address and v["model"] == advertisement.model_id for v in self.sources): return
        self._manager.update(advertisement)
        if not self._manager.last_update_accepted: return
        for name in ("left", "right", "case"):
            if getattr(advertisement.state, name).battery.percent is not None:
                self._valid_at[name] = self.clock()
        self.refresh()

    @Slot(str)
    def _scan_error(self, message):
        self._scanner_error = message
        self.changed.emit()

    @Slot()
    def refresh(self):
        now = self.clock()
        self._nearby = {a:v for a,v in self._nearby.items() if now-v["seen"] < 30}
        candidates = [{k:v for k,v in item.items() if k != "seen"} for item in sorted(self._nearby.values(),key=lambda v:v["address"])]
        if candidates != self._candidates:
            self._candidates = candidates; self.candidatesChanged.emit()
        current = self._manager.current
        rows = []
        for name, label in (("left","L"),("right","R"),("case","CASE")):
            age = now-self._valid_at.get(name,-float("inf"))
            previous = next((r for r in self._batteries if r["label"]==label), {})
            pod = getattr(current,name,None)
            candidate = pod.battery.percent if pod is not None else None
            value = candidate if candidate is not None else previous.get("value",-1)
            value = value if value is not None and age<=120 else -1
            rows.append(dict(label=label,value=value,charging=bool(pod and pod.battery.charging and age<=10),
                             quality="unknown" if value<0 else "fresh" if age<=10 else "cached"))
        if rows != self._batteries:
            self._batteries = rows; self.batteriesChanged.emit()

    def stop(self):
        self._stop.set(); self._commands.put(None); self._tick.stop(); self.scanner.stop()
        if self._thread: self._thread.join(timeout=2)
