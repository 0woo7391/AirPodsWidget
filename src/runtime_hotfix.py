from __future__ import annotations

import ctypes
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger(__name__)
_PATCH_MARKER = "AirPodsWidget integrated 2026-09-09 hotfix"


def _project_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _app_data_dir() -> Path:
    base = os.getenv("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    path = Path(base) / "AirPodsWidget"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_address(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 < value <= 0xFFFFFFFFFFFF else None
    text = str(value).strip().replace(":", "").replace("-", "").replace(" ", "")
    if text.lower().startswith("0x"):
        text = text[2:]
    if not text or len(text) > 12:
        return None
    try:
        parsed = int(text, 16)
    except ValueError:
        return None
    return parsed if 0 < parsed <= 0xFFFFFFFFFFFF else None


def _format_address(value: object) -> str:
    parsed = _normalize_address(value)
    return f"{parsed:012X}" if parsed is not None else ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _find_nested(data: dict[str, Any], keys: Iterable[str]) -> Any:
    sections = ("airpods", "bluetooth", "audio", "system", "settings")
    for section_name in sections:
        section = data.get(section_name)
        if isinstance(section, dict):
            for key in keys:
                if section.get(key) not in (None, ""):
                    return section[key]
    for key in keys:
        if data.get(key) not in (None, ""):
            return data[key]
    return None


def _selected_identity() -> tuple[int | None, str]:
    settings = _read_json(_app_data_dir() / "settings.json")
    address = _find_nested(
        settings,
        (
            "selected_airpods_address",
            "selectedAirPodsAddress",
            "selected_address",
            "selectedAddress",
            "airpods_address",
            "airPodsAddress",
        ),
    )
    name = _find_nested(
        settings,
        (
            "selected_airpods_name",
            "selectedAirPodsName",
            "selected_name",
            "selectedName",
            "airpods_name",
            "airPodsName",
        ),
    )
    return _normalize_address(address), str(name or "").strip()


def _recent_path() -> Path:
    return _app_data_dir() / "recent_airpods.json"


def _recent_identity() -> tuple[int | None, str]:
    data = _read_json(_recent_path())
    return _normalize_address(data.get("address")), str(data.get("name") or "").strip()


def _save_recent(device: Any) -> None:
    address = _format_address(getattr(device, "address", None))
    if not address:
        return
    payload = {"address": address, "name": str(getattr(device, "name", "") or "")}
    path = _recent_path()
    current = _read_json(path)
    if current == payload:
        return
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _choose_airpods(devices: Iterable[Any]) -> Any | None:
    candidates = [item for item in devices if bool(getattr(item, "paired", True))]
    if not candidates:
        return None

    selected_address, selected_name = _selected_identity()
    if selected_address is not None:
        # An explicit user selection is authoritative. Never silently fall
        # through to another pair if the selected pair is currently absent.
        return next(
            (
                item
                for item in candidates
                if _normalize_address(getattr(item, "address", None)) == selected_address
            ),
            None,
        )

    selected_key = selected_name.casefold()
    if selected_key:
        matches = [
            item
            for item in candidates
            if str(getattr(item, "name", "")).strip().casefold() == selected_key
        ]
        if matches:
            return sorted(
                matches,
                key=lambda item: (
                    not bool(getattr(item, "connected", False)),
                    int(getattr(item, "address", 0)),
                ),
            )[0]
        return None

    recent_address, _ = _recent_identity()
    if recent_address is not None:
        recent = next(
            (
                item
                for item in candidates
                if _normalize_address(getattr(item, "address", None)) == recent_address
            ),
            None,
        )
        if recent is not None:
            return recent

    connected = [item for item in candidates if bool(getattr(item, "connected", False))]
    pool = connected or candidates
    return sorted(pool, key=lambda item: int(getattr(item, "address", 0)))[0]


def _install_bluetooth_identity_patch() -> bool:
    """Replace enumeration-order selection before controller imports it."""
    if os.name != "nt":
        return False
    try:
        from ctypes import wintypes
        from services import bluetooth_status as bt
    except Exception:
        LOGGER.exception("Could not load Bluetooth status module for identity patch")
        return False

    if getattr(bt, "_recent_identity_patch_installed", False):
        return True
    if not all(
        hasattr(bt, name)
        for name in (
            "BLUETOOTH_DEVICE_SEARCH_PARAMS",
            "BLUETOOTH_DEVICE_INFO",
            "BluetoothDeviceStatus",
        )
    ):
        LOGGER.warning("Bluetooth backend signature is not compatible with identity patch")
        return False

    def find_airpods_status():
        library = ctypes.WinDLL("bthprops.cpl")
        first = library.BluetoothFindFirstDevice
        next_device = library.BluetoothFindNextDevice
        close = library.BluetoothFindDeviceClose
        first.argtypes = [
            ctypes.POINTER(bt.BLUETOOTH_DEVICE_SEARCH_PARAMS),
            ctypes.POINTER(bt.BLUETOOTH_DEVICE_INFO),
        ]
        first.restype = wintypes.HANDLE
        next_device.argtypes = [wintypes.HANDLE, ctypes.POINTER(bt.BLUETOOTH_DEVICE_INFO)]
        next_device.restype = wintypes.BOOL
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL

        params = bt.BLUETOOTH_DEVICE_SEARCH_PARAMS()
        params.dwSize = ctypes.sizeof(params)
        params.fReturnAuthenticated = True
        params.fReturnRemembered = True
        params.fReturnUnknown = False
        params.fReturnConnected = True
        params.fIssueInquiry = False
        params.cTimeoutMultiplier = 1
        params.hRadio = None

        info = bt.BLUETOOTH_DEVICE_INFO()
        info.dwSize = ctypes.sizeof(info)
        handle = first(ctypes.byref(params), ctypes.byref(info))
        if not handle:
            return None

        devices: list[Any] = []
        try:
            while True:
                paired = bool(info.fAuthenticated) or bool(info.fRemembered)
                if paired and "airpods" in info.szName.casefold():
                    devices.append(
                        bt.BluetoothDeviceStatus(
                            info.szName,
                            info.Address.ullLong,
                            paired=True,
                            connected=bool(info.fConnected),
                        )
                    )
                info = bt.BLUETOOTH_DEVICE_INFO()
                info.dwSize = ctypes.sizeof(info)
                if not next_device(handle, ctypes.byref(info)):
                    break
        finally:
            close(handle)

        selected = _choose_airpods(devices)
        if selected is not None and bool(getattr(selected, "connected", False)):
            _save_recent(selected)
        return selected

    bt.find_airpods_status = find_airpods_status
    bt.find_connected_airpods = lambda: (
        (device := find_airpods_status())
        if device is not None and bool(getattr(device, "connected", False))
        else None
    )
    bt._recent_identity_patch_installed = True
    return True


def _replace_function(text: str, function_name: str, replacement: str) -> tuple[str, bool]:
    marker = f"function {function_name}"
    start = text.find(marker)
    if start < 0:
        return text, False
    brace = text.find("{", start)
    if brace < 0:
        return text, False
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[index + 1 :], True
    return text, False


def _patch_qml_widget(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "widgetToggleSlot" not in text or "morphAnchorInset" not in text:
        return False
    original = text

    # Right edge is the single horizontal anchor. The primary center is always
    # the vertical center of the native envelope, in both steady states and
    # every intermediate frame.
    text, _ = _replace_function(
        text,
        "chooseMorphPlacement",
        """function chooseMorphPlacement(anchorX, anchorY) {
        // AirPodsWidget integrated 2026-09-09 hotfix:
        // one physical primary stays on the right edge for both states.
        morphExpandLeft = true
        morphExpandUp = false
    }""",
    )

    text = re.sub(
        r"y:\s*window\.morphExpandUp\s*\?\s*parent\.height\s*-\s*\(window\.morphAnchorInset\s*-\s*shell\.y\)\s*-\s*height\s*/\s*2\s*:\s*\(window\.morphAnchorInset\s*-\s*shell\.y\)\s*-\s*height\s*/\s*2",
        "y: (parent.height - height) / 2",
        text,
        count=1,
        flags=re.S,
    )

    text = re.sub(
        r"var offsetY\s*=\s*window\.morphExpandUp\s*\?\s*frameHeight\s*-\s*window\.morphAnchorInset\s*\*\s*appController\.widgetScale\s*:\s*window\.morphAnchorInset\s*\*\s*appController\.widgetScale",
        "var offsetY = frameHeight / 2",
        text,
        count=1,
        flags=re.S,
    )

    if text == original:
        return False
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True


def _patch_web_primary(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    original = text
    rule_re = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.S)
    pieces: list[str] = []
    last = 0
    hits = 0
    for match in rule_re.finditer(text):
        selector = match.group("selector")
        body = match.group("body")
        key = selector.casefold()
        if not any(word in key for word in ("primary", "toggle", "collapse", "expand")):
            continue
        if not re.search(r"(?:width|inline-size)\s*:\s*34(?:\.0)?px", body, re.I):
            continue
        if not re.search(r"(?:height|block-size)\s*:\s*34(?:\.0)?px", body, re.I):
            continue
        if not re.search(r"right\s*:", body, re.I):
            continue
        new_body = re.sub(r"right\s*:\s*[^;]+;", "right:12px;", body, count=1, flags=re.I)
        if re.search(r"top\s*:", new_body, re.I):
            new_body = re.sub(r"top\s*:\s*[^;]+;", "top:50%;", new_body, count=1, flags=re.I)
        else:
            new_body += "\n  top:50%;"
        if re.search(r"transform\s*:", new_body, re.I):
            new_body = re.sub(
                r"transform\s*:\s*[^;]+;",
                "transform:translateY(-50%);",
                new_body,
                count=1,
                flags=re.I,
            )
        else:
            new_body += "\n  transform:translateY(-50%);"
        if new_body != body:
            pieces.append(text[last : match.start("body")])
            pieces.append(new_body)
            last = match.end("body")
            hits += 1
    if not hits:
        return False
    pieces.append(text[last:])
    patched = "".join(pieces)
    if patched == original:
        return False
    try:
        path.write_text(patched, encoding="utf-8")
    except OSError:
        return False
    return True


def _patch_structural_easing(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    low = text.casefold()
    if not any(word in low for word in ("morph", "collapse", "restore", "geometry")):
        return False
    original = text
    replacements = {
        "QEasingCurve.OutBack": "QEasingCurve.InOutCubic",
        "QEasingCurve.InBack": "QEasingCurve.InOutCubic",
        "QEasingCurve.InOutBack": "QEasingCurve.InOutCubic",
        "QEasingCurve.OutBounce": "QEasingCurve.InOutCubic",
        "QEasingCurve.InOutBounce": "QEasingCurve.InOutCubic",
        "QEasingCurve.OutElastic": "QEasingCurve.InOutCubic",
        "QEasingCurve.InOutElastic": "QEasingCurve.InOutCubic",
    }
    for old, new in replacements.items():
        if old in text:
            # Only rewrite when the token itself is close to a structural term.
            positions = [match.start() for match in re.finditer(re.escape(old), text)]
            for pos in reversed(positions):
                context = text[max(0, pos - 220) : min(len(text), pos + len(old) + 220)].casefold()
                if any(word in context for word in ("morph", "collapse", "restore", "geometry")):
                    text = text[:pos] + new + text[pos + len(old) :]
    if text == original:
        return False
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True


def _apply_ui_source_fixes(root: Path) -> list[str]:
    changed: list[str] = []
    qml = root / "src" / "ui" / "components" / "WidgetWindow.qml"
    if qml.is_file() and _patch_qml_widget(qml):
        changed.append(str(qml.relative_to(root)))

    for suffix in ("*.css", "*.html", "*.htm"):
        for path in root.rglob(suffix):
            if _patch_web_primary(path):
                changed.append(str(path.relative_to(root)))

    for suffix in ("*.py", "*.js", "*.qml"):
        for path in root.rglob(suffix):
            if path.resolve() == Path(__file__).resolve():
                continue
            if _patch_structural_easing(path):
                changed.append(str(path.relative_to(root)))
    return sorted(set(changed))


def apply_runtime_hotfix() -> dict[str, Any]:
    """Apply the integrated fix before controller/QML import.

    The function is deliberately idempotent. It is part of the complete app,
    not a user-facing patch step.
    """
    root = _project_root()
    changed = _apply_ui_source_fixes(root)
    bluetooth = _install_bluetooth_identity_patch()
    return {"marker": _PATCH_MARKER, "changed": changed, "bluetooth": bluetooth}


__all__ = [
    "apply_runtime_hotfix",
    "_choose_airpods",
    "_normalize_address",
    "_patch_qml_widget",
    "_patch_structural_easing",
    "_patch_web_primary",
]
