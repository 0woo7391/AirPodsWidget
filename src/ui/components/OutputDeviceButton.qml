import QtQuick

Item {
    id: root
    property UiTheme theme
    property string kind: "speaker"
    property string deviceName: ""
    property bool available: false
    property bool current: false
    signal clicked()

    implicitWidth: 82
    implicitHeight: 28
    opacity: available ? 1 : 0.28

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    readonly property string displayLabel: root.kind === "airpods" ? "AirPods"
                                           : root.kind === "headphones" ? "헤드폰" : "스피커"

    Rectangle {
        id: buttonSurface
        anchors.fill: parent
        radius: 8
        color: root.current ? "transparent"
             : mouse.containsMouse && root.available ? root.theme.hover : "transparent"
        border.width: 1
        border.color: root.current ? "transparent"
                      : root.available ? root.theme.border : root.theme.track
        scale: mouse.pressed && root.available ? 0.975 : 1.0

        Behavior on color { ColorAnimation { duration: 190; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 190; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: root.current ? root.theme.accent : "transparent"
            opacity: root.current ? 0.26 : 0

            Behavior on border.color { ColorAnimation { duration: 190 } }
            Behavior on opacity { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
        }

        Row {
            anchors.centerIn: parent
            spacing: 5

            MediaIcon {
                id: deviceIcon
                width: 13
                height: 13
                anchors.verticalCenter: parent.verticalCenter
                icon: root.kind === "airpods" ? "bluetooth" : root.kind
                foreground: root.current ? root.theme.textPrimary : root.theme.textSecondary

                Behavior on foreground { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
            }

            Text {
                id: deviceLabel
                text: root.displayLabel
                color: root.current ? root.theme.textPrimary : root.theme.textSecondary
                font.family: root.theme.fontText
                font.pixelSize: root.theme.captionSize
                font.weight: root.theme.labelWeight
                anchors.verticalCenter: parent.verticalCenter

                Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
            }
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: root.available
            hoverEnabled: true
            cursorShape: root.available ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.clicked()
        }
    }
}
