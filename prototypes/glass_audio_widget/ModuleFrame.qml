import QtQuick

Item {
    id: frame
    required property string moduleId
    required property Item canvas
    property bool editing: false
    readonly property point visualTranslation: Qt.point(drag.active ? drag.activeTranslation.x : 0,drag.active ? drag.activeTranslation.y : 0)
    property point lastDrop
    signal dropped(string source, real px, real py)
    transform: Translate {
        x: drag.active ? drag.activeTranslation.x : 0
        y: drag.active ? drag.activeTranslation.y : 0
    }
    z: drag.active ? 30 : 0
    Rectangle {
        anchors.fill: parent; anchors.margins: -4
        visible: frame.editing; radius: 14
        color: drag.active ? "#443C3C3C" : "transparent"
        border.color: "#CCCCCC"; border.width: 1
    }
    DragHandler {
        id: drag; target: null; enabled: frame.editing
        onActiveTranslationChanged: {
            frame.lastDrop=frame.parent.mapToItem(frame.canvas,
                frame.x+frame.width/2+activeTranslation.x,frame.y+frame.height/2+activeTranslation.y)
        }
        onActiveChanged: {
            if (!active) frame.dropped(frame.moduleId,frame.lastDrop.x,frame.lastDrop.y)
        }
    }
    MouseArea {
        anchors.fill: parent; enabled: frame.editing
        acceptedButtons: Qt.NoButton; cursorShape: Qt.OpenHandCursor
    }
}
