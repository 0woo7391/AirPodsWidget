import QtQuick

// One glass pane: tinted body, a soft top sheen, a hairline rim and a lit top
// edge. The blur itself comes from the window's native Acrylic backdrop.
Item {
    id: surface
    property real radius: Theme.radius
    property bool lifted: false

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
            GradientStop { position: 0.0; color: surface.lifted ? "#26FFFFFF" : "#1AFFFFFF" }
            GradientStop { position: 0.42; color: "#06FFFFFF" }
            GradientStop { position: 1.0; color: "#00FFFFFF" }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.fadeDuration } }
    }
    Rectangle {
        anchors.fill: parent
        radius: surface.radius
        color: "transparent"
        border.width: 1
        border.color: surface.lifted ? Theme.strokeLit : Theme.stroke
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
            GradientStop { position: 0.5; color: surface.lifted ? "#8CFFFFFF" : "#59FFFFFF" }
            GradientStop { position: 1.0; color: "#00FFFFFF" }
        }
    }
}
