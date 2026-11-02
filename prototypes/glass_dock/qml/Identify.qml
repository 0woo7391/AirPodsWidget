import QtQuick

// Big screen number shown on every monitor by "화면 식별", matching the map in the settings.
Item {
    id: root
    width: 320
    height: 220
    property int number: 1
    property string label: ""

    Rectangle {
        anchors.fill: parent
        radius: 36
        color: "#E6141418"
        border.width: 2
        border.color: "#38C6FF"
        Column {
            anchors.centerIn: parent
            spacing: 6
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.number
                color: "#F5F5F7"
                font.family: dockFont; font.pixelSize: 112; font.weight: Font.DemiBold
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.label
                color: "#B8F5F5F7"
                font.family: dockFont; font.pixelSize: 16
            }
        }
    }
}
