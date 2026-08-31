import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property UiTheme theme
    property real materialOpacity: 1.0
    property int requestedVolume: Math.max(0, appController.audioVolume)
    property bool volumeDragging: false

    Connections {
        target: appController
        function onAudioChanged() {
            if (!root.volumeDragging)
                root.requestedVolume = Math.max(0, appController.audioVolume)
        }
    }

    Timer {
        id: volumeCommit
        interval: 55
        repeat: false
        onTriggered: appController.setAudioVolume(root.requestedVolume)
    }

    // The volume row and output selector are two different controls. Their
    // surfaces are intentionally different so the selector reads as one
    // segmented control instead of another large card.
    implicitHeight: 88
    height: implicitHeight

    Rectangle {
        id: volumePanel
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 48
        radius: root.theme.cardRadius
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.00; color: root.theme.glassCardTop(root.materialOpacity) }
            GradientStop { position: 1.00; color: root.theme.glassCardBottom(root.materialOpacity) }
        }
        border.width: 1
        border.color: root.theme.sectionBorder

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 8

            Item {
                Layout.preferredWidth: 20
                Layout.fillHeight: true
                MediaIcon {
                    anchors.centerIn: parent
                    width: 15
                    height: 15
                    icon: "volume"
                    foreground: root.theme.textSecondary
                    opacity: appController.audioVolumeAvailable ? 1 : 0.35
                }
            }

            AppleSlider {
                id: volumeSlider
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                from: 0
                to: 100
                stepSize: 1
                value: root.volumeDragging
                       ? root.requestedVolume : Math.max(0, appController.audioVolume)
                enabled: appController.audioVolumeAvailable
                smoothExternalChanges: true
                progressColor: root.theme.accent
                onMoved: {
                    root.volumeDragging = true
                    root.requestedVolume = Math.round(value)
                    volumeCommit.restart()
                }
                onPressedChanged: {
                    if (!pressed && root.volumeDragging) {
                        volumeCommit.stop()
                        appController.setAudioVolume(root.requestedVolume)
                        root.volumeDragging = false
                    }
                }
            }

            AnimatedNumber {
                Layout.preferredWidth: 38
                Layout.fillHeight: true
                value: appController.audioVolumeAvailable ? root.requestedVolume : -1
                fontFamily: root.theme.fontDisplay
                pixelSize: root.theme.labelSize
                fontWeight: root.theme.valueWeight
                revealOnAvailability: false
                foreground: root.theme.textSecondary
                animationDuration: root.theme.motionFast
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Rectangle {
        id: outputPanel
        objectName: "outputPanel"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 32
        radius: 16
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.00; color: root.theme.glassInsetTop(root.materialOpacity) }
            GradientStop { position: 1.00; color: root.theme.glassInsetBottom(root.materialOpacity) }
        }
        border.width: 1
        border.color: root.theme.border

        property int selectedIndex: {
            for (var i = 0; i < appController.audioOutputButtons.length; ++i) {
                if (appController.audioOutputButtons[i].current)
                    return i
            }
            return -1
        }

        // One shared indicator moves between fixed button slots. This is the
        // tabs-sliding interaction; the labels never jump when the device
        // changes.
        Rectangle {
            id: selectedIndicator
            objectName: "outputActiveIndicator"
            visible: outputPanel.selectedIndex >= 0
            x: 6 + Math.max(0, outputPanel.selectedIndex) * 94
            y: 3
            width: 88
            height: 26
            radius: 13
            color: root.theme.accentSoft
            border.width: 1
            border.color: root.theme.accent
            z: 0

            Behavior on x {
                NumberAnimation { duration: root.theme.motionStandard; easing.type: Easing.OutCubic }
            }
            Behavior on color { ColorAnimation { duration: root.theme.motionStandard } }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            spacing: 6

            Repeater {
                model: appController.audioOutputButtons

                delegate: OutputDeviceButton {
                    required property var modelData
                    Layout.preferredWidth: modelData.deviceId !== "" ? 88 : 0
                    Layout.preferredHeight: 26
                    z: 1
                    visible: modelData.deviceId !== ""
                    theme: root.theme
                    kind: modelData.kind
                    deviceName: modelData.name
                    available: modelData.available
                    current: modelData.current
                    onClicked: appController.selectAudioOutput(modelData.deviceId)
                }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
