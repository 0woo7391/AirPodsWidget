import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window
    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"
    visible: false
    width: 480
    height: 700
    minimumWidth: 440
    minimumHeight: 600
    title: "AirPods Widget 설정"
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

    function reveal(targetX, targetY) {
        x = targetX
        y = targetY
        show()
        raise()
        requestActivate()
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 8
        radius: theme.shellRadius
        // Settings prioritizes legibility over the desktop material. The
        // widget opacity slider still affects only the widget background.
        color: theme.settingsSurface
        border.width: 1
        border.color: theme.settingsBorder
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 68

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: "설정"
                    color: theme.textPrimary
                    font.family: theme.fontDisplay
                    font.pixelSize: theme.titleSize + 2
                    font.weight: theme.titleWeight
                }

                Rectangle {
                    width: 34; height: 34; radius: 17
                    anchors.right: parent.right
                    anchors.rightMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    color: closeMouse.containsMouse ? theme.hover : "transparent"
                    Text { anchors.centerIn: parent; text: "×"; color: theme.textSecondary; font.pixelSize: 22 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.hide() }
                }

                MouseArea {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 60
                    cursorShape: Qt.SizeAllCursor
                    onPressed: window.startSystemMove()
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                ColumnLayout {
                    width: window.width - 56
                    x: 28
                    spacing: 12

                    Text { text: "위젯"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 306
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "바탕화면 위젯"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.widgetVisible; theme: window.theme; onToggled: function(value) { appController.setWidgetVisible(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "위치 잠금"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.widgetLocked; theme: window.theme; onToggled: function(value) { appController.setWidgetLocked(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "항상 위에 표시"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.widgetAlwaysOnTop; theme: window.theme; onToggled: function(value) { appController.setWidgetAlwaysOnTop(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "위젯 레이아웃"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                Rectangle {
                                    Layout.preferredWidth: 150
                                    Layout.preferredHeight: 32
                                    radius: 11
                                    color: theme.track

                                    Row {
                                        anchors.fill: parent
                                        anchors.margins: 3
                                        spacing: 3

                                        Repeater {
                                            model: [
                                                { label: "흐름형", value: "flow" },
                                                { label: "컴팩트", value: "compact" }
                                            ]

                                            delegate: Rectangle {
                                                required property var modelData
                                                width: 69
                                                height: 26
                                                radius: 8
                                                color: appController.widgetLayoutMode === modelData.value ? theme.settingsControl : "transparent"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: modelData.label
                                                    color: appController.widgetLayoutMode === modelData.value ? theme.textPrimary : theme.textSecondary
                                                    font.family: theme.fontText
                                                    font.pixelSize: theme.captionSize
                                                    font.weight: theme.labelWeight
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: appController.setWidgetLayoutMode(modelData.value)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "테마"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                Rectangle {
                                    Layout.preferredWidth: 124
                                    Layout.preferredHeight: 30
                                    radius: 10
                                    color: theme.track
                                    Row {
                                        anchors.fill: parent
                                        anchors.margins: 3
                                        spacing: 2
                                        Repeater {
                                            model: [{ label: "다크", value: "dark" }, { label: "라이트", value: "light" }]
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: 58
                                                height: 24
                                                radius: 8
                                                color: appController.theme === modelData.value ? theme.settingsControl : "transparent"
                                                Text { anchors.centerIn: parent; text: modelData.label; color: appController.theme === modelData.value ? theme.textPrimary : theme.textSecondary; font.family: theme.fontText; font.pixelSize: theme.microSize; font.weight: theme.labelWeight }
                                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appController.setTheme(modelData.value) }
                                            }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.preferredWidth: 76; text: "배경 투명도"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSlider {
                                    theme: window.theme
                                    id: opacitySlider
                                    Layout.fillWidth: true
                                    from: 0.55; to: 1; value: appController.widgetOpacity
                                    onMoved: appController.setWidgetOpacity(value)
                                }
                                AnimatedText { Layout.preferredWidth: 38; Layout.fillHeight: true; horizontalAlignment: Text.AlignRight; text: Math.round(opacitySlider.value * 100) + "%"; color: theme.textSecondary; fontFamily: theme.fontText; pixelSize: theme.captionSize; elide: Text.ElideRight; changeDuration: 90 }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.preferredWidth: 76; text: "크기"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSlider {
                                    theme: window.theme
                                    id: scaleSlider
                                    Layout.fillWidth: true
                                    from: 0.7; to: 1.5; value: appController.widgetScale
                                    onMoved: appController.setWidgetScale(value)
                                }
                                AnimatedText { Layout.preferredWidth: 38; Layout.fillHeight: true; horizontalAlignment: Text.AlignRight; text: Math.round(scaleSlider.value * 100) + "%"; color: theme.textSecondary; fontFamily: theme.fontText; pixelSize: theme.captionSize; elide: Text.ElideRight; changeDuration: 90 }
                            }
                        }
                    }

                    Text { text: "배터리 알림"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 214
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "저전력 알림"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.batteryAlertEnabled; theme: window.theme; onToggled: function(value) { appController.setBatteryAlertEnabled(value) } }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.preferredWidth: 76; text: "알림 기준"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSlider {
                                    theme: window.theme
                                    id: thresholdSlider
                                    Layout.fillWidth: true
                                    from: 10; to: 30; stepSize: 10; snapMode: Slider.SnapAlways
                                    value: appController.batteryThreshold
                                    onMoved: appController.setBatteryThreshold(Math.round(value))
                                }
                                AnimatedText { Layout.preferredWidth: 48; Layout.fillHeight: true; horizontalAlignment: Text.AlignRight; text: Math.round(thresholdSlider.value) + "% 이하"; color: theme.textSecondary; fontFamily: theme.fontText; pixelSize: theme.captionSize; elide: Text.ElideRight; changeDuration: 90 }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.preferredWidth: 76; text: "알림 볼륨"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSlider {
                                    theme: window.theme
                                    id: volumeSlider
                                    Layout.fillWidth: true
                                    from: 0; to: 100; stepSize: 1
                                    value: appController.alertVolume
                                    onMoved: appController.setAlertVolume(Math.round(value))
                                }
                                AnimatedText { Layout.preferredWidth: 38; Layout.fillHeight: true; horizontalAlignment: Text.AlignRight; text: Math.round(volumeSlider.value) + "%"; color: theme.textSecondary; fontFamily: theme.fontText; pixelSize: theme.captionSize; elide: Text.ElideRight; changeDuration: 90 }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                radius: 13
                                color: testMouse.containsMouse ? theme.hover : theme.settingsControl
                                border.width: 1
                                border.color: theme.settingsBorder
                                scale: testMouse.pressed ? 0.985 : 1
                                Behavior on scale { NumberAnimation { duration: 120 } }
                                AnimatedText {
                                    anchors.centerIn: parent
                                    text: appController.testPlaying ? "■  재생 중" : "▶  테스트 알림"
                                    color: theme.textPrimary
                                    fontFamily: theme.fontText
                                    pixelSize: theme.labelSize
                                    fontWeight: theme.labelWeight
                                    changeDuration: 130
                                }
                                MouseArea { id: testMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: appController.testAlert() }
                            }
                        }
                    }

                    Text { text: "미디어"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "플레이어 표시"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.mediaVisibleSetting; theme: window.theme; onToggled: function(value) { appController.setMediaVisible(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "미디어 없을 때도 표시"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.mediaAlwaysVisible; theme: window.theme; onToggled: function(value) { appController.setMediaAlwaysVisible(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "양쪽을 빼면 일시정지"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.autoPause; theme: window.theme; onToggled: function(value) { appController.setAutoPause(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "다시 착용하면 재생"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.autoResume; theme: window.theme; onToggled: function(value) { appController.setAutoResume(value) } }
                            }
                        }
                    }

                    Text { text: "출력 버튼"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 70 + appController.audioOutputButtons.length * 44
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 8

                            Repeater {
                                model: appController.audioOutputButtons

                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
                                        radius: 9
                                        color: modelData.available ? theme.accentSoft : theme.track
                                        MediaIcon {
                                            anchors.centerIn: parent
                                            width: 16
                                            height: 16
                                            icon: modelData.kind === "airpods" ? "bluetooth" : modelData.kind
                                            foreground: modelData.available ? theme.textSecondary : theme.textTertiary
                                        }
                                    }

                                    ComboBox {
                                        id: outputSelector
                                        Layout.fillWidth: true
                                        model: appController.audioOutputDevices
                                        textRole: "name"
                                        valueRole: "deviceId"
                                        currentIndex: {
                                            for (var i = 0; i < model.length; ++i) {
                                                if (model[i].deviceId === modelData.deviceId)
                                                    return i
                                            }
                                            return 0
                                        }
                                        onActivated: appController.setAudioOutputButton(modelData.index, currentValue)
                                    }

                                    Rectangle {
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
                                        radius: 9
                                        color: removeMouse.containsMouse ? theme.hover : "transparent"
                                        Text { anchors.centerIn: parent; text: "×"; color: theme.textSecondary; font.pixelSize: 18 }
                                        MouseArea {
                                            id: removeMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: appController.removeAudioOutputButton(modelData.index)
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 34
                                radius: 10
                                enabled: appController.audioOutputButtons.length < 3
                                opacity: enabled ? 1 : 0.42
                                color: addMouse.containsMouse && enabled ? theme.hover : "transparent"
                                border.width: 1
                                border.color: theme.border
                                Text {
                                    anchors.centerIn: parent
                                    text: parent.enabled ? "+  출력 버튼 추가" : "최대 3개"
                                    color: theme.textSecondary
                                    font.family: theme.fontText
                                    font.pixelSize: theme.captionSize
                                    font.weight: theme.labelWeight
                                }
                                MouseArea {
                                    id: addMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: parent.enabled
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: appController.addAudioOutputButton()
                                }
                            }
                        }
                    }

                    Text { text: "팝업"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "연결 팝업"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.connectionPopupEnabled; theme: window.theme; onToggled: function(value) { appController.setConnectionPopupEnabled(value) } }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: "게임 중 팝업 차단"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                                AppleSwitch { checked: appController.suppressPopupsDuringGames; theme: window.theme; onToggled: function(value) { appController.setSuppressPopupsDuringGames(value) } }
                            }
                        }
                    }

                    Text { text: "시스템"; color: theme.textTertiary; font.family: theme.fontText; font.pixelSize: theme.labelSize; font.weight: theme.labelWeight; font.letterSpacing: 0.6; leftPadding: 2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        radius: theme.cardRadius
                        color: theme.settingsPanel
                        border.width: 1
                        border.color: theme.settingsBorder
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            Text { Layout.fillWidth: true; text: "Windows 시작 시 실행"; color: theme.textPrimary; font.family: theme.fontText; font.pixelSize: theme.bodySize }
                            AppleSwitch { checked: appController.startWithWindows; theme: window.theme; onToggled: function(value) { appController.setStartWithWindows(value) } }
                        }
                    }
                    Item { Layout.preferredHeight: 24 }
                }
            }
        }
    }
}
