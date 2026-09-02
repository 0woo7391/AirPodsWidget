import QtQuick
import QtQuick.Controls
import QtQuick.Window

Item {
    id: root
    property UiTheme theme
    property real materialOpacity: 1.0
    property bool compact: false
    property bool minimized: false
    property int requestedVolume: Math.max(0, appController.audioVolume)
    property bool volumeDragging: false
    // The output group follows the widget's shared morph timeline. This is a
    // visual transform only; the button hit targets and popup anchor remain
    // in their fixed layout slots.
    property real revealProgress: 1.0
    property real outputRevealProgress: root.revealProgress
    readonly property bool volumePopupOpen: volumePopup.visible
    readonly property int outputSlotWidth: 86
    readonly property int outputSlotGap: 6

    implicitHeight: root.minimized ? 38 : 72
    height: implicitHeight
    // This component owns a fixed layout slot. The parent morph timeline
    // reveals its two groups below; moving the whole item as well created a
    // second translate and made the volume row and output buttons arrive at
    // different times.
    opacity: root.revealProgress

    function closeVolumePopupIfUnavailable() {
        volumePopup.closePopup()
    }

    function positionVolumePopup(anchorItem) {
        var target = anchorItem || volumeButton
        var anchor = target.mapToGlobal(target.width / 2, target.height / 2)
        var popupWidth = volumePopup.width
        var popupHeight = volumePopup.height
        var gap = 6
        var area = root.Window.window && root.Window.window.screen
                   ? root.Window.window.screen.availableGeometry
                   : null
        var workWidth = area && area.width > 0
                        ? area.width : (Screen.width > 0 ? Screen.width : 1920)
        var workHeight = area && area.height > 0
                         ? area.height : (Screen.height > 0 ? Screen.height : 1080)
        var areaX = area && area.width > 0 ? area.x : 0
        var areaY = area && area.height > 0 ? area.y : 0
        var areaRight = areaX + workWidth
        var areaBottom = areaY + workHeight
        var nextX = Math.max(areaX + 4, Math.min(areaRight - popupWidth - 4,
                                                   anchor.x - popupWidth / 2))
        var belowY = anchor.y + target.height / 2 + gap
        var aboveY = anchor.y - target.height / 2 - popupHeight - gap
        var belowFits = belowY + popupHeight <= areaBottom - 4
        var aboveFits = aboveY >= areaY + 4

        volumePopup.popupX = Math.round(nextX)
        volumePopup.opensBelow = belowFits || !aboveFits
        volumePopup.popupY = Math.round(volumePopup.opensBelow ? belowY : aboveY)
    }

    function toggleVolumePopup(anchorItem) {
        if (volumePopup.visible) {
            volumePopup.closePopup()
            return
        }
        positionVolumePopup(anchorItem)
        volumePopup.openPopup()
    }

    onCompactChanged: closeVolumePopupIfUnavailable()
    onMinimizedChanged: closeVolumePopupIfUnavailable()

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

    Rectangle {
        id: audioDivider
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: root.theme.border
        opacity: 0.42 * root.revealProgress
        visible: !root.minimized
    }

    Item {
        id: volumeRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: root.minimized ? parent.top : audioDivider.bottom
        height: 38

        Rectangle {
            id: volumeButton
            objectName: "volumeButton"
            width: root.minimized ? 56 : 34
            height: 34
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            radius: 10
            // Flow mode already exposes the full horizontal slider. Keep the
            // glyph as a visual cue there; only compact/minimized use it as a
            // volume popover trigger.
            visible: !root.compact || root.minimized
            color: root.compact || root.minimized
                   ? (volumeMouse.containsMouse ? root.theme.hover : root.theme.surfaceSubtle)
                   : "transparent"
            border.width: root.compact || root.minimized ? 1 : 0
            border.color: root.theme.border
            opacity: appController.audioVolumeAvailable ? 1 : 0.4
            scale: (root.compact || root.minimized) && volumeMouse.pressed ? 0.96 : 1

            MediaIcon {
                anchors.centerIn: parent
                width: 15
                height: 15
                icon: "volume"
                foreground: root.theme.textPrimary
                visible: !root.minimized
            }

            Row {
                visible: root.minimized
                anchors.centerIn: parent
                spacing: 4

                MediaIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 13
                    height: 13
                    icon: "volume"
                    foreground: root.theme.textPrimary
                }

                Item {
                    width: 22
                    height: 22

                    AnimatedNumber {
                        anchors.fill: parent
                        visible: appController.audioVolumeAvailable
                        value: root.requestedVolume
                        suffix: ""
                        fontFamily: root.theme.fontDisplay
                        pixelSize: 10
                        fontWeight: root.theme.valueWeight
                        revealOnAvailability: false
                        foreground: root.theme.textPrimary
                        animationDuration: root.theme.motionFast
                        verticalAlignment: Text.AlignVCenter
                    }

                    EmptyIndicator {
                        anchors.fill: parent
                        theme: root.theme
                        active: !appController.audioVolumeAvailable
                    }
                }
            }

            Behavior on color { ColorAnimation { duration: root.theme.motionFast; easing.type: Easing.OutCubic } }
            Behavior on scale { NumberAnimation { duration: root.theme.motionFast; easing.type: Easing.OutCubic } }

            MouseArea {
                id: volumeMouse
                anchors.fill: parent
                enabled: appController.audioVolumeAvailable && (root.compact || root.minimized)
                hoverEnabled: root.compact || root.minimized
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.toggleVolumePopup(volumeButton)
            }
        }

        AppleSlider {
            id: horizontalVolume
            visible: !root.compact && !root.minimized
            anchors.left: volumeButton.right
            anchors.leftMargin: 10
            anchors.right: volumeValueSlot.left
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            theme: root.theme
            from: 0
            to: 100
            stepSize: 1
            value: root.volumeDragging ? root.requestedVolume : Math.max(0, appController.audioVolume)
            enabled: appController.audioVolumeAvailable
            smoothExternalChanges: true
            progressColor: root.theme.textPrimary
            trackColor: root.theme.track
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

        Rectangle {
            id: compactVolumeButton
            objectName: "compactVolumeButton"
            visible: root.compact && !root.minimized
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 76
            height: 28
            radius: 9
            color: root.volumePopupOpen
                   ? root.theme.accentSoft
                   : (compactVolumeMouse.containsMouse ? root.theme.hover : "transparent")
            border.width: root.volumePopupOpen || compactVolumeMouse.containsMouse ? 1 : 0
            border.color: root.theme.border

            Row {
                anchors.centerIn: parent
                spacing: 5

                MediaIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 13
                    height: 13
                    icon: "volume"
                    foreground: root.theme.textPrimary
                }

                Item {
                    width: 24
                    height: 20

                    AnimatedNumber {
                        anchors.fill: parent
                        visible: appController.audioVolumeAvailable
                        value: root.requestedVolume
                        suffix: ""
                        fontFamily: root.theme.fontDisplay
                        pixelSize: root.theme.captionSize
                        fontWeight: root.theme.valueWeight
                        revealOnAvailability: false
                        foreground: root.theme.textPrimary
                        animationDuration: root.theme.motionFast
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    EmptyIndicator {
                        anchors.fill: parent
                        theme: root.theme
                        active: !appController.audioVolumeAvailable
                    }
                }
            }

            MouseArea {
                id: compactVolumeMouse
                anchors.fill: parent
                enabled: appController.audioVolumeAvailable
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.toggleVolumePopup(compactVolumeButton)
            }
        }

        Item {
            id: volumeValueSlot
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 42
            height: 28
            visible: !root.minimized && !root.compact

            AnimatedNumber {
                id: volumeValue
                anchors.fill: parent
                visible: appController.audioVolumeAvailable
                value: root.requestedVolume
                suffix: ""
                fontFamily: root.theme.fontDisplay
                pixelSize: root.theme.valueSize
                fontWeight: root.theme.valueWeight
                revealOnAvailability: false
                foreground: root.theme.textSecondary
                animationDuration: root.theme.motionFast
                verticalAlignment: Text.AlignVCenter
            }

            EmptyIndicator {
                anchors.fill: parent
                theme: root.theme
                active: !appController.audioVolumeAvailable
            }
        }

    }

    Rectangle {
        id: selectorDivider
        anchors.left: parent.left
        anchors.right: parent.right
        y: 40
        height: 1
        color: root.theme.border
        opacity: 0.26 * root.outputRevealProgress
        visible: !root.minimized
    }

    Item {
        id: outputPanel
        objectName: "outputPanel"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 31
        visible: !root.minimized
        opacity: root.outputRevealProgress
        transform: Translate {
            y: (1 - root.outputRevealProgress) * (root.theme ? root.theme.motionMorphSlide : 6)
        }

        property int selectedIndex: {
            for (var i = 0; i < appController.audioOutputButtons.length; ++i) {
                if (appController.audioOutputButtons[i].current)
                    return i
            }
            return -1
        }

        Row {
            id: outputButtonRow
            objectName: "outputButtonRow"
            anchors.left: root.compact ? undefined : parent.left
            anchors.horizontalCenter: root.compact ? parent.horizontalCenter : undefined
            anchors.verticalCenter: parent.verticalCenter
            spacing: root.outputSlotGap

            Repeater {
                model: appController.audioOutputButtons

                delegate: OutputDeviceButton {
                    required property var modelData
                    width: root.outputSlotWidth
                    height: 30
                    theme: root.theme
                    kind: modelData.kind
                    deviceName: modelData.name
                    available: modelData.available
                    loading: modelData.pending
                    current: modelData.current
                    onClicked: appController.selectAudioOutput(modelData.deviceId)
                }
            }
        }

        Rectangle {
            id: selectedIndicator
            objectName: "outputActiveIndicator"
            visible: outputPanel.selectedIndex >= 0
            x: outputPanel.selectedIndex < 0 ? 0
                : outputButtonRow.x
                  + outputPanel.selectedIndex * (root.outputSlotWidth + root.outputSlotGap) + 12
            y: parent.height - 2
            width: root.outputSlotWidth - 24
            height: 2
            radius: 1
            color: root.theme.accent

            Behavior on x {
                NumberAnimation { duration: root.theme.motionStandard; easing.type: Easing.OutCubic }
            }
            Behavior on color { ColorAnimation { duration: root.theme.motionStandard } }
        }
    }

    VolumePopoverWindow {
        id: volumePopup
        objectName: root.minimized ? "volumePopoverMinimized"
                    : root.compact ? "volumePopoverCompact" : "volumePopoverFlow"
        theme: root.theme
        ownerWindow: root.Window.window
        minimized: root.minimized
        compactMode: root.compact
        available: appController.audioVolumeAvailable
        value: root.requestedVolume
        onValueMoved: {
            root.volumeDragging = true
            root.requestedVolume = value
            volumeCommit.restart()
        }
        onDragFinished: {
            volumeCommit.stop()
            appController.setAudioVolume(root.requestedVolume)
            root.volumeDragging = false
        }
    }
}
