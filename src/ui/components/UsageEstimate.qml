import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property UiTheme theme
    property string value: "—"

    implicitHeight: 16

    Text {
        anchors.centerIn: parent
        text: root.value
        color: root.theme.textSecondary
        font.family: root.theme.fontDisplay
        font.pixelSize: root.theme.labelSize
        font.weight: root.theme.bodyWeight
        horizontalAlignment: Text.AlignHCenter
    }
}
