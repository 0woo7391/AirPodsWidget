import QtQuick

Rectangle {
    id: root
    property bool checked: false
    property UiTheme theme
    signal toggled(bool value)

    implicitWidth: 44
    implicitHeight: 25
    radius: height / 2
    color: checked ? theme.accent : theme.track
    scale: switchMouse.pressed ? 0.96 : 1

    Behavior on color { ColorAnimation { duration: 180 } }
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

    Rectangle {
        width: 21
        height: 21
        radius: 11
        y: 2
        x: root.checked ? root.width - width - 2 : 2
        color: root.checked ? (root.theme.dark ? "#0A0A0A" : "#FFFFFF") : root.theme.textPrimary

        Behavior on x { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        id: switchMouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }
}
