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
            "readonly property int motionMorphOpen: 400",
            "readonly property int motionMorphClose: 400",
            "readonly property int motionMorphFade: 200",
            "readonly property int motionMorphSlide: 6",
            'readonly property string fontDisplay: "Segoe UI Variable Display"',
            "readonly property int batteryTrackStart",
        ),
        "src/ui/components/AppleSlider.qml": (
            "readonly property int handleSize",
            "control.handleSize",
            "Behavior on value",
            "One value timeline drives both the fill and the handle",
        ),
        "src/ui/components/WidgetWindow.qml": (
            "property real morphProgress: 0",
            "readonly property real baseHeight:",
            "readonly property real minimizedContentOpacity:",
            "readonly property real expandedContentOpacity:",
            "readonly property real expandedRevealProgress:",
            "readonly property real expandedHeaderRevealProgress:",
            "readonly property real expandedBatteryRevealProgress:",
            "readonly property real expandedAudioRevealProgress:",
            "readonly property real expandedMediaRevealProgress:",
            "function setMinimized(value, source)",
            "function mediaSlotShouldBeVisible()",
            "function syncMediaLayoutAvailability()",
            "function chooseMorphPlacement(anchorX, anchorY)",
            "property bool morphPlacementResolved: false",
            "function requestWindowShapeUpdate()",
            "property bool mediaLayoutUpdatePending: false",
            "property bool layoutMediaAvailable: false",
            "readonly property real shellRadius:",
            "id: shapeUpdateTimer",
            "interval: 0",
            'objectName: "widgetToggleButton"',
            "iconProgress: window.morphProgress",
            "property bool morphExpandLeft: true",
            "property bool morphExpandUp: false",
            "easing.type: Easing.Linear",
            'property: "morphProgress"',
            "Layout.preferredWidth: 56",
            "property bool compact: appController.widgetLayoutMode === \"compact\"",
            "anchors.left: window.morphExpandLeft ? parent.left : toggleSlot.right",
            "spacing: 7",
            'objectName: "flowHeader"',
            'objectName: "flowBatteryOverview"',
            'objectName: "flowAudioOutput"',
            'objectName: "flowMediaSection"',
            "revealProgress: window.expandedBatteryRevealProgress",
            "revealProgress: window.expandedAudioRevealProgress",
            "revealProgress: window.expandedMediaRevealProgress",
            "opening: window.morphOpening",
            "Qt.WindowDoesNotAcceptFocus",
            "BatteryOverview",
            "CompactController",
            "Layout.preferredHeight: window.layoutMediaAvailable ? 146 : 0",
            "persistent: window.layoutMediaAvailable",
            "changeOffset: 0",
        ),
        "src/ui/components/VolumePopoverWindow.qml": (
            "Window {",
            "Qt.WindowDoesNotAcceptFocus",
            "function openPopup()",
            "function closePopup()",
            "property bool compactMode: false",
            "property int displayedValue:",
            "objectName: root.minimized ? \"minimizedVolumePointer\"",
            "property int popupX: 0",
            "orientation: Qt.Vertical",
        ),
        "src/ui/components/BatteryOverview.qml": (
            "property real revealProgress: 1.0",
            "transform: Translate",
            "estimatedRemainingUsage",
            "BatteryRow",
            "Item { Layout.preferredWidth: root.theme.batteryValueColumn }",
        ),
        "src/ui/components/AudioOutputSection.qml": (
            "id: selectedIndicator",
            "Behavior on x",
            "selectedIndex",
            "readonly property bool volumePopupOpen",
            "property real revealProgress: 1.0",
            "property real outputRevealProgress: root.revealProgress",
            "transform: Translate",
            'objectName: "outputButtonRow"',
            "function positionVolumePopup(anchorItem)",
            "function toggleVolumePopup(anchorItem)",
            "onClicked: root.toggleVolumePopup(compactVolumeButton)",
            'objectName: root.minimized ? "volumePopoverMinimized"',
            "VolumePopoverWindow",
        ),
        "src/ui/components/MediaSection.qml": (
            "property bool persistent: false",
            "property real revealProgress: 1.0",
            "opacity: slotVisible ? root.revealProgress : 0",
            "transform: Translate",
        ),
        "src/ui/components/CompactController.qml": (
            "property real revealProgress: 1.0",
            "property bool opening: false",
            "readonly property real batteryRevealProgress:",
            "readonly property real audioRevealProgress:",
            "readonly property real outputRevealProgress:",
            "readonly property real mediaRevealProgress:",
            'objectName: "compactBatteryGroup"',
            'objectName: "compactMediaStrip"',
            'icon: "charging"',
            "foreground: root.theme.yellow",
        ),
        "src/ui/components/BatteryRow.qml": (
            "Layout.preferredWidth: root.theme.batteryValueColumn",
            "horizontalAlignment: Text.AlignLeft",
            "verticalAlignment: Text.AlignVCenter",
            'icon: "charging"',
            "foreground: root.theme.yellow",
        ),
        "src/services/windows_material.py": (
            "DwmSetWindowAttribute",
            "DWMWA_SYSTEMBACKDROP_TYPE / DWMSBT_TRANSIENTWINDOW = Acrylic",
            "apply_window_shape(window)",
            "radius = min(radius",
        ),
        "src/controller.py": (
            "audioRefreshFinished = Signal(int, object, str)",
            "audioVolumeSetFinished = Signal(int, int, bool, str)",
            "name=\"WindowsAudioRefresh\"",
            "name=\"WindowsAudioVolumeRefresh\"",
            "name=\"WindowsAudioVolumeWrite\"",
            "name=\"WindowsAudioSwitch\"",
            "name=\"AirPodsAudioEndpointPoll\"",
            "def _audio_reconnect_poll_worker",
        ),
    }
    for relative, texts in implementation_checks.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"Missing implementation file: {relative}")
            continue
        for text in texts:
            require_text(path, text, errors)

    widget_source = (ROOT / "src/ui/components/WidgetWindow.qml").read_text(encoding="utf-8")
    if 'iconName: "more"' in widget_source or "appController.showSettings()" in widget_source:
        errors.append("WidgetWindow.qml must not expose a settings button; use the tray menu.")
    if "Behavior on height" in (ROOT / "src/ui/components/MediaSection.qml").read_text(encoding="utf-8"):
        errors.append("MediaSection.qml must not run a second height animation during the window morph.")
    if "Behavior on opacity" in (ROOT / "src/ui/components/MediaSection.qml").read_text(encoding="utf-8"):
        errors.append("MediaSection.qml must not run a second opacity animation during the window morph.")
    audio_source = (ROOT / "src/ui/components/AudioOutputSection.qml").read_text(encoding="utf-8")
    if "compactVolumeValueMouse" in audio_source:
        errors.append("AudioOutputSection.qml must have one compact volume trigger.")
    tray_source = (ROOT / "src/ui/components/TrayPopup.qml").read_text(encoding="utf-8")
    if 'text: "설정"' not in tray_source or "appController.showSettings()" not in tray_source:
        errors.append("TrayPopup.qml must remain the settings entry point.")

    if errors:
        print("UI spec check failed:")
        print("\n".join(errors))
        return 1
    print("UI spec check passed: requirements and implementation anchors agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
