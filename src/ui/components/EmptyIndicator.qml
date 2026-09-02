import QtQuick

// A quiet visual placeholder. It communicates an empty value without adding a
// literal dash that competes with the battery labels and numeric columns.
Item {
    id: root
    property UiTheme theme
    property bool active: true
    property real indicatorOpacity: active ? 0.72 : 0

    implicitWidth: 18
    implicitHeight: 18
    opacity: root.indicatorOpacity
    scale: root.active ? 1 : 0.88

    Rectangle {
        anchors.centerIn: parent
        width: 11
        height: 3
        radius: 1.5
        color: root.theme ? root.theme.textTertiary : "#777777"
    }

    Behavior on opacity {
        NumberAnimation { duration: root.theme ? root.theme.motionFast : 140; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
        NumberAnimation { duration: root.theme ? root.theme.motionStandard : 190; easing.type: Easing.OutCubic }
    }
}
