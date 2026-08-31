import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
    color: "transparent"
    visible: false
    width: 360
    height: appController.mediaAvailable ? 498 : 340
    title: "AirPods"
    property UiTheme theme: UiTheme {}
    property int materialInset: 8
    property int materialCornerRadius: theme.shellRadius

    onWidthChanged: appController.updateWindowShape(window)
    onHeightChanged: appController.updateWindowShape(window)

    Component.onCompleted: appController.applyWindowMaterial(window)

    Connections {
        target: appController
        function onSettingsChanged() { appController.applyWindowMaterial(window) }
    }

    Behavior on height {
        NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
    }

    onActiveChanged: {
        if (!window.active && window.visible)
            closeTimer.restart()
    }

    Timer {
        id: closeTimer
        interval: 160
        onTriggered: if (!window.active) window.hide()
    }

    function reveal(targetX, targetY) {
        x = targetX
        y = targetY
        show()
        requestActivate()
    }

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 8
        radius: theme.shellRadius
        color: theme.shellColor(theme.widgetSurface, appController.widgetOpacity)
        border.width: 1
        border.color: theme.border
        clip: true

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: theme.innerBorder
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 18
            anchors.bottomMargin: 16
            spacing: 0

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 42

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: appController.deviceName
                    color: theme.textPrimary
                    font.family: theme.fontDisplay
                    font.pixelSize: theme.titleSize
                    font.weight: theme.titleWeight
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 86
                    height: 28
                    radius: 14
                    color: theme.surfaceSubtle
                    border.width: 1
                    border.color: theme.border

                    Row {
                        anchors.centerIn: parent
                        spacing: 6
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: appController.connected ? theme.green
                                  : appController.detected ? theme.orange : theme.textTertiary
                        }
                        Text {
                            text: appController.connected ? "연결됨"
                                  : appController.detected ? "검색 중" : "대기 중"
                            color: theme.textSecondary
                            font.family: theme.fontText
                            font.pixelSize: theme.bodySize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: theme.space1 }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 96
                radius: theme.cardRadius
                color: theme.insetColor(theme.widgetInset, appController.widgetOpacity)
                border.width: 1
                border.color: theme.sectionBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 5
                    anchors.bottomMargin: 5
                    spacing: 0
                    BatteryRow { Layout.fillWidth: true; Layout.preferredHeight: 24; label: "L"; value: appController.leftBattery; charging: appController.leftCharging; inEar: appController.leftInEar; alertThreshold: appController.batteryThreshold; theme: window.theme }
                    BatteryRow { Layout.fillWidth: true; Layout.preferredHeight: 24; label: "R"; value: appController.rightBattery; charging: appController.rightCharging; inEar: appController.rightInEar; alertThreshold: appController.batteryThreshold; theme: window.theme }
                    UsageEstimate { Layout.fillWidth: true; Layout.preferredHeight: 16; theme: window.theme; value: appController.estimatedRemainingUsage }
                    BatteryRow { Layout.fillWidth: true; Layout.preferredHeight: 24; label: "CASE"; value: appController.caseBattery; charging: appController.caseCharging; alertThreshold: appController.batteryThreshold; theme: window.theme }
                }
            }

            Item { Layout.preferredHeight: theme.space1 }

            AudioOutputSection {
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                theme: window.theme
                materialOpacity: appController.widgetOpacity
            }

            Item { Layout.preferredHeight: appController.mediaAvailable ? theme.space1 : 0 }

            MediaSection {
                Layout.fillWidth: true
                Layout.preferredHeight: appController.mediaAvailable ? 150 : 0
                Layout.alignment: Qt.AlignTop
                available: appController.mediaAvailable
                playing: appController.mediaPlaying
                title: appController.mediaTitle
                subtitle: appController.mediaSubtitle
                canPrevious: appController.canPrevious
                canNext: appController.canNext
                canPlayPause: appController.canPlayPause
                positionSeconds: appController.mediaPosition
                durationSeconds: appController.mediaDuration
                theme: window.theme
                materialOpacity: appController.widgetOpacity
            }

            Item { Layout.fillHeight: true }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: theme.border
            }

            Item { Layout.preferredHeight: theme.space1 }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 19
                    color: widgetMouse.containsMouse ? theme.hover : theme.surfaceSubtle
                    border.width: 1
                    border.color: theme.border
                    scale: widgetMouse.pressed ? 0.985 : 1
                    Behavior on scale { NumberAnimation { duration: theme.motionFast } }
                    Text {
                        anchors.centerIn: parent
                        text: appController.widgetVisible ? "위젯 숨기기" : "위젯 표시"
                        color: theme.textPrimary
                        font.family: theme.fontText
                        font.pixelSize: theme.labelSize
                        font.weight: theme.labelWeight
                    }
                    MouseArea { id: widgetMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: appController.toggleWidget() }
                }

                Rectangle {
                    Layout.preferredWidth: 76
                    Layout.preferredHeight: 38
                    radius: 19
                    color: settingsMouse.containsMouse ? theme.hover : theme.surfaceSubtle
                    border.width: 1
                    border.color: theme.border
                    Text { anchors.centerIn: parent; text: "설정"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight }
                    MouseArea { id: settingsMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { window.visible = false; appController.showSettings() } }
                }
            }
        }
    }
}
