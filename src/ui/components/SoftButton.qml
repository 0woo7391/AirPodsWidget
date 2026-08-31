import QtQuick

Rectangle {
    id: root
    property string text: ""
    property string iconName: ""
    property string displayedIcon: iconName
    property bool primary: false
    property UiTheme theme
    signal clicked()

    implicitWidth: 42
    implicitHeight: 42
    radius: height / 2
    color: primary ? theme.textPrimary : (mouse.containsMouse ? theme.hover : "transparent")
    border.width: primary ? 0 : 1
    border.color: theme.border
    opacity: enabled ? 1 : 0.28
    scale: mouse.pressed ? 0.96 : 1

    Behavior on color { ColorAnimation { duration: 160 } }
    Behavior on border.color { ColorAnimation { duration: 160 } }
    Behavior on border.width { NumberAnimation { duration: 130 } }
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

    Item {
        id: iconHolder
        anchors.centerIn: parent
        width: root.primary ? 18 : 17
        height: width

        MediaIcon {
            anchors.fill: parent
            visible: root.iconName.length > 0
            icon: root.displayedIcon
            foreground: root.primary ? (root.theme.dark ? "#151517" : "white") : root.theme.textPrimary
        }

        Text {
            anchors.centerIn: parent
            visible: root.iconName.length === 0
            text: root.text
            color: root.primary ? (root.theme.dark ? "#151517" : "white") : root.theme.textPrimary
            font.family: root.theme.fontText
            font.pixelSize: root.primary ? 17 : 20
            font.weight: Font.DemiBold
            renderType: Text.NativeRendering
        }
    }

    SequentialAnimation {
        id: iconSwap
        NumberAnimation { target: iconHolder; property: "opacity"; to: 0; duration: 85; easing.type: Easing.InCubic }
        ScriptAction { script: root.displayedIcon = root.iconName }
        NumberAnimation { target: iconHolder; property: "opacity"; to: 1; duration: 135; easing.type: Easing.OutCubic }
    }

    onIconNameChanged: {
        if (displayedIcon !== iconName)
            iconSwap.restart()
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
