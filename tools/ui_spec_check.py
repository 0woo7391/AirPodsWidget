from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "UI_REDESIGN_SPEC.md"


def require_text(path: Path, text: str, errors: list[str]) -> None:
    if text not in path.read_text(encoding="utf-8"):
        errors.append(f"{path.relative_to(ROOT)} is missing: {text}")


def main() -> int:
    errors: list[str] = []
    if not SPEC.is_file():
        print("Missing UI_REDESIGN_SPEC.md")
        return 1

    for text in (
        "## 1. 제품 목적과 변하지 않는 범위",
        "## 2. 참고 자료와 적용 원칙",
        "## 3. 새 시각 시스템",
        "## 4. 타이포그래피",
        "## 5. 위젯 레이아웃",
        "## 6. 모션 규칙",
        "## 9. 완료 조건",
        "Tabs Sliding",
        "Number Pop-in",
        "Icon Swap",
        "Modal Open/Close",
        "WindowDoesNotAcceptFocus",
        "Vanguard",
    ):
        require_text(SPEC, text, errors)

    implementation_checks = {
        "src/ui/components/UiTheme.qml": (
            "readonly property int space1: 8",
            "readonly property int motionStandard: 190",
            'readonly property string fontDisplay: "Segoe UI Variable Display"',
        ),
        "src/ui/components/AppleSlider.qml": (
            "readonly property int handleSize",
            "Behavior on width",
            "control.handleSize",
        ),
        "src/ui/components/AudioOutputSection.qml": (
            "id: selectedIndicator",
            "Behavior on x",
            "selectedIndex",
        ),
        "src/ui/components/WidgetWindow.qml": (
            "property real baseHeight: appController.mediaAvailable ? 464 : 302",
            "Qt.WindowDoesNotAcceptFocus",
            "Layout.preferredHeight: appController.mediaAvailable ? 150 : 0",
        ),
        "src/services/windows_material.py": (
            "DwmSetWindowAttribute",
            "DWMWA_SYSTEMBACKDROP_TYPE / DWMSBT_TRANSIENTWINDOW = Acrylic",
            "apply_window_shape(window)",
        ),
    }
    for relative, texts in implementation_checks.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"Missing implementation file: {relative}")
            continue
        for text in texts:
            require_text(path, text, errors)

    if errors:
        print("UI spec check failed:")
        print("\n".join(errors))
        return 1
    print("UI spec check passed: requirements and implementation anchors agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
