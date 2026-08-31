from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, Signal

from services.airpods_protocol import APPLE_COMPANY_ID, parse_airpods_manufacturer_data
from services.state_manager import AirPodsStateManager


class BleService(QObject):
    stateReceived = Signal(object)
    deviceLost = Signal()
    errorOccurred = Signal(str)
    scannerRunningChanged = Signal(bool)

    def __init__(self, *, rssi_min: int = -85, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manager = AirPodsStateManager(rssi_min=rssi_min)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._reported_lost = True

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="AirPodsBLE", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def set_rssi_min(self, value: int) -> None:
        self._manager.rssi_min = value

    def _thread_main(self) -> None:
        while not self._stop.is_set():
            try:
                asyncio.run(self._scan())
            except Exception as exc:  # scanner failures must never crash the UI process
                self.errorOccurred.emit(f"BLE scanner: {exc}")
                self.scannerRunningChanged.emit(False)
            if not self._stop.wait(5.0):
                continue

    async def _scan(self) -> None:
        from bleak import BleakScanner

        def callback(device: Any, advertisement: Any) -> None:
            raw = advertisement.manufacturer_data.get(APPLE_COMPANY_ID)
            if not raw:
                return
            parsed = parse_airpods_manufacturer_data(
                bytes(raw), address=str(device.address), rssi=int(advertisement.rssi)
            )
            if parsed is None:
                return
            state = self._manager.update(parsed)
            if state is not None:
                self._reported_lost = False
                self.stateReceived.emit(state)

        scanner = BleakScanner(detection_callback=callback)
        await scanner.start()
        self.scannerRunningChanged.emit(True)
        try:
            while not self._stop.is_set():
                await asyncio.sleep(0.5)
                expired = self._manager.expire_if_needed(time.monotonic())
                refreshed = self._manager.consume_expiry_state()
                if refreshed is not None:
                    self.stateReceived.emit(refreshed)
                if expired and not self._reported_lost:
                    self._reported_lost = True
                    self.deviceLost.emit()
        finally:
            await scanner.stop()
            self.scannerRunningChanged.emit(False)
