import QtQuick

QtObject {
    readonly property bool dark: appController.theme === "dark"

    // The UI follows a small, explicit scale so a short widget does not grow
    // accidental gaps as optional sections appear or disappear.
    readonly property int space1: 8
    readonly property int space2: 12
    readonly property int space3: 16
    readonly property int space4: 20
    readonly property int shellRadius: 24
    readonly property int cardRadius: 16
    readonly property int controlRadius: 10
    readonly property int motionFast: 140
    readonly property int motionStandard: 190
    readonly property int motionLayout: 220
    readonly property int motionWindow: 280
    // Dropdown-menu-morph timing: both directions leave enough samples for
    // the window geometry to travel without a mid-transition snap.
    readonly property int motionMorphOpen: 400
    readonly property int motionMorphClose: 400
    readonly property int motionMorphFade: 200
    // Reveal motion is deliberately restrained; the shell supplies the large
    // movement, while content only travels a few pixels into place.
    readonly property int motionMorphSlide: 6

    // Battery rows share these columns in the flow layout. Keeping the
    // geometry in one place prevents the estimate row and CASE row from
    // drifting away from L/R when the window is resized.
    readonly property int batteryLabelColumn: 36
    readonly property int batteryStatusColumn: 10
    readonly property int batteryLabelStatusGap: 5
    readonly property int batteryTrackGap: 6
    readonly property int batteryValueGap: 8
    readonly property int batteryValueColumn: 34
    readonly property int batteryTrackStart: batteryLabelColumn + batteryLabelStatusGap + batteryStatusColumn + batteryTrackGap

    // Map the user's background-opacity setting onto a safe material range.
    // The minimum tint preserves contrast on the opposite-color wallpaper;
    // foreground text and controls are never included in this opacity.
    function materialColor(baseColor, opacity, minimumAlpha, maximumAlpha) {
        var normalized = Math.max(0, Math.min(1, (opacity - 0.55) / 0.45))
        var alpha = minimumAlpha + (maximumAlpha - minimumAlpha) * normalized
        return Qt.rgba(baseColor.r, baseColor.g, baseColor.b, alpha)
    }

    function shellColor(baseColor, opacity) {
        // The shell is the translucent material layer. Its tint is deliberately
        // lower than the previous card so a Windows DWM backdrop can remain
        // visible through it without sacrificing text contrast.
        return materialColor(baseColor, opacity, dark ? 0.34 : 0.48, dark ? 0.64 : 0.78)
    }

    function insetColor(baseColor, opacity) {
        return materialColor(baseColor, opacity, dark ? 0.10 : 0.18, dark ? 0.20 : 0.30)
    }

    function panelColor(baseColor, opacity) {
        return materialColor(baseColor, opacity, dark ? 0.05 : 0.12, dark ? 0.13 : 0.23)
    }

    // These stops are intentionally separate from the solid color tokens.
    // A glass surface needs a faint directional reflection and a darker lower
    // edge; one opaque charcoal fill reads as a normal card even when DWM is
    // supplying a backdrop behind the window.
    function glassShellTop(opacity) {
        return dark
            ? materialColor(Qt.rgba(0.12, 0.12, 0.12, 1), opacity, 0.30, 0.42)
            : materialColor(Qt.rgba(1, 1, 1, 1), opacity, 0.62, 0.86)
    }

    function glassShellMid(opacity) {
        return dark
            ? materialColor(Qt.rgba(0.08, 0.08, 0.08, 1), opacity, 0.40, 0.52)
            : materialColor(Qt.rgba(1, 1, 1, 1), opacity, 0.48, 0.72)
    }

    function glassShellBottom(opacity) {
        return dark
            ? materialColor(Qt.rgba(0, 0, 0, 1), opacity, 0.50, 0.62)
            : materialColor(Qt.rgba(0.65, 0.65, 0.65, 1), opacity, 0.05, 0.10)
    }

    function glassCardTop(opacity) {
        return dark
            ? materialColor(Qt.rgba(0.14, 0.14, 0.14, 1), opacity, 0.30, 0.42)
            : materialColor(Qt.rgba(1, 1, 1, 1), opacity, 0.42, 0.68)
    }

    function glassCardBottom(opacity) {
        return dark
            ? materialColor(Qt.rgba(0.03, 0.03, 0.03, 1), opacity, 0.40, 0.50)
            : materialColor(Qt.rgba(0.70, 0.70, 0.70, 1), opacity, 0.04, 0.08)
    }

    function glassInsetTop(opacity) {
        return dark
            ? materialColor(Qt.rgba(0.04, 0.04, 0.04, 1), opacity, 0.42, 0.54)
            : materialColor(Qt.rgba(1, 1, 1, 1), opacity, 0.30, 0.56)
    }

    function glassInsetBottom(opacity) {
        return dark
            ? materialColor(Qt.rgba(0, 0, 0, 1), opacity, 0.50, 0.62)
            : materialColor(Qt.rgba(0.70, 0.70, 0.70, 1), opacity, 0.04, 0.08)
    }
    // The utility palette stays neutral; color is reserved for semantic state
    // and selection feedback rather than decoration.
    readonly property color surface: dark ? "#D00A0A0A" : "#EAF5F5F5"
    readonly property color surfaceTop: surface
    readonly property color surfaceBottom: surface
    readonly property color surfaceRaised: dark ? "#E0161616" : "#F4FFFFFF"
    readonly property color surfaceInset: dark ? "#26161616" : "#28FFFFFF"
    readonly property color surfaceInsetTop: surfaceInset
    readonly property color surfaceInsetBottom: surfaceInset
    readonly property color surfaceSubtle: dark ? "#0CFFFFFF" : "#10000000"
    readonly property color surfaceSubtleTop: surfaceSubtle
    readonly property color surfaceSubtleBottom: surfaceSubtle
    // Settings are information-dense, so they use a regular, more opaque
    // neutral surface while keeping the same visual language.
    readonly property color settingsSurface: dark ? "#E10A0A0A" : "#F2F5F5F5"
    readonly property color settingsSurfaceTop: settingsSurface
    readonly property color settingsSurfaceBottom: settingsSurface
    readonly property color settingsPanel: dark ? "#E5161616" : "#FAFFFFFF"
    readonly property color settingsPanelTop: settingsPanel
    readonly property color settingsPanelBottom: settingsPanel
    readonly property color settingsBorder: dark ? "#35FFFFFF" : "#40B2B2B2"
    readonly property color settingsControl: dark ? "#18FFFFFF" : "#12000000"

    readonly property color widgetSurface: dark ? "#161717" : "#F4F4F1"
    readonly property color widgetSurfaceTop: widgetSurface
    readonly property color widgetSurfaceBottom: widgetSurface
    readonly property color widgetPanel: dark ? "#1C1D1D" : "#FFFFFF"
    readonly property color widgetPanelTop: widgetPanel
    readonly property color widgetPanelBottom: widgetPanel
    readonly property color widgetInset: dark ? "#1B1C1C" : "#FFFFFF"
    readonly property color widgetInsetTop: widgetInset
    readonly property color widgetInsetBottom: widgetInset
    // Popovers sit on top of live content, so they need a readable surface of
    // their own instead of allowing the underlying numbers to bleed through.
    readonly property color popoverSurface: dark ? "#F12A2A2A" : "#F9F9F5"
    readonly property color border: dark ? "#38FFFFFF" : "#40B2B2B2"
    readonly property color innerBorder: dark ? "#18FFFFFF" : "#35FFFFFF"
    readonly property color sectionBorder: dark ? "#32D4D4D4" : "#4CB2B2B2"
    readonly property color highlight: dark ? "#E5E5E5" : "#FFFFFF"
    readonly property color textPrimary: dark ? "#FFFFFF" : "#1B1B1B"
    readonly property color textSecondary: dark ? "#C2C2C2" : "#686868"
    readonly property color textTertiary: dark ? "#686868" : "#8A8A8A"
    readonly property color batteryValue: dark ? "#EDEDED" : "#1B1B1B"
    readonly property color accent: dark ? "#FFFFFF" : "#0A0A0A"
    readonly property color accentSoft: dark ? "#24FFFFFF" : "#180A0A0A"
    readonly property color green: dark ? "#4ADE80" : "#22A55A"
    readonly property color yellow: dark ? "#F2C14E" : "#A66B08"
    readonly property color batteryHealthy: dark ? "#BBDCC6" : "#2E7A4D"
    readonly property color orange: dark ? "#E59A3A" : "#B86A18"
    readonly property color red: dark ? "#F07171" : "#C23B3B"
    readonly property color track: dark ? "#3A3A3A" : "#B2B2B2"
    readonly property color hover: dark ? "#18FFFFFF" : "#14000000"
    readonly property color shadow: dark ? "#000000" : "#686868"
    // Segoe UI is the Windows-native display face; Korean falls back to the
    // bundled Pretendard registration. This gives Latin and numeric values a
    // calmer, less heavy rhythm than using Pretendard for every role.
    readonly property string fontDisplay: "Segoe UI Variable Display"
    readonly property string fontText: "Pretendard"
    readonly property int titleSize: 18
    readonly property int bodySize: 14
    readonly property int labelSize: 12
    readonly property int valueSize: 14
    readonly property int captionSize: 12
    readonly property int microSize: 10
    readonly property int titleWeight: Font.Medium
    readonly property int bodyWeight: Font.Normal
    readonly property int labelWeight: Font.Medium
    readonly property int valueWeight: Font.Medium
}
