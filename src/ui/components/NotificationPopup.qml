import QtQuick
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    color: "transparent"
    visible: false
    width: 346
    height: 118
    opacity: 0
    title: "AirPods 알림"
    property UiTheme theme: UiTheme {}
    property int materialInset: 8
    property int materialCornerRadius: theme.controlRadius + 8

    onWidthChanged: appController.updateWindowShape(window)
    onHeightChanged: appController.updateWindowShape(window)

    Component.onCompleted: appController.applyWindowMaterial(window)

    Connections {
        target: appController
        function onSettingsChanged() { appController.applyWindowMaterial(window) }
    }

    function reveal(targetX, targetY) {
        x = targetX
        y = targetY
        show()
        animation.restart()
    }

    SequentialAnimation {
        id: animation
        ParallelAnimation {
            NumberAnimation { target: window; property: "opacity"; from: 0; to: 1; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { target: card; property: "scale"; from: 0.98; to: 1; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { target: card; property: "y"; from: 7; to: 0; duration: 180; easing.type: Easing.OutCubic }
        }
        PauseAnimation { duration: 3500 }
        ParallelAnimation {
            NumberAnimation { target: window; property: "opacity"; to: 0; duration: 180; easing.type: Easing.InCubic }
            NumberAnimation { target: card; property: "y"; to: 6; duration: 180; easing.type: Easing.InCubic }
        }
        ScriptAction { script: window.hide() }
    }

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 8
        radius: theme.cardRadius
        color: theme.popoverSurface
        border.width: 1
        border.color: theme.border

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            anchors.topMargin: 1
            height: 1
            color: theme.highlight
            opacity: 0.3
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 12

            Rectangle {
                width: 36; height: 36; radius: 11
                color: theme.surfaceSubtle
                border.width: 1
                border.color: theme.innerBorder
                MediaIcon {
                    anchors.centerIn: parent
                    width: 18
                    height: 18
                    icon: "bluetooth"
                    foreground: theme.textPrimary
                }
            }

            Column {
                Layout.fillWidth: true
                spacing: 3
                AnimatedText { text: appController.popupTitle; color: theme.textPrimary; fontFamily: theme.fontDisplay; pixelSize: theme.bodySize; fontWeight: theme.titleWeight; elide: Text.ElideRight; width: parent.width; height: 20; changeDuration: 150 }
                AnimatedText { text: appController.popupMessage; color: theme.textPrimary; fontFamily: theme.fontText; pixelSize: theme.labelSize; elide: Text.ElideRight; width: parent.width; height: 18; changeDuration: 130 }
                AnimatedText { text: appController.popupDetail; color: theme.textSecondary; fontFamily: theme.fontText; pixelSize: theme.captionSize; elide: Text.ElideRight; width: parent.width; height: 16; changeDuration: 130 }
            }
        }
    }
}
