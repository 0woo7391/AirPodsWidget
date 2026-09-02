import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property bool available: false
    property bool persistent: false
    property bool playing: false
    property string title: ""
    property string subtitle: ""
    property bool canPrevious: false
    property bool canNext: false
    property bool canPlayPause: false
    property real positionSeconds: 0
    property real durationSeconds: 0
    property real displayedPosition: positionSeconds
    property real clockPosition: positionSeconds
    property double clockTimestamp: Date.now()
    property UiTheme theme
    property real materialOpacity: 1.0
    // Media enters last in the expanded composition. Its height remains owned
    // by the frozen parent layout; only the visual reveal is animated here.
    property real revealProgress: 1.0

    readonly property bool slotVisible: available || persistent

    implicitHeight: slotVisible ? 146 : 0
    height: implicitHeight
    opacity: slotVisible ? root.revealProgress : 0
    visible: height > 1
    transform: Translate {
        y: (1 - root.revealProgress) * (root.theme ? root.theme.motionMorphSlide : 14)
    }

    onPositionSecondsChanged: {
        if (!playbackSlider.pressed) {
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
        id: playbackClock
        interval: 100
        repeat: true
        running: root.available && root.playing && !playbackSlider.pressed && root.durationSeconds > 0
        onTriggered: {
            root.displayedPosition = Math.min(
                root.durationSeconds,
                root.clockPosition + (Date.now() - root.clockTimestamp) / 1000
            )
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.theme.cardRadius + 2
        color: root.theme.surfaceRaised
        border.width: 1
        border.color: root.theme.border
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 15
        anchors.rightMargin: 15
        anchors.topMargin: 10
        anchors.bottomMargin: 8
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 13
            spacing: 6

            Rectangle {
                Layout.preferredWidth: 4
                Layout.preferredHeight: 4
                radius: 2
                color: root.theme.accent
                opacity: root.available ? 1 : 0.55
            }

            Text {
                text: root.available ? "NOW PLAYING" : "PLAYER"
                color: root.theme.textTertiary
                font.family: root.theme.fontText
                font.pixelSize: root.theme.microSize
                font.weight: root.theme.labelWeight
                font.letterSpacing: 1.1
            }

            Item { Layout.fillWidth: true }
        }

        MarqueeText {
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            text: root.title
            color: root.theme.textPrimary
            fontFamily: root.theme.fontDisplay
            pixelSize: root.theme.bodySize + 1
            fontWeight: root.theme.titleWeight
            running: root.playing

            EmptyIndicator {
                anchors.fill: parent
                theme: root.theme
                active: !root.available
            }
        }

        AnimatedText {
            Layout.fillWidth: true
            Layout.preferredHeight: 16
            text: root.subtitle
            color: root.theme.textSecondary
            fontFamily: root.theme.fontText
            pixelSize: root.theme.captionSize
            elide: Text.ElideRight
            changeDuration: 130
        }

        // A small title/subtitle separation keeps the two readings distinct;
        // the larger player gaps belong between groups, not inside the text.
        Item { Layout.preferredHeight: 3 }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 13

            Item {
                Layout.preferredWidth: 38
                Layout.fillHeight: true

                Text {
                    anchors.fill: parent
                    text: root.formatTime(root.displayedPosition)
                    color: root.theme.textTertiary
                    font.family: root.theme.fontDisplay
                    font.pixelSize: root.theme.microSize
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }

                EmptyIndicator {
                    anchors.fill: parent
                    theme: root.theme
                    active: root.durationSeconds <= 0
                }
            }

            Item { Layout.fillWidth: true }

            Item {
                Layout.preferredWidth: 38
                Layout.fillHeight: true

                Text {
                    anchors.fill: parent
                    text: root.formatTime(root.durationSeconds)
                    color: root.theme.textTertiary
                    font.family: root.theme.fontDisplay
                    font.pixelSize: root.theme.microSize
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }

                EmptyIndicator {
                    anchors.fill: parent
                    theme: root.theme
                    active: root.durationSeconds <= 0
                }
            }
        }

        AppleSlider {
            id: playbackSlider
            Layout.fillWidth: true
            Layout.preferredHeight: 16
            theme: root.theme
            from: 0
            to: Math.max(1, root.durationSeconds)
            value: Math.max(0, Math.min(to, root.displayedPosition))
            enabled: appController.mediaSeekable
            opacity: root.durationSeconds > 0 ? (enabled ? 1 : 0.45) : 0.3
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

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            spacing: 13

            Item { Layout.fillWidth: true }

            SoftButton {
                theme: root.theme
                iconName: "previous"
                enabled: root.canPrevious
                implicitWidth: 36
                implicitHeight: 36
                onClicked: appController.previousTrack()
            }

            SoftButton {
                theme: root.theme
                iconName: root.playing ? "pause" : "play"
                primary: true
                enabled: root.canPlayPause
                implicitWidth: 44
                implicitHeight: 44
                onClicked: appController.togglePlayPause()
            }

            SoftButton {
                theme: root.theme
                iconName: "next"
                enabled: root.canNext
                implicitWidth: 36
                implicitHeight: 36
                onClicked: appController.nextTrack()
            }

            Item { Layout.fillWidth: true }
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0 && appController.mediaDuration <= 0)
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
