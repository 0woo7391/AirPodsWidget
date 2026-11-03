import QtQuick

// A volume slider with a ruler on top: the usual bar (filled to the value, a round
// knob) and above it short ticks every 5 and long ticks every 10. Ticks near the knob
// swell, and when there is room the tens near the knob show their numbers, fading with
// distance. Drag, click or scroll to change it.
Item {
    id: slider
    property real value: 0
    property real from: 0
    property real to: 100
    property bool enabled: true
    property real trackHeight: 6
    property real knobSize: 16
    signal moved(int value)
    implicitHeight: 40

    readonly property real span: to - from
    readonly property real step: width / (span / 5)           // pixels between ticks
    readonly property bool labelled: step * 2 >= 11             // room for "20" and "30" near the knob
    readonly property real ratio: Math.max(0, Math.min(1, (value - from) / span))
    property real shownRatio: ratio
    Behavior on shownRatio { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    readonly property real knobX: shownRatio * width
    readonly property real tickBottom: track.y - 4

    // ---- the ruler -------------------------------------------------------------
    Repeater {
        model: Math.round(slider.span / 5) + 1
        Item {
            id: tick
            required property int index
            readonly property real tickValue: slider.from + index * 5
            readonly property bool ten: tickValue % 10 === 0
            readonly property real distance: Math.abs(x - slider.knobX)
            readonly property real near: Theme.magnify(distance, Math.max(24, slider.step * 4))
            x: index * slider.step
            width: 1; height: slider.tickBottom
            Rectangle {
                width: 1.5; radius: 0.75
                height: (tick.ten ? 6 : 3) + 4 * tick.near
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                color: tick.tickValue <= slider.value ? Theme.inkSecondary : Theme.inkTertiary
                opacity: 0.55 + 0.45 * tick.near
            }
            Text {
                visible: slider.labelled && tick.ten && opacity > 0.02
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: 11
                text: tick.tickValue
                // Only the tens nearest the knob; on a tight ruler just the closest one.
                opacity: slider.step * 2 < 16
                    ? (tick.tickValue === Math.round(slider.value / 10) * 10 ? 1 : 0)
                    : Theme.magnify(tick.distance, slider.step * 2.5)
                Behavior on opacity { NumberAnimation { duration: 160 } }
                color: Theme.inkSecondary
                font.family: dockFont; font.pixelSize: 9; font.features: Theme.numberFeatures
            }
        }
    }

    // ---- the bar -----------------------------------------------------------------
    Rectangle {
        id: track
        anchors.bottom: parent.bottom; anchors.bottomMargin: (slider.knobSize - slider.trackHeight) / 2
        width: parent.width; height: slider.trackHeight; radius: height / 2
        color: Theme.well
        Rectangle {
            width: Math.max(track.height, slider.knobX); height: track.height; radius: track.radius
            color: Theme.ink
            // A soft glow on the filled part.
            Rectangle {
                anchors.fill: parent; anchors.margins: -2
                radius: height / 2
                color: "transparent"
                border.width: 2; border.color: "#1FFFFFFF"
            }
        }
    }
    Rectangle {
        id: knob
        width: slider.knobSize; height: width; radius: width / 2
        x: slider.knobX - width / 2
        anchors.verticalCenter: track.verticalCenter
        color: Theme.ink
        border.color: "#33000000"; border.width: 1
        scale: press.pressed ? 1.15 : hover.hovered ? 1.06 : 1
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
    }
    HoverHandler { id: hover }
    MouseArea {
        id: press
        anchors.fill: parent
        anchors.margins: -6
        enabled: slider.enabled
        cursorShape: Qt.PointingHandCursor
        function set(mouseX) {
            const v = slider.from + Math.max(0, Math.min(1, (mouseX - 6) / slider.width)) * slider.span
            slider.moved(Math.round(v))
        }
        onPressed: function(mouse) { set(mouse.x) }
        onPositionChanged: function(mouse) { if (pressed) set(mouse.x) }
    }
    WheelHandler {
        enabled: slider.enabled
        onWheel: function(event) {
            slider.moved(Math.max(slider.from, Math.min(slider.to, Math.round(slider.value) + (event.angleDelta.y > 0 ? 2 : -2))))
        }
    }
}
