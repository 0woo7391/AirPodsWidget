"""CPU, memory and network ping for the system module, read every two seconds on a worker thread."""
from __future__ import annotations

import ctypes
import socket
import threading
from ctypes import wintypes

from PySide6.QtCore import Property, QObject, Signal

PING_HOST = "1.1.1.1"     # a nearby, always-up anycast host: the line's own latency
REFRESH_SECONDS = 2.0


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def _times():
    idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    value = lambda f: (f.dwHighDateTime << 32) | f.dwLowDateTime
    return value(idle), value(kernel) + value(user)   # kernel time includes idle time


def cpu_percent(before, after) -> int:
    idle = after[0] - before[0]
    total = after[1] - before[1]
    return max(0, min(100, round(100 * (total - idle) / total))) if total > 0 else 0


def memory() -> tuple[int, float, float]:
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    gib = 1024 ** 3
    return status.dwMemoryLoad, (status.ullTotalPhys - status.ullAvailPhys) / gib, status.ullTotalPhys / gib


def ping_ms(host: str = PING_HOST, timeout_ms: int = 1000) -> int:
    """Round trip of one ICMP echo (IcmpSendEcho needs no admin rights), -1 when it fails."""
    iphlpapi = ctypes.WinDLL("iphlpapi")
    iphlpapi.IcmpCreateFile.restype = wintypes.HANDLE
    iphlpapi.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
    iphlpapi.IcmpSendEcho.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.WORD,
                                      ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    try:
        address = int.from_bytes(socket.inet_aton(socket.gethostbyname(host)), "little")
    except OSError:
        return -1
    handle = iphlpapi.IcmpCreateFile()
    if not handle or handle == wintypes.HANDLE(-1).value:
        return -1
    try:
        payload = b"glassdock"
        reply = ctypes.create_string_buffer(64 + len(payload) + 8)
        if not iphlpapi.IcmpSendEcho(handle, address, payload, len(payload), None, reply, len(reply), timeout_ms):
            return -1
        status = int.from_bytes(reply.raw[4:8], "little")       # ICMP_ECHO_REPLY.Status
        return int.from_bytes(reply.raw[8:12], "little") if status == 0 else -1   # .RoundTripTime
    finally:
        iphlpapi.IcmpCloseHandle(handle)


class SystemStatus(QObject):
    changed = Signal()
    _read = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = dict(cpu=0, memory=0, memoryUsed=0.0, memoryTotal=0.0, ping=-1)
        self._stop = threading.Event()
        self._thread = None
        self._read.connect(self._apply)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state)

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="SystemStatus", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        before = _times()
        while not self._stop.wait(REFRESH_SECONDS):
            after = _times()
            load, used, total = memory()
            self._read.emit(dict(cpu=cpu_percent(before, after), memory=load, memoryUsed=round(used, 1),
                                 memoryTotal=round(total, 1), ping=ping_ms()))
            before = after

    def _apply(self, state):
        if state != self._state:
            self._state = state
            self.changed.emit()
