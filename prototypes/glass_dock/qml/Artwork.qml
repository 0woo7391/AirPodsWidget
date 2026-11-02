import QtQuick

// Album art with a quiet placeholder.
Rectangle {
    id: art
    property string source: ""
    radius: 10
    color: Theme.well
    clip: true
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
        color: Theme.inkTertiary
        visible: !art.source.length
    }
}
