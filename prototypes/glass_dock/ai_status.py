"""AI assistants for the AI module: usage left, reply alerts, open the app.

Codex: its own session logs (~/.codex/sessions) carry the 5-hour and weekly rate
limits (used %, reset time); the newest session that has them is read. Claude: the same
two limits come from Anthropic's usage page, asked with the Claude login already on this PC
(~/.claude/.credentials.json, the user agreed to it); the token goes only to
api.anthropic.com and is never shown, logged or saved. When that fails, the limits Claude
Code hands its status line (claude_statusline.ps1 saves them to claude_limits.json) are
used. Today's tokens come from its logs (~/.claude/projects). Reply alerts: a new Windows
notification from the app's package adds a red
dot until the app is opened from the dock. Opening uses the Store app's identity, so
an open window comes to the front and a closed app starts.
"""
from __future__ import annotations

import asyncio
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

HOME = Path.home()
ASSISTANTS = [
    dict(id="codex", name="Codex", package="OpenAI.Codex", aumid="OpenAI.Codex_2p2nqsd0c76g0!App"),
    dict(id="claude", name="Claude", package="Claude", aumid="Claude_pzs8sxrjxfjjc!Claude"),
]
LIMIT_NAMES = {300: "5시간", 10080: "주간"}
CLAUDE_LIMITS = Path(os.environ.get("LOCALAPPDATA", HOME)) / "GlassDock" / "claude_limits.json"
CLAUDE_CREDENTIALS = HOME / ".claude" / ".credentials.json"
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
ONLINE_REFRESH_SECONDS = 180
FILE_REFRESH_SECONDS = 20
POLL_SECONDS = 1.0


def codex_sessions(root: Path = HOME / ".codex" / "sessions"):
    """Session logs, newest first; they live in year/month/day folders."""
    def newest_dirs(folder: Path):
        try:
            return sorted((p for p in folder.iterdir() if p.is_dir()), reverse=True)
        except OSError:
            return []
    for year in newest_dirs(root):
        for month in newest_dirs(year):
            for day in newest_dirs(month):
                yield from sorted(day.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def latest_codex_limits(root: Path = HOME / ".codex" / "sessions", now: float | None = None, look_back: int = 40) -> dict:
    """The limits of the newest session that has any: a session opened without a turn
    (or while out of usage) logs none."""
    for index, path in enumerate(codex_sessions(root)):
        if index >= look_back:
            break
        result = codex_limits(path, now)
        if result["limits"]:
            return result
    return dict(limits=[], asOf=0)


def codex_limits(path: Path | None, now: float | None = None) -> dict:
    """{limits: [{label, used, resetsAt(ms), window}], asOf(ms)} from the last rate_limits in a log."""
    now = time.time() if now is None else now
    if path is None:
        return dict(limits=[], asOf=0)
    try:
        with open(path, "rb") as file:
            file.seek(0, os.SEEK_END)
            file.seek(max(0, file.tell() - 512 * 1024))
            tail = file.read().decode("utf-8", "replace")
        start = tail.rfind('"rate_limits"')
        if start < 0:
            return dict(limits=[], asOf=0)
        rest = tail[start + len('"rate_limits"'):].lstrip()
        data, _ = json.JSONDecoder().raw_decode(rest[1:].lstrip() if rest.startswith(":") else rest)
    except (OSError, ValueError):
        return dict(limits=[], asOf=0)
    limits = []
    for key in ("primary", "secondary"):
        part = data.get(key) if isinstance(data, dict) else None
        if not isinstance(part, dict):
            continue
        resets = float(part.get("resets_at") or 0)
        window = int(part.get("window_minutes") or 0)
        used = float(part.get("used_percent") or 0)
        if resets and resets < now:          # that window has rolled over since the log was written
            used, resets = 0.0, 0
        limits.append(dict(label=LIMIT_NAMES.get(window, f"{window // 60}시간"), used=round(used),
                           resetsAt=resets * 1000, window=window))
    return dict(limits=limits, asOf=path.stat().st_mtime * 1000)


def claude_limits(path: Path = CLAUDE_LIMITS, now: float | None = None) -> dict:
    """{limits, asOf(ms)} from the status line's last save, in the shape codex_limits gives."""
    now = time.time() if now is None else now
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        as_of = path.stat().st_mtime * 1000
    except (OSError, ValueError):
        return dict(limits=[], asOf=0)
    limits = _claude_windows(data, now, "used_percentage")
    return dict(limits=limits, asOf=as_of if limits else 0)


def claude_usage(credentials: Path = CLAUDE_CREDENTIALS, now: float | None = None) -> dict:
    """{limits, asOf(ms), note} from Anthropic's usage page, with the Claude login on this PC.

    note: "" when read, "nologin" (no login file), "expired" (the login needs renewing:
    left to Claude itself, since renewing here would sign Claude Code out), "offline".
    The token is sent to api.anthropic.com only, and never printed or kept.
    """
    now = time.time() if now is None else now
    try:
        oauth = json.loads(credentials.read_text(encoding="utf-8"))["claudeAiOauth"]
        token = oauth["accessToken"]
    except (OSError, ValueError, KeyError, TypeError):
        return dict(limits=[], asOf=0, note="nologin")
    if oauth.get("expiresAt") and oauth["expiresAt"] / 1000 < now:
        return dict(limits=[], asOf=0, note="expired")
    request = urllib.request.Request(CLAUDE_USAGE_URL, headers={
        "Authorization": "Bearer " + token, "anthropic-beta": "oauth-2025-04-20",
        "Content-Type": "application/json", "User-Agent": "GlassDock"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as error:
        return dict(limits=[], asOf=0, note="expired" if error.code in (401, 403) else "offline")
    except (OSError, ValueError):
        return dict(limits=[], asOf=0, note="offline")
    limits = _claude_windows(data, now, "utilization")
    return dict(limits=limits, asOf=now * 1000 if limits else 0, note="" if limits else "offline")


def _claude_windows(data, now: float, field: str) -> list:
    """The 5-hour and weekly windows of a Claude usage answer, `field` holding the used %."""
    limits = []
    for key, window in (("five_hour", 300), ("seven_day", 10080)):
        part = data.get(key) if isinstance(data, dict) else None
        if not isinstance(part, dict):
            continue
        resets = part.get("resets_at") or 0
        if isinstance(resets, str):
            try:
                resets = datetime.fromisoformat(resets.replace("Z", "+00:00")).timestamp()
            except ValueError:
                resets = 0
        resets = float(resets)
        used = float(part.get(field) or 0)
        if resets and resets < now:          # rolled over since it was read
            used, resets = 0.0, 0
        limits.append(dict(label=LIMIT_NAMES[window], used=round(used), resetsAt=resets * 1000, window=window))
    return limits


def claude_today(root: Path = HOME / ".claude" / "projects", now: float | None = None) -> dict:
    """{tokens, lastUsed(ms)}: today's input+output+cache-write tokens of Claude Code's own logs."""
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now).date()
    start_of_day = datetime.combine(today, datetime.min.time()).timestamp()
    seen: dict[str, int] = {}
    last = 0.0
    try:
        files = [p for p in root.glob("*/*.jsonl") if p.stat().st_mtime >= start_of_day]
    except OSError:
        files = []
    for path in files:
        last = max(last, path.stat().st_mtime)
        try:
            with open(path, encoding="utf-8", errors="replace") as file:
                for line in file:
                    if '"usage"' not in line:
                        continue
                    try:
                        entry = json.loads(line)
                        stamp = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).astimezone()
                        if stamp.date() != today:
                            continue
                        message = entry["message"]
                        usage = message["usage"]
                    except (ValueError, KeyError, TypeError):
                        continue
                    # A reply is logged several times while it streams; count its last usage once.
                    seen[message.get("id") or str(len(seen))] = (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                                                                + usage.get("cache_creation_input_tokens", 0))
        except OSError:
            continue
    return dict(tokens=sum(seen.values()), lastUsed=last * 1000)


def app_logo(package: str) -> str:
    """A file URL of the Store app's small logo (largest target size), or "" when not installed."""
    try:
        location = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-AppxPackage -Name '{package}').InstallLocation"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    if not location:
        return ""
    assets = [p for folder in ("Assets", "assets") for p in (Path(location) / folder).glob("Square44x44Logo*.png")]
    if not assets:
        return ""
    def size(p: Path) -> int:
        digits = "".join(c for c in p.stem.split("targetsize-")[-1] if c.isdigit()) if "targetsize-" in p.stem else ""
        return int(digits) if digits else 44
    best = sorted(assets, key=lambda p: (size(p) > 64, -size(p)))[0]
    return QUrl.fromLocalFile(str(best)).toString()


def open_app(aumid: str) -> None:
    frozen = os.name == "nt" and getattr(sys, "frozen", False)
    if frozen:   # don't hand the packaged dock's DLL folder to the app (see launcher.py)
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        os.startfile("shell:AppsFolder\\" + aumid)
    finally:
        if frozen:
            ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)


class AiStatus(QObject):
    changed = Signal()
    _update = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = {a["id"]: dict(a, installed=False, logo="", unread=0, limits=[], asOf=0, tokens=0, lastUsed=0)
                       for a in ASSISTANTS}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._update.connect(self._apply)

    @Property("QVariantList", notify=changed)
    def assistants(self):
        return [dict(item) for item in self._items.values() if item["installed"]]

    @Slot(str)
    def openApp(self, assistant_id):
        item = self._items.get(assistant_id)
        if not item:
            return
        open_app(item["aumid"])
        if item["unread"]:
            item["unread"] = 0
            self.changed.emit()

    def start(self):
        if not self._threads:
            for target in (self._files, self._notifications):
                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                self._threads.append(thread)

    def stop(self):
        self._stop.set()

    def _files(self):
        for item in ASSISTANTS:
            logo = app_logo(item["package"])
            self._update.emit((item["id"], dict(installed=bool(logo), logo=logo)))
        online, asked = dict(limits=[], asOf=0, note="nologin"), 0.0
        while True:
            self._update.emit(("codex", latest_codex_limits()))
            if time.time() - asked >= ONLINE_REFRESH_SECONDS:
                online, asked = claude_usage(), time.time()
            limits = online if online["limits"] else dict(claude_limits(), note=online["note"])
            self._update.emit(("claude", dict(claude_today(), **limits)))
            if self._stop.wait(FILE_REFRESH_SECONDS):
                return

    def _notifications(self):
        async def run():
            try:
                from winrt.windows.ui.notifications import NotificationKinds
                from winrt.windows.ui.notifications.management import UserNotificationListener
                listener = UserNotificationListener.current
                if int(await listener.request_access_async()) != 1:
                    return
            except Exception:
                return   # no notification access: the module simply shows no reply dots
            seen = None
            by_app = {a["aumid"]: a["id"] for a in ASSISTANTS}
            while not self._stop.is_set():
                try:
                    items = await listener.get_notifications_async(NotificationKinds.TOAST)
                    current = {i.id: (i.app_info.app_user_model_id if i.app_info else "") for i in items}
                    if seen is not None:
                        for key in current.keys() - seen:
                            assistant = by_app.get(current[key])
                            if assistant:
                                self._update.emit((assistant, "reply"))
                    seen = set(current)
                except Exception:
                    pass
                await asyncio.sleep(POLL_SECONDS)
        asyncio.run(run())

    @Slot(object)
    def _apply(self, update):
        assistant, values = update
        item = self._items[assistant]
        if values == "reply":
            item["unread"] += 1
        else:
            if all(item.get(k) == v for k, v in values.items()):
                return
            item.update(values)
        self.changed.emit()
