import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window

    // The widget is deliberately non-activating. It may remain visible above
    // the desktop, but it never takes focus from a foreground game or app.
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
           | ((appController.widgetAlwaysOnTop && !appController.gameActive)
              ? Qt.WindowStaysOnTopHint : Qt.WindowStaysOnBottomHint)
    color: "transparent"
    visible: appController.widgetVisible
    property real baseWidth: 360
    property real baseHeight: appController.mediaAvailable ? 464 : 302
    width: baseWidth * appController.widgetScale
    height: baseHeight * appController.widgetScale
    opacity: 1
    title: "AirPods Widget"
    property UiTheme theme: UiTheme {}
    property int materialInset: Math.round(8 * appController.widgetScale)
    property int materialCornerRadius: Math.round(theme.shellRadius * appController.widgetScale)

    onWidthChanged: appController.updateWindowShape(window)
    onHeightChanged: appController.updateWindowShape(window)

    Behavior on height {
        NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
    }
    Behavior on width {
        NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
    }

    Component.onCompleted: {
        appController.applyWindowMaterial(window)
        x = appController.widgetX
        y = appController.widgetY
        syncVisibility()
    }

    function syncVisibility() {
        if (appController.widgetVisible) {
            if (!window.visible)
                window.show()
        } else if (window.visible) {
            window.hide()
        }
    }

    function syncStacking() {
        var wasVisible = window.visible
        if (wasVisible) {
            window.hide()
            window.show()
        }
    }

    Connections {
        target: appController
        function onSettingsChanged() {
            appController.applyWindowMaterial(window)
            window.syncVisibility()
            window.syncStacking()
        }
        function onGameChanged() { window.syncStacking() }
    }

    onClosing: function(close) {
        close.accepted = false
        appController.setWidgetVisible(false)
    }

    Item {
        id: resizeHandle
        width: 22
        height: 22
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        z: 20
        visible: !appController.widgetLocked
        opacity: resizeMouse.containsMouse ? 0.9 : 0

        Behavior on opacity { NumberAnimation { duration: theme.motionFast } }

        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = theme.textTertiary
                ctx.lineWidth = 1.2
                ctx.lineCap = "round"
                ctx.beginPath()
                ctx.moveTo(8, 17); ctx.lineTo(17, 8)
                ctx.moveTo(13, 17); ctx.lineTo(17, 13)
                ctx.stroke()
            }
        }

        MouseArea {
            id: resizeMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.SizeFDiagCursor
            property real startGlobalX: 0
            property real startScale: 1

            onPressed: {
                var point = resizeHandle.mapToGlobal(mouse.x, mouse.y)
                startGlobalX = point.x
                startScale = appController.widgetScale
            }

            onPositionChanged: {
                if (!pressed)
                    return
                var point = resizeHandle.mapToGlobal(mouse.x, mouse.y)
                var nextScale = startScale + (point.x - startGlobalX) / window.baseWidth
                appController.setWidgetScale(Math.max(0.7, Math.min(1.5, nextScale)))
            }
        }
    }

    Item {
        id: scaledContent
        width: window.baseWidth
        height: window.baseHeight
        scale: appController.widgetScale
        transformOrigin: Item.TopLeft

        Behavior on height {
            NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
        }
        Behavior on scale {
            NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
        }

        Rectangle {
            id: card
            anchors.fill: parent
            anchors.margins: 8
            radius: theme.shellRadius
            color: "transparent"
            gradient: Gradient {
                GradientStop { position: 0.00; color: theme.glassShellTop(appController.widgetOpacity) }
                GradientStop { position: 0.46; color: theme.glassShellMid(appController.widgetOpacity) }
                GradientStop { position: 1.00; color: theme.glassShellBottom(appController.widgetOpacity) }
            }
            clip: true
            border.width: 1
            border.color: theme.border

            // One restrained optical edge is enough to describe the material;
            // the backdrop itself is supplied by Windows DWM when available.
            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.width: 1
                border.color: theme.innerBorder
            }

            MouseArea {
                id: cardHover
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.topMargin: 20
                anchors.bottomMargin: 16
                spacing: 0

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42

                    Column {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: appController.deviceName
                            color: theme.textPrimary
                            font.family: theme.fontDisplay
                            font.pixelSize: theme.titleSize
                            font.weight: theme.titleWeight
                            font.letterSpacing: -0.15
                            renderType: Text.NativeRendering
                        }
                    }

                    Row {
                        id: headerControls
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6

                        Rectangle {
                            id: statusPill
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
                                    width: 6
                                    height: 6
                                    radius: 3
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: appController.connected ? theme.green
                                          : appController.detected ? theme.orange : theme.textTertiary
                                    Behavior on color { ColorAnimation { duration: theme.motionStandard } }
                                }

                                Text {
                                    text: appController.connected ? "연결됨"
                                          : appController.detected ? "검색 중" : "대기 중"
                                    color: theme.textSecondary
                                    font.family: theme.fontText
                                    font.pixelSize: theme.bodySize
                                    font.weight: theme.bodyWeight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }

                        Rectangle {
                            id: menuButton
                            width: 28
                            height: 28
                            radius: 14
                            color: menuMouse.containsMouse ? theme.hover : "transparent"
                            border.width: menuMouse.containsMouse ? 1 : 0
                            border.color: theme.border
                            opacity: cardHover.containsMouse ? 1 : 0.72

                            Behavior on color { ColorAnimation { duration: theme.motionFast } }
                            Behavior on opacity { NumberAnimation { duration: theme.motionFast } }

                            Text {
                                anchors.centerIn: parent
                                text: "•••"
                                color: theme.textSecondary
                                font.family: theme.fontText
                                font.pixelSize: theme.captionSize
                                font.letterSpacing: 1
                            }

                            MouseArea {
                                id: menuMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: appController.showSettings()
                            }
                        }
                    }

                    MouseArea {
                        anchors.left: parent.left
                        anchors.right: headerControls.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        cursorShape: appController.widgetLocked ? Qt.ArrowCursor : Qt.SizeAllCursor
                        onPressed: if (!appController.widgetLocked) window.startSystemMove()
                        onReleased: appController.saveWidgetPosition(window.x, window.y)
                    }
                }

                Item { Layout.preferredHeight: theme.space2 }

                Rectangle {
                    id: batterySurface
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    radius: theme.cardRadius
                    color: "transparent"
                    gradient: Gradient {
                        GradientStop { position: 0.00; color: theme.glassInsetTop(appController.widgetOpacity) }
                        GradientStop { position: 1.00; color: theme.glassInsetBottom(appController.widgetOpacity) }
                    }
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

                Item { Layout.preferredHeight: theme.space2 }

                AudioOutputSection {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 88
                    theme: window.theme
                    materialOpacity: appController.widgetOpacity
                }

                Item { Layout.preferredHeight: appController.mediaAvailable ? theme.space2 : 0 }

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
            }
        }
    }
}
