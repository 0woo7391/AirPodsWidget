import QtQuick

// Thin battery/level track with a rounded fill.
Rectangle {
    id: meter
    property real value: -1
    property color fill: Theme.ink
    implicitHeight: 4
    radius: height / 2
    color: Theme.well
    Rectangle {
        width: meter.value < 0 ? 0 : Math.max(meter.height, meter.width * Math.min(100, meter.value) / 100)
        height: meter.height
        radius: meter.radius
        color: meter.fill
        visible: meter.value >= 0
        Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }
}
