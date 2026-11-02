pragma Singleton
import QtQuick

// Liquid glass + bento tokens. Colors are white ink on a dark tint so the dock
// reads on light and dark wallpapers alike.
QtObject {
    readonly property color ink: "#F5F5F7"
    readonly property color inkSecondary: "#B8F5F5F7"
    readonly property color inkTertiary: "#6BF5F5F7"
    readonly property color good: "#7EE2A0"
    readonly property color warn: "#FFC861"
    readonly property color bad: "#FF7A70"
    readonly property color charge: "#8FD0FF"

    // With the native Acrylic backdrop the tint can stay light; without it the
    // card must carry the contrast by itself.
    readonly property color glassFill: "#4D17171C"
    readonly property color glassFillFallback: "#8C1B1B21"
    // A grown card floats over its neighbours, so it must hide them.
    readonly property color glassFillLifted: "#EB1C1C22"
    readonly property real dimmedOpacity: 0.45
    readonly property real dimmedScale: 0.97
    readonly property color stroke: "#29FFFFFF"
    readonly property color strokeLit: "#66FFFFFF"
    readonly property color well: "#1AFFFFFF"
    readonly property color wellHover: "#2EFFFFFF"
    readonly property color wellPressed: "#40FFFFFF"

    readonly property int dockWidth: 176
    readonly property int gap: 10
    readonly property int pad: 14
    readonly property int radius: 22
    readonly property int radiusInner: 12
    readonly property int detailWidth: 300

    // Minimized dock: a rail of icons that widens to show labels on hover.
    readonly property int railWidth: 52
    readonly property int railRow: 48
    readonly property int railLabelWidth: 150

    readonly property int hoverOpenDelay: 140
    readonly property int hoverCloseDelay: 260
    readonly property int fadeDuration: 140

    // Cursor magnification (#208): peak extra scale and how far (px) it reaches.
    readonly property real magnifyCard: 0.05
    readonly property real magnifyRail: 0.12
    readonly property real magnifyTile: 0.24
    readonly property real magnifyReach: 110

    readonly property var numberFeatures: ({ "tnum": 1 })

    // Under-damped spring step response, shared by the dock and the island.
    function spring(w0, zeta, t) {
        if (t <= 0) return 0
        const wd = w0 * Math.sqrt(1 - zeta * zeta)
        return 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + zeta * w0 / wd * Math.sin(wd * t))
    }
    function seg(v, a0, a1) { return Math.max(0, Math.min(1, (v - a0) / (a1 - a0))) }
    // Bell-shaped falloff of the magnification with the pointer's distance.
    function magnify(distance, reach) { return Math.exp(-2 * distance * distance / (reach * reach)) }
}
