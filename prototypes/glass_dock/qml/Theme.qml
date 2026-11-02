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
    readonly property real dimmedOpacity: 0.28
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

    readonly property int hoverOpenDelay: 140
    readonly property int hoverCloseDelay: 260
    readonly property int expandDuration: 260
    readonly property int fadeDuration: 140

    readonly property var numberFeatures: ({ "tnum": 1 })
}
