import QtQuick
import QtQuick.Effects

// One glass pane: tinted body, a soft top sheen, a hairline rim and a lit top
// edge. The blur itself comes from the window's native Acrylic backdrop.
// `lift` (0..1) raises the pane with a soft shadow; `lit` brightens the rim
// under the pointer before the card opens.
Item {
    id: surface
    property real radius: Theme.radius
    property bool lifted: false
    property real lift: 0
    property bool lit: false

    RectangularShadow {
        anchors.fill: parent
        offset.y: 10
        radius: surface.radius
        blur: 28
        spread: -4
        color: "#8C000000"
        opacity: surface.lift
        visible: surface.lift > 0.01
    }
    Rectangle {
        anchors.fill: parent
        radius: surface.radius
        color: surface.lifted ? Theme.glassFillLifted : dockHost.nativeGlass ? Theme.glassFill : Theme.glassFillFallback
        Behavior on color { ColorAnimation { duration: Theme.fadeDuration } }
    }
    Rectangle {
        anchors.fill: parent
        radius: surface.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: surface.lifted || surface.lit ? "#26FFFFFF" : "#1AFFFFFF" }
            GradientStop { position: 0.42; color: "#06FFFFFF" }
            GradientStop { position: 1.0; color: "#00FFFFFF" }
        }
    }
    Rectangle {
        anchors.fill: parent
        radius: surface.radius
        color: "transparent"
        border.width: 1
        border.color: surface.lifted || surface.lit ? Theme.strokeLit : Theme.stroke
        Behavior on border.color { ColorAnimation { duration: Theme.fadeDuration } }
    }
    Rectangle {
        x: surface.radius * 0.7
        y: 1
        width: parent.width - surface.radius * 1.4
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#00FFFFFF" }
            GradientStop { position: 0.5; color: surface.lifted || surface.lit ? "#8CFFFFFF" : "#59FFFFFF" }
            GradientStop { position: 1.0; color: "#00FFFFFF" }
        }
    }
}
