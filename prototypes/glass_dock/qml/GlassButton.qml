import QtQuick

// Round or pill control on the glass. The icon is optically centered.
Item {
    id: button
    property string icon: ""
    property string pose: ""
    property string text: ""
    property bool accent: false
    property bool selected: false
    property real iconSize: 16
    property bool mirrorIcon: false
    signal clicked()

    implicitWidth: text.length ? label.implicitWidth + (icon.length ? iconSize + 30 : 28) : 34
    implicitHeight: 34
    opacity: enabled ? 1 : 0.38

    Rectangle {
        anchors.fill: parent
        radius: button.text.length ? Theme.radiusInner : height / 2
        color: button.accent ? Theme.ink
            : mouse.pressed ? Theme.wellPressed
            : mouse.containsMouse || button.selected ? Theme.wellHover : Theme.well
        border.width: button.selected && !button.accent ? 1 : 0
        border.color: Theme.strokeLit
        scale: mouse.pressed ? 0.96 : 1
        Behavior on color { ColorAnimation { duration: 110 } }
        Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
    }
    Row {
        anchors.centerIn: parent
        spacing: 7
        DockIcon {
            visible: button.icon.length > 0
            anchors.verticalCenter: parent.verticalCenter
            name: button.icon
            pose: button.pose
            mirror: button.mirrorIcon
            size: button.iconSize
            color: button.accent ? "#16161A" : Theme.ink
        }
        Text {
            id: label
            visible: button.text.length > 0
            anchors.verticalCenter: parent.verticalCenter
            text: button.text
            color: button.accent ? "#16161A" : Theme.ink
            font.family: dockFont
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: button.enabled
        onClicked: button.clicked()
    }
}
