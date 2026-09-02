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
    height: appController.mediaAvailable ? 476 : 322
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
        id: shell
        anchors.fill: parent
        anchors.margins: 8
        radius: theme.shellRadius
        // The tray is a transient control surface. Keep it opaque so the
        // desktop wallpaper cannot reduce contrast behind live controls.
        color: theme.popoverSurface
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
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            anchors.topMargin: 15
            spacing: 8

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 38

                AnimatedText {
                    anchors.left: parent.left
                    anchors.right: statusGroup.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: appController.deviceAvailable && appController.deviceName
                          ? appController.deviceName : ""
                    color: theme.textPrimary
                    fontFamily: theme.fontDisplay
                    pixelSize: theme.titleSize
                    fontWeight: theme.titleWeight
                    elide: Text.ElideRight
                    changeDuration: 190

                    EmptyIndicator {
                        anchors.fill: parent
                        theme: window.theme
                        active: !appController.deviceAvailable || !appController.deviceName
                    }
                }

                Row {
                    id: statusGroup
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Item {
                        width: 12
                        height: 16
                        anchors.verticalCenter: parent.verticalCenter

                        Rectangle {
                            anchors.centerIn: parent
                            width: 6
                            height: 6
                            radius: 3
                            color: appController.connected ? theme.green
                                  : appController.detected ? theme.orange : theme.textTertiary
                            opacity: appController.deviceAvailable ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: theme.motionFast; easing.type: Easing.OutCubic } }
                        }

                        MediaIcon {
                            anchors.centerIn: parent
                            width: 12
                            height: 12
                            icon: "bluetooth"
                            foreground: theme.textTertiary
                            opacity: appController.deviceAvailable ? 0 : 0.72
                            Behavior on opacity { NumberAnimation { duration: theme.motionFast; easing.type: Easing.OutCubic } }
                        }
                    }

                    AnimatedText {
                        text: appController.connected ? "연결됨"
                              : appController.detected ? "검색 중" : "대기 중"
                        color: theme.textSecondary
                        fontFamily: theme.fontText
                        pixelSize: theme.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                        width: implicitWidth
                        changeDuration: 150
                        changeOffset: 0
                    }
                }
            }

            BatteryOverview {
                Layout.fillWidth: true
                Layout.preferredHeight: 104
                theme: window.theme
                materialOpacity: appController.widgetOpacity
                devicePresent: appController.deviceAvailable
            }

            AudioOutputSection {
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                theme: window.theme
                materialOpacity: appController.widgetOpacity
            }

            MediaSection {
                Layout.fillWidth: true
                Layout.preferredHeight: appController.mediaAvailable ? 146 : 0
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

            Item { Layout.preferredHeight: 1 }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    radius: 10
                    color: widgetMouse.containsMouse ? theme.hover : theme.surfaceSubtle
                    border.width: 1
                    border.color: theme.border
                    scale: widgetMouse.pressed ? 0.985 : 1

                    AnimatedText {
                        anchors.centerIn: parent
                        text: appController.widgetVisible ? "위젯 숨기기" : "위젯 표시"
                        color: theme.textPrimary
                        fontFamily: theme.fontText
                        pixelSize: theme.captionSize
                        fontWeight: theme.labelWeight
                        changeDuration: 140
                    }

                    MouseArea {
                        id: widgetMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: appController.toggleWidget()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 72
                    Layout.preferredHeight: 36
                    radius: 10
                    color: settingsMouse.containsMouse ? theme.hover : theme.surfaceSubtle
                    border.width: 1
                    border.color: theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "설정"
                        color: theme.textPrimary
                        font.family: theme.fontText
                        font.pixelSize: theme.captionSize
                        font.weight: theme.labelWeight
                    }

                    MouseArea {
                        id: settingsMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            window.visible = false
                            appController.showSettings()
                        }
                    }
                }
            }
        }
    }
}
