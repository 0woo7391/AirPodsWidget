import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property UiTheme theme
    property string value: ""

    implicitHeight: 16

    AnimatedText {
        anchors.fill: parent
        text: root.value
        color: root.theme.textSecondary
        fontFamily: root.theme.fontDisplay
        pixelSize: root.theme.labelSize
        fontWeight: root.theme.bodyWeight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        changeDuration: 130
    }

    EmptyIndicator {
        anchors.fill: parent
        theme: root.theme
        active: !root.value
    }
}
