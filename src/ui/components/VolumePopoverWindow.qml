import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: root

    property UiTheme theme
    property bool minimized: false
    property bool compactMode: false
    property bool available: false
    property int value: -1
    // Keep the parent binding on `value` intact. Interaction updates this
    // local value and emits it upward instead of assigning to the bound
    // property, which otherwise leaves the popup stuck on an old volume.
    property int displayedValue: Math.max(0, value)
    property bool dragging: false
    property bool opensBelow: true
    property int popupX: 0
    property int popupY: 0
    // Keep the volume surface transient to the widget so Windows places it
    // above the non-activating desktop window instead of behind it.
    property var ownerWindow: null
    signal valueMoved(int value)
    signal dragFinished()

    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
           | Qt.WindowStaysOnTopHint
    transientParent: ownerWindow
    color: "transparent"
    visible: false
    width: minimized ? 62 : compactMode ? 68 : 72
    height: minimized ? 86 : compactMode ? 118 : 148
    opacity: 0
    title: "AirPods volume"

    function openPopup() {
        if (visible) {
            openAnimation.restart()
            return
        }
        if (!dragging)
            displayedValue = Math.max(0, value)
        visible = true
        opacity = 0
        contentRoot.scale = 0.98
        // Window managers may reset a hidden Window's position on show; set
        // the screen position after making it visible as well.
        root.x = root.popupX
        root.y = root.popupY
        root.raise()
        openAnimation.restart()
    }

    function closePopup() {
        if (!visible)
            return
        openAnimation.stop()
        closeAnimation.restart()
    }

    onVisibleChanged: {
        if (visible) {
            root.x = root.popupX
            root.y = root.popupY
        }
    }

    ParallelAnimation {
        id: openAnimation
        NumberAnimation {
            target: root
            property: "opacity"
            from: 0
            to: 1
            duration: root.theme ? root.theme.motionMorphFade : 200
            easing.type: Easing.OutCubic
        }
            NumberAnimation {
                target: contentRoot
                property: "scale"
                from: 0.98
                to: 1
                duration: root.theme ? root.theme.motionStandard : 190
                easing.type: Easing.OutCubic
        }
    }

    SequentialAnimation {
        id: closeAnimation
        ParallelAnimation {
            NumberAnimation {
                target: root
                property: "opacity"
                to: 0
                duration: 120
                easing.type: Easing.InCubic
            }
            NumberAnimation {
                target: contentRoot
                property: "scale"
                to: 0.98
                duration: root.theme ? root.theme.motionFast : 140
                easing.type: Easing.InCubic
            }
        }
        ScriptAction { script: root.visible = false }
    }

    Item {
        id: contentRoot
        anchors.fill: parent
        transformOrigin: root.opensBelow ? Item.Top : Item.Bottom

            Rectangle {
                anchors.fill: parent
            radius: root.minimized ? 11 : root.compactMode ? 12 : 14
            color: root.theme ? root.theme.popoverSurface : "#202124"
            border.width: 1
            border.color: root.theme ? root.theme.border : "#40FFFFFF"

            Column {
                anchors.fill: parent
                anchors.margins: root.minimized ? 7 : root.compactMode ? 8 : 9
                spacing: root.minimized ? 4 : 5

                Item {
                    width: parent.width
                    height: root.minimized ? 16 : root.compactMode ? 18 : 20

                    AnimatedNumber {
                        anchors.fill: parent
                        visible: root.available
                        value: root.displayedValue
                        suffix: ""
                        fontFamily: root.theme ? root.theme.fontDisplay : "Segoe UI"
                        pixelSize: root.minimized ? 10 : root.compactMode ? 11 : 13
                        fontWeight: root.theme ? root.theme.valueWeight : Font.Medium
                        foreground: root.theme ? root.theme.textPrimary : "white"
                        revealOnAvailability: false
                        animationDuration: root.theme ? root.theme.motionFast : 140
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    EmptyIndicator {
                        anchors.fill: parent
                        theme: root.theme
                        active: !root.available
                    }
                }

                Item {
                    id: verticalRail
                    objectName: root.minimized ? "minimizedVerticalVolumeRail" : "verticalVolumeRail"
                    width: 30
                    height: root.minimized ? 48 : root.compactMode ? 76 : 102
                    anchors.horizontalCenter: parent.horizontalCenter

                    Rectangle {
                        objectName: root.minimized ? "minimizedVerticalVolumeTrack" : "verticalVolumeTrack"
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 2
                        width: 5
                        height: Math.max(12, parent.height - 4)
                        radius: width / 2
                        color: root.theme ? root.theme.track : "#555555"
                        opacity: root.available ? 1 : 0.45
                    }

                    AppleSlider {
                        id: verticalVolume
                        anchors.fill: parent
                        orientation: Qt.Vertical
                        theme: root.theme
                        background: Item {}
                        from: 0
                        to: 100
                        stepSize: 1
                        value: root.available ? root.displayedValue : 0
                        enabled: root.available
                        smoothExternalChanges: !root.dragging
                        progressColor: root.theme ? root.theme.textPrimary : "white"
                        trackColor: "transparent"
                        onMoved: {
                            root.dragging = true
                            root.displayedValue = Math.round(value)
                            root.valueMoved(root.displayedValue)
                        }
                        onPressedChanged: {
                            if (!pressed && root.dragging) {
                                root.dragging = false
                                root.dragFinished()
                            }
                        }
                    }

                    // The rail, not the 5px painted track, is the hit target.
                    // This makes a short minimized popup usable with a mouse
                    // while keeping the visual bar thin and quiet.
                    MouseArea {
                        id: volumePointer
                        objectName: root.minimized ? "minimizedVolumePointer" : "volumePointer"
                        anchors.fill: parent
                        z: 2
                        enabled: root.available
                        hoverEnabled: true
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        property bool tracking: false

                        function updateFromY(yPosition) {
                            var handle = verticalVolume.handleSize
                            var span = Math.max(1, verticalRail.height - handle)
                            var normalized = Math.max(0, Math.min(1,
                                (yPosition - handle / 2) / span))
                            var nextValue = verticalVolume.to
                                - normalized * (verticalVolume.to - verticalVolume.from)
                            root.dragging = true
                            root.displayedValue = Math.round(nextValue)
                            root.valueMoved(root.displayedValue)
                        }

                        onPressed: {
                            tracking = true
                            updateFromY(mouse.y)
                        }
                        onPositionChanged: {
                            if (tracking)
                                updateFromY(mouse.y)
                        }
                        onReleased: {
                            if (!tracking)
                                return
                            tracking = false
                            root.dragging = false
                            root.dragFinished()
                        }
                    }
                }
            }
        }
    }
}
