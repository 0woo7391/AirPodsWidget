from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "UI_REDESIGN_SPEC.md",
    "UI_V2_DESIGN_BRIEF.md",
    "assets/low_power_warning.mp3",
    "assets/app.ico",
    "assets/fonts/Pretendard-Regular.otf",
    "assets/fonts/Pretendard-Medium.otf",
    "assets/fonts/Pretendard-SemiBold.otf",
    "assets/fonts/LICENSE.txt",
    "src/ui/Main.qml",
    "src/ui/components/WidgetWindow.qml",
    "src/ui/components/TrayPopup.qml",
    "src/ui/components/SettingsWindow.qml",
    "src/ui/components/NotificationPopup.qml",
    "packaging/AppxManifest.xml",
]
EXPECTED_ALERT_SHA256 = "84a9b99a5fffdf4e33fec6799eadb5f2880a71016cd280449abf4df160dcb9e6"


def validate_required_assets() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Missing or empty required file: {relative}")
    audio = ROOT / "assets" / "low_power_warning.mp3"
    if audio.is_file():
        digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        if digest != EXPECTED_ALERT_SHA256:
            errors.append(f"Low-power alert SHA-256 mismatch: {digest}")
    return errors


def validate_python() -> list[str]:
    errors: list[str] = []
    for path in list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path}: {exc}")
    return errors


def validate_qml() -> list[str]:
    errors: list[str] = []
    pairs = {"{": "}", "[": "]", "(": ")"}
    closing = {value: key for key, value in pairs.items()}
    for path in (ROOT / "src" / "ui").rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        stack: list[tuple[str, int]] = []
        quote = None
        escaped = False
        line_comment = False
        block_comment = False
        i = 0
        while i < len(text):
            ch = text[i]
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if line_comment:
                if ch == "\n":
                    line_comment = False
                i += 1
                continue
            if block_comment:
                if ch == "*" and nxt == "/":
                    block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
                i += 1
                continue
            if ch == "/" and nxt == "/":
                line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                block_comment = True
                i += 2
                continue
            if ch in {'"', "'"}:
                quote = ch
            elif ch in pairs:
                stack.append((ch, i))
            elif ch in closing:
                if not stack or stack[-1][0] != closing[ch]:
                    errors.append(f"{path}: unmatched {ch} at offset {i}")
                    break
                stack.pop()
            i += 1
        if stack:
            errors.append(f"{path}: unclosed {stack[-1][0]} at offset {stack[-1][1]}")
        if "=>" in text:
            errors.append(f"{path}: avoid arrow handlers for broad Qt compatibility")
    return errors


def validate_media_package_manifest() -> list[str]:
    path = ROOT / "packaging" / "AppxManifest.xml"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    required = (
        'ProcessorArchitecture="x64"',
        'Executable="AirPodsWidget.exe"',
        '<rescap:Capability Name="runFullTrust"',
        '<uap7:Capability Name="globalMediaControl"',
    )
    return [
        f"{path}: missing required package declaration: {fragment}"
        for fragment in required
        if fragment not in text
    ]


def main() -> int:
    errors = (
        validate_required_assets()
        + validate_python()
        + validate_qml()
        + validate_media_package_manifest()
    )
    if errors:
        print("\n".join(errors))
        return 1
    print("Project validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
