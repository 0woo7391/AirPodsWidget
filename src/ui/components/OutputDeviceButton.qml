import QtQuick

Rectangle {
    id: root
    property UiTheme theme
    property string kind: "speaker"
    property string deviceName: ""
    property bool available: false
    property bool current: false
    property bool loading: false
    signal clicked()

    implicitWidth: 86
    implicitHeight: 30
    radius: 9
    color: root.current ? root.theme.accentSoft
         : mouse.containsMouse && root.available && !root.loading ? root.theme.hover : "transparent"
    border.width: 1
    border.color: root.current ? root.theme.accent
                  : root.available ? root.theme.border : root.theme.track
    opacity: root.available ? (root.loading ? 0.72 : 1) : 0.28
    scale: mouse.pressed && root.available && !root.loading ? 0.975 : 1

    Behavior on color { ColorAnimation { duration: 170; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: 170; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }

    Row {
        anchors.centerIn: parent
        spacing: 5

        Item {
            width: 13
            height: 13
            anchors.verticalCenter: parent.verticalCenter

            MediaIcon {
                anchors.fill: parent
                icon: root.kind === "airpods" ? "bluetooth" : root.kind
                foreground: root.current ? root.theme.textPrimary : root.theme.textSecondary
                visible: !root.loading
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
            }

            Row {
                anchors.centerIn: parent
                spacing: 2
                visible: root.loading
                opacity: visible ? 1 : 0
                Repeater {
                    model: 3
                    delegate: Rectangle {
                        required property int index
                        width: 3
                        height: 3
                        radius: 2
                        color: root.current ? root.theme.textPrimary : root.theme.textSecondary
                        opacity: 0.35
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            PauseAnimation { duration: index * 110 }
                            NumberAnimation { to: 1; duration: 220; easing.type: Easing.OutCubic }
                            NumberAnimation { to: 0.35; duration: 220; easing.type: Easing.InCubic }
                            PauseAnimation { duration: (2 - index) * 110 }
                        }
                    }
                }
                Behavior on opacity { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
            }
        }

        Text {
            text: root.kind === "airpods" ? "AirPods"
                  : root.kind === "headphones" ? "헤드폰" : "스피커"
            color: root.current ? root.theme.textPrimary : root.theme.textSecondary
            font.family: root.theme.fontText
            font.pixelSize: root.theme.captionSize
            font.weight: root.theme.labelWeight
            anchors.verticalCenter: parent.verticalCenter

            Behavior on color { ColorAnimation { duration: 170; easing.type: Easing.OutCubic } }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.available && !root.loading
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
