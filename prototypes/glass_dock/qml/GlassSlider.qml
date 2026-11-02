import QtQuick

// Horizontal level control: thick track, ink fill, round thumb.
Item {
    id: slider
    property real value: 0
    property real from: 0
    property real to: 100
    signal moved(real value)
    implicitHeight: 24
    readonly property real ratio: Math.max(0, Math.min(1, (value - from) / (to - from)))

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width; height: 6; radius: 3
        color: Theme.well
        Rectangle {
            width: Math.max(track.height, track.width * slider.ratio); height: track.height; radius: track.radius
            color: Theme.ink
        }
    }
    Rectangle {
        width: 18; height: 18; radius: 9
        anchors.verticalCenter: parent.verticalCenter
        x: (slider.width - width) * slider.ratio
        color: Theme.ink
        border.color: "#33000000"; border.width: 1
        scale: drag.pressed ? 1.12 : 1
        Behavior on scale { NumberAnimation { duration: 110 } }
    }
    MouseArea {
        id: drag
        anchors.fill: parent
        anchors.margins: -6
        function update(mouseX) {
            const ratio = Math.max(0, Math.min(1, (mouseX - 6) / slider.width))
            slider.moved(Math.round(slider.from + ratio * (slider.to - slider.from)))
        }
        onPressed: function(mouse) { update(mouse.x) }
        onPositionChanged: function(mouse) { if (pressed) update(mouse.x) }
    }
    WheelHandler {
        onWheel: function(event) {
            slider.moved(Math.max(slider.from, Math.min(slider.to, slider.value + (event.angleDelta.y > 0 ? 2 : -2))))
        }
    }
}
