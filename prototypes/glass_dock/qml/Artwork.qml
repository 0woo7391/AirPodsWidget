import QtQuick

// Album art; without one, a gradient in the source app's colour with a note.
Rectangle {
    id: art
    property string source: ""
    property color tint: "transparent"
    radius: 10
    color: Theme.well
    clip: true
    gradient: tint.a > 0 && !source.length ? placeholder : null
    Gradient {
        id: placeholder
        GradientStop { position: 0; color: Qt.lighter(art.tint, 1.15) }
        GradientStop { position: 1; color: Qt.darker(art.tint, 1.8) }
    }
    Image {
        anchors.fill: parent
        source: art.source
        fillMode: Image.PreserveAspectCrop
        visible: status === Image.Ready
    }
    DockIcon {
        anchors.centerIn: parent
        size: Math.round(art.width * 0.42)
        name: "music"
        color: art.tint.a > 0 ? "#E6FFFFFF" : Theme.inkTertiary
        visible: !art.source.length
    }
}
