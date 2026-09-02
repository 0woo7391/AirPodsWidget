import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property UiTheme theme
    property real materialOpacity: 1.0
    property bool mediaAvailable: false
    property bool devicePresent: true
    property bool playing: false
    property string title: ""
    property string subtitle: ""
    property bool canPrevious: false
    property bool canNext: false
    property bool canPlayPause: false
    property real positionSeconds: 0
    property real durationSeconds: 0
    // Compact mode uses the same shared timeline as the flow composition but
    // reveals its three logical groups in a shorter, denser sequence.
    property real revealProgress: 1.0
    property bool opening: false
    property real displayedPosition: positionSeconds
    property real clockPosition: positionSeconds
    property double clockTimestamp: Date.now()

    // These are the actual sums of the fixed groups below:
    // battery 32 + audio 72 + media 104 + two 9px gaps. Keeping the envelope
    // equal to the content prevents a fake empty band when media is absent.
    implicitHeight: root.mediaAvailable ? 226 : 113

    readonly property real batteryRevealProgress: smoothStep(0.12, 0.32, root.revealProgress)
    readonly property real audioRevealProgress: smoothStep(0.42, 0.62, root.revealProgress)
    readonly property real outputRevealProgress: smoothStep(0.54, 0.74, root.revealProgress)
    // The compact media strip is the last block in the stack. Delay it until
    // the expanding envelope can contain its full height; otherwise its top
    // edge appears first and the shell clips the controls during the morph.
    readonly property real mediaRevealProgress: smoothStep(0.90, 0.99, root.revealProgress)

    function smoothStep(edge0, edge1, value) {
        var normalized = Math.max(0, Math.min(1, (value - edge0) / (edge1 - edge0)))
        return normalized * normalized * (3 - 2 * normalized)
    }

    onPositionSecondsChanged: {
        if (!compactPlaybackSlider.pressed) {
            root.clockPosition = root.positionSeconds
            root.clockTimestamp = Date.now()
            root.displayedPosition = root.positionSeconds
        }
    }

    onPlayingChanged: {
        root.clockPosition = root.positionSeconds
        root.clockTimestamp = Date.now()
        root.displayedPosition = root.positionSeconds
    }

    Timer {
        id: compactPlaybackClock
        interval: 100
        repeat: true
        running: root.mediaAvailable && root.playing && !compactPlaybackSlider.pressed && root.durationSeconds > 0
        onTriggered: {
            root.displayedPosition = Math.min(
                root.durationSeconds,
                root.clockPosition + (Date.now() - root.clockTimestamp) / 1000
            )
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 9

        RowLayout {
            id: compactBatteryGroup
            objectName: "compactBatteryGroup"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.preferredHeight: 32
            spacing: 8
            opacity: root.batteryRevealProgress
            transform: Translate {
                y: (1 - root.batteryRevealProgress) * (root.theme ? root.theme.motionMorphSlide : 14)
            }

            Repeater {
                model: [
                    { label: "L", value: root.devicePresent ? appController.leftBattery : -1, inEar: root.devicePresent && appController.leftInEar, charging: root.devicePresent && appController.leftCharging },
                    { label: "R", value: root.devicePresent ? appController.rightBattery : -1, inEar: root.devicePresent && appController.rightInEar, charging: root.devicePresent && appController.rightCharging },
                    { label: "CASE", value: root.devicePresent ? appController.caseBattery : -1, inEar: false, charging: root.devicePresent && appController.caseCharging }
                ]

                delegate: Item {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    // The row must be allowed to compress while the parent
                    // window is between the minimized and expanded widths;
                    // a hard 70px minimum per column makes the last column
                    // intrude into the fixed morph toggle.
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 70

                    Row {
                        anchors.centerIn: parent
                        spacing: 5

                        Text {
                            text: modelData.label
                            color: root.theme.textTertiary
                            font.family: root.theme.fontText
                            font.pixelSize: root.theme.microSize
                            font.weight: root.theme.labelWeight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item {
                            width: 10
                            height: 16
                            visible: modelData.charging || (modelData.inEar && modelData.label !== "CASE")
                            anchors.verticalCenter: parent.verticalCenter

                            Rectangle {
                                anchors.centerIn: parent
                                width: 5
                                height: 5
                                radius: 3
                                color: root.theme.green
                                visible: modelData.inEar && !modelData.charging && modelData.label !== "CASE"
                            }

                            MediaIcon {
                                anchors.centerIn: parent
                                width: 11
                                height: 13
                                icon: "charging"
                                foreground: root.theme.yellow
                                visible: modelData.charging
                            }
                        }

                        Item {
                            width: 22
                            height: parent.height
                            anchors.verticalCenter: parent.verticalCenter

                            AnimatedNumber {
                                anchors.fill: parent
                                visible: modelData.value >= 0
                                value: modelData.value
                                suffix: ""
                                fontFamily: root.theme.fontDisplay
                                pixelSize: root.theme.captionSize
                                fontWeight: root.theme.valueWeight
                                revealOnAvailability: true
                                animationDuration: root.theme.motionStandard
                                horizontalAlignment: Text.AlignRight
                                verticalAlignment: Text.AlignVCenter
                                foreground: modelData.value >= 0 && modelData.value <= appController.batteryThreshold ? root.theme.red : root.theme.textPrimary
                            }

                            EmptyIndicator {
                                anchors.fill: parent
                                theme: root.theme
                                active: modelData.value < 0
                            }
                        }
                    }
                }
            }

            Item {
                Layout.preferredWidth: 54
                Layout.fillHeight: true

                AnimatedText {
                    anchors.fill: parent
                    text: root.devicePresent ? appController.estimatedRemainingUsage : ""
                    color: root.theme.textSecondary
                    fontFamily: root.theme.fontDisplay
                    pixelSize: root.theme.captionSize
                    fontWeight: root.theme.valueWeight
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                EmptyIndicator {
                    anchors.fill: parent
                    theme: root.theme
                    active: !root.devicePresent || appController.estimatedRemainingUsage === "—"
                }
            }
        }

        AudioOutputSection {
            id: compactAudioOutput
            objectName: "compactAudioOutput"
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            compact: true
            theme: root.theme
            materialOpacity: root.materialOpacity
            revealProgress: root.audioRevealProgress
            outputRevealProgress: root.outputRevealProgress
        }

        Rectangle {
            id: mediaStrip
            objectName: "compactMediaStrip"
            Layout.fillWidth: true
            Layout.preferredHeight: root.mediaAvailable ? 104 : 0
            visible: root.mediaAvailable
            opacity: root.mediaAvailable ? root.mediaRevealProgress : 0
            transform: Translate {
                y: (1 - root.mediaRevealProgress) * (root.theme ? root.theme.motionMorphSlide : 14)
            }
            radius: 14
            color: root.theme.surfaceRaised
            border.width: 1
            border.color: root.theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 5
                anchors.bottomMargin: 6
                spacing: 4

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 37
                    spacing: 3

                    MarqueeText {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 20
                        text: root.title
                        color: root.theme.textPrimary
                        fontFamily: root.theme.fontDisplay
                        pixelSize: root.theme.captionSize + 1
                        fontWeight: root.theme.titleWeight
                        running: root.playing
                    }

                    AnimatedText {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 14
                        text: root.subtitle
                        color: root.theme.textSecondary
                        fontFamily: root.theme.fontText
                        pixelSize: root.theme.microSize + 1
                        elide: Text.ElideRight
                        changeDuration: 130
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 14
                    spacing: 6

                    Item {
                        Layout.preferredWidth: 32
                        Layout.fillHeight: true

                        Text {
                            anchors.fill: parent
                            visible: root.durationSeconds > 0
                            text: root.formatTime(root.displayedPosition)
                            color: root.theme.textTertiary
                            font.family: root.theme.fontDisplay
                            font.pixelSize: root.theme.microSize
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        EmptyIndicator {
                            anchors.fill: parent
                            theme: root.theme
                            active: root.durationSeconds <= 0
                        }
                    }

                    AppleSlider {
                        id: compactPlaybackSlider
                        Layout.fillWidth: true
                        Layout.preferredHeight: 14
                        theme: root.theme
                        from: 0
                        to: Math.max(1, root.durationSeconds)
                        value: Math.max(0, Math.min(to, root.displayedPosition))
                        enabled: appController.mediaSeekable
                        smoothExternalChanges: false
                        progressColor: root.theme.textPrimary
                        trackColor: root.theme.track
                        onMoved: {
                            root.displayedPosition = value
                            root.clockPosition = value
                            root.clockTimestamp = Date.now()
                            appController.seekMedia(value)
                        }
                    }

                    Item {
                        Layout.preferredWidth: 32
                        Layout.fillHeight: true

                        Text {
                            anchors.fill: parent
                            visible: root.durationSeconds > 0
                            text: root.formatTime(root.durationSeconds)
                            color: root.theme.textTertiary
                            font.family: root.theme.fontDisplay
                            font.pixelSize: root.theme.microSize
                            horizontalAlignment: Text.AlignRight
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        EmptyIndicator {
                            anchors.fill: parent
                            theme: root.theme
                            active: root.durationSeconds <= 0
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    spacing: 6

                    Item { Layout.fillWidth: true }
                    SoftButton { theme: root.theme; iconName: "previous"; enabled: root.canPrevious; implicitWidth: 28; implicitHeight: 28; onClicked: appController.previousTrack() }
                    SoftButton { theme: root.theme; iconName: root.playing ? "pause" : "play"; primary: true; enabled: root.canPlayPause; implicitWidth: 34; implicitHeight: 34; onClicked: appController.togglePlayPause() }
                    SoftButton { theme: root.theme; iconName: "next"; enabled: root.canNext; implicitWidth: 28; implicitHeight: 28; onClicked: appController.nextTrack() }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0 && root.durationSeconds <= 0)
            return ""
        var total = Math.max(0, Math.floor(seconds))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var remainder = total % 60
        function pad(value) { return value < 10 ? "0" + value : value }
        return hours > 0
            ? hours + ":" + pad(minutes) + ":" + pad(remainder)
            : minutes + ":" + pad(remainder)
    }
}
