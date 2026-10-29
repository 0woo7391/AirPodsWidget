"""No Bluetooth/audio calls: fake service, fake scanner, temporary QSettings."""
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer, QSettings, QObject, Signal
from device_backend import DeviceBackend, bluetooth_status
from preferences import Preferences, LAYOUTS
from services.airpods_protocol import parse_airpods_manufacturer_data


class Scanner(QObject):
    advertisementReceived=Signal(object)
    errorOccurred=Signal(str)
    def start(self): raise AssertionError("Real scanner must not start in unit tests")
    def stop(self): pass


class Clock:
    def __init__(self): self.now=time.monotonic()
    def __call__(self): return self.now


class Service:
    def __init__(self,clock):
        self.clock=clock; self.calls=[]; self.fail=False; self.never=False
        self.records=[bluetooth_status.BluetoothDeviceStatus("이름을 바꾼 이어폰",0xAABBCCDDEEFF,True,False),
                      bluetooth_status.BluetoothDeviceStatus("다른 장치",0x112233445566,True,False)]
    def paired_devices(self):
        if self.never: self.clock.now+=3
        return self.records
    def reconnect_paired_audio(self,device):
        self.calls.append(device.address)
        if self.fail: raise RuntimeError("fake connection failure")
        if not self.never: device.connected=True


def advertisement(address="AA:BB:CC:DD:EE:01",percent=8,charging=False,model=0x2027,timestamp=None):
    data=bytearray(27); data[0]=7; data[1]=25; data[3:5]=model.to_bytes(2,"little")
    data[5]=0x20; data[6]=(7<<4)|percent; data[7]=6|(0x10 if charging else 0)
    return parse_airpods_manufacturer_data(bytes(data),address=address,rssi=-45,timestamp=timestamp)


def wait_until(condition):
    deadline=time.perf_counter()+5
    while not condition() and time.perf_counter()<deadline:
        loop=QEventLoop(); QTimer.singleShot(10,loop.quit); loop.exec()
    assert condition(),"fake worker did not settle"


class DeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=QSettings(str(Path(self.temp.name)/"devices.ini"),QSettings.IniFormat)
        self.clock=Clock(); self.service=Service(self.clock)
        self.backend=DeviceBackend(self.service,Scanner(),self.settings,start=False,clock=self.clock)
        self.poll()
    def tearDown(self): self.backend.stop(); self.temp.cleanup()
    def poll(self,command="",error="",records=True):
        self.backend._received(dict(records=self.service.records if records else None,command=command,error=error))
    def select(self): self.assertTrue(self.backend.selectDevice("AABBCCDDEEFF"))
    def bind(self):
        self.select(); self.backend._advertisement(advertisement())
        self.backend.refresh(); self.assertTrue(self.backend.bindSources(["AA:BB:CC:DD:EE:01"]))
    def worker(self):
        self.backend._thread=threading.Thread(target=self.backend._run,daemon=True)
        self.backend._thread.start()

    def test_renamed_target_restores_by_address(self):
        self.select()
        restored=DeviceBackend(self.service,Scanner(),self.settings,start=False)
        try:
            self.assertEqual(restored.state["targetId"],"AABBCCDDEEFF")
            self.assertEqual(restored.state["name"],"이름을 바꾼 이어폰")
            self.assertFalse(self.backend.selectDevice("FFFFFFFFFFFF"))
        finally: restored.stop()

    def test_hint_once_and_only_on_confirmed_status(self):
        self.select(); hints=[]; self.backend.connectionHint.connect(lambda:hints.append(1))
        self.poll(); self.poll(); self.poll()
        self.assertEqual(len(hints),1)
        self.service.records[0].connected=True; self.poll()
        self.poll(error="query failed",records=False)
        self.assertTrue(self.backend.state["connected"])
        self.assertEqual(len(hints),1)
        self.clock.now+=100; self.service.records[0].connected=False; self.poll(); self.poll()
        self.assertEqual(len(hints),2)

    def test_connection_duplicate_and_target_change_blocked(self):
        self.select(); self.backend.connectDevice(); self.backend.connectDevice()
        self.assertEqual(self.backend._commands.qsize(),1)
        self.assertFalse(self.backend.selectDevice("112233445566"))
        self.worker(); wait_until(lambda:not self.backend.state["pending"])
        self.assertEqual(self.service.calls,[0xAABBCCDDEEFF])
        self.assertTrue(self.backend.state["connected"])
        self.backend.connectDevice(); self.assertEqual(self.service.calls,[0xAABBCCDDEEFF])

    def test_failed_connection_preserves_disconnected_state(self):
        self.select(); self.service.fail=True; self.backend.connectDevice(); self.worker()
        wait_until(lambda:not self.backend.state["pending"])
        self.assertFalse(self.backend.state["connected"])
        self.assertIn("fake connection failure",self.backend.state["error"])

    def test_query_and_scanner_errors_recover_independently(self):
        self.poll(error="query failed",records=False)
        self.backend._scan_error("scanner failed")
        self.poll()
        self.assertEqual(self.backend.state["error"],"scanner failed")
        self.poll(error="query failed",records=False)
        self.backend._advertisement(advertisement())
        self.assertEqual(self.backend.state["error"],"query failed")
        self.poll()
        self.assertEqual(self.backend.state["error"],"")

    def test_poll_does_not_hide_connection_failure(self):
        self.poll(command="AABBCCDDEEFF",error="connection failed",records=False)
        self.assertEqual(self.backend.state["error"],"connection failed")
        self.poll()
        self.assertEqual(self.backend.state["error"],"connection failed")

    def test_rejected_packet_cannot_refresh_cached_battery(self):
        self.bind(); stamp=time.monotonic()
        first=replace(advertisement(timestamp=stamp),rssi=-80)
        other=replace(advertisement("AA:BB:CC:DD:EE:02",timestamp=stamp+.01),
                      side=type(first.side).RIGHT,rssi=-75)
        self.backend.sources.append(dict(address=other.address,model=other.model_id))
        self.backend._advertisement(first); self.backend._advertisement(other)
        self.clock.now+=11; self.backend.refresh()
        ages=dict(self.backend._valid_at)
        rejected=replace(advertisement(percent=1,timestamp=stamp+.02),rssi=-10)
        self.backend._advertisement(rejected)
        self.assertFalse(self.backend._manager.last_update_accepted)
        self.assertEqual(self.backend._valid_at,ages)
        self.assertEqual(self.backend.batteries[0]["value"],80)
        self.assertEqual(self.backend.batteries[0]["quality"],"cached")
        self.backend._advertisement(replace(first,timestamp=stamp+.03))
        self.assertTrue(self.backend._manager.last_update_accepted)
        self.assertEqual(self.backend.batteries[0]["quality"],"fresh")

    def test_successful_request_without_connection_times_out(self):
        self.select(); self.service.never=True; self.backend.connectDevice(); self.worker()
        wait_until(lambda:not self.backend.state["pending"])
        self.assertFalse(self.backend.state["connected"])
        self.assertIn("시간 초과",self.backend.state["error"])

    def test_unbound_and_wrong_sources_never_publish_battery(self):
        self.select(); self.backend._advertisement(advertisement()); self.backend.refresh()
        self.assertTrue(all(r["value"]==-1 for r in self.backend.batteries))
        self.assertTrue(self.backend.bindSources(["AA:BB:CC:DD:EE:01"]))
        self.backend._advertisement(advertisement("AA:BB:CC:DD:EE:02")); self.backend.refresh()
        self.assertTrue(all(r["value"]==-1 for r in self.backend.batteries))
        self.backend._advertisement(advertisement()); self.backend.refresh()
        self.assertEqual([r["value"] for r in self.backend.batteries],[80,70,60])
        self.backend._advertisement(advertisement(percent=1,model=0x2014)); self.backend.refresh()
        self.assertEqual(self.backend.batteries[0]["value"],80)

    def test_battery_gaps_do_not_change_bluetooth_state(self):
        self.bind(); self.service.records[0].connected=True; self.poll()
        self.backend._advertisement(advertisement()); self.clock.now+=11; self.backend.refresh()
        self.assertTrue(self.backend.state["connected"])
        self.assertEqual(self.backend.batteries[0]["value"],80)
        self.assertEqual(self.backend.batteries[0]["quality"],"cached")
        self.clock.now+=120; self.backend.refresh()
        self.assertEqual(self.backend.batteries[0]["value"],-1)
        self.assertTrue(self.backend.state["connected"])

    def test_missing_field_does_not_refresh_old_value(self):
        self.bind(); self.backend._advertisement(advertisement())
        self.clock.now+=11
        self.backend._advertisement(advertisement(percent=15,timestamp=time.monotonic()+.01))
        self.assertEqual(self.backend.batteries[0]["quality"],"cached")

    def test_unknown_packet_after_scanner_gap_keeps_cached_value(self):
        self.bind(); self.backend._advertisement(advertisement())
        self.clock.now+=15; self.backend._manager.reset()
        self.backend._advertisement(advertisement(percent=15,timestamp=time.monotonic()+.1))
        self.assertEqual(self.backend.batteries[0]["value"],80)
        self.assertEqual(self.backend.batteries[0]["quality"],"cached")

    def test_charging_requires_confirmed_change(self):
        self.bind(); stamp=time.monotonic()
        self.backend._advertisement(advertisement(timestamp=stamp))
        self.backend._advertisement(advertisement(charging=True,timestamp=stamp+.1))
        self.assertFalse(self.backend.batteries[0]["charging"])
        self.backend._advertisement(advertisement(charging=True,timestamp=stamp+.2))
        self.assertTrue(self.backend.batteries[0]["charging"])
        self.clock.now+=11; self.backend.refresh()
        self.assertFalse(self.backend.batteries[0]["charging"])

    def test_persistence_and_target_change_clear_battery_sources(self):
        self.bind(); self.assertTrue(self.backend.selectDevice(self.backend.target))
        self.assertEqual(self.backend.batterySources,["AA:BB:CC:DD:EE:01"])
        restored=DeviceBackend(self.service,Scanner(),self.settings,start=False)
        try: self.assertEqual(restored.batterySources,self.backend.batterySources)
        finally: restored.stop()
        self.assertTrue(self.backend.selectDevice("112233445566"))
        self.assertFalse(self.backend.batterySources)

    def test_invalid_binding_and_corrupt_preferences(self):
        self.select()
        self.assertFalse(self.backend.bindSources([["bad"]]))
        self.assertFalse(self.backend.bindSources(["unknown"]))
        self.settings.setValue("bluetooth/target",12)
        self.settings.setValue("battery/sources",'{"bad":1}')
        restored=DeviceBackend(self.service,Scanner(),self.settings,start=False)
        try:
            self.assertEqual(restored.target,""); self.assertFalse(restored.sources)
        finally: restored.stop()

    def test_stop_ignores_queued_results(self):
        self.select(); self.backend.stop(); self.service.records[0].connected=True; self.poll()
        self.assertFalse(self.backend.state["connected"])

    def test_layout_and_appearance_persist(self):
        prefs=Preferences(self.settings)
        self.assertTrue(prefs.moveModule("volume","media"))
        self.assertTrue(prefs.moveModule("battery","media"))
        prefs.setReducedMotion(True); prefs.setTint(.24)
        self.assertIsNone(self.settings.value("appearance/tint",None))
        prefs.flush(); other=Preferences(self.settings)
        self.assertIn(tuple(other.order),LAYOUTS)
        self.assertEqual(other.order,["battery","volume","media"])
        self.assertTrue(other.reducedMotion); self.assertAlmostEqual(other.tint,.24)
        self.assertFalse(other.moveModule("not-a-module","media"))

    def test_readability_and_blur_persist_without_device_reset(self):
        self.bind(); prefs=Preferences(self.settings)
        prefs.setReadability(.71); prefs.setBlur(6)
        self.assertIsNone(self.settings.value("appearance/readability",None))
        prefs.setReadability(.1); prefs.setBlur(20)
        self.assertEqual(prefs.readability,.71); self.assertEqual(prefs.blur,6)
        prefs.flush(); restored=Preferences(self.settings)
        self.assertEqual(restored.readability,.71); self.assertEqual(restored.blur,6)
        self.assertEqual(self.settings.value("bluetooth/target"),"AABBCCDDEEFF")
        self.assertEqual(self.backend.batterySources,["AA:BB:CC:DD:EE:01"])


if __name__=="__main__": unittest.main()
