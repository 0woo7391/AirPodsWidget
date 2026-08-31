import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property bool available: false
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

    implicitHeight: available ? 150 : 0
    height: implicitHeight
    opacity: available ? 1 : 0
    visible: height > 1

    Behavior on height {
        NumberAnimation { duration: root.theme.motionLayout; easing.type: Easing.OutCubic }
    }
    Behavior on opacity {
        NumberAnimation { duration: root.theme.motionStandard; easing.type: Easing.OutCubic }
    }

    // Windows timeline updates are not guaranteed to arrive every second.
    // The local clock keeps the display responsive while playback is active.
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
        radius: root.theme.cardRadius
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.00; color: root.theme.glassCardTop(root.materialOpacity) }
            GradientStop { position: 1.00; color: root.theme.glassCardBottom(root.materialOpacity) }
        }
        border.width: 1
        border.color: root.theme.sectionBorder
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 12
        anchors.bottomMargin: 10
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 40

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 7

                MarqueeText {
                    width: parent.width
                    height: 21
                    text: root.title
                    color: root.theme.textPrimary
                    fontFamily: root.theme.fontDisplay
                    pixelSize: root.theme.bodySize + 1
                    fontWeight: root.theme.titleWeight
                    running: root.playing
                }

                Text {
                    width: parent.width
                    height: 15
                    text: root.subtitle
                    color: root.theme.textSecondary
                    font.family: root.theme.fontText
                    font.pixelSize: root.theme.captionSize
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 35
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 15

                Text {
                    text: root.formatTime(root.displayedPosition)
                    color: root.theme.textSecondary
                    font.family: root.theme.fontDisplay
                    font.pixelSize: root.theme.captionSize
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.formatTime(root.durationSeconds)
                    color: root.theme.textSecondary
                    font.family: root.theme.fontDisplay
                    font.pixelSize: root.theme.captionSize
                }
            }

            AppleSlider {
                id: playbackSlider
                Layout.fillWidth: true
                Layout.preferredHeight: 18
                theme: root.theme
                from: 0
                to: Math.max(1, root.durationSeconds)
                value: Math.max(0, Math.min(to, root.displayedPosition))
                enabled: appController.mediaSeekable
                opacity: root.durationSeconds > 0 ? (enabled ? 1 : 0.5) : 0.35
                smoothExternalChanges: false
                progressColor: root.theme.dark ? "#EDEDED" : "#1B1B1B"
                trackColor: root.theme.dark ? "#3A3A3A" : "#B2B2B2"
                onMoved: {
                    root.displayedPosition = value
                    root.clockPosition = value
                    root.clockTimestamp = Date.now()
                    appController.seekMedia(value)
                }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            spacing: 13

            Item { Layout.fillWidth: true }

            SoftButton {
                theme: root.theme
                iconName: "previous"
                enabled: root.canPrevious
                implicitWidth: 38
                implicitHeight: 38
                onClicked: appController.previousTrack()
            }

            SoftButton {
                theme: root.theme
                iconName: root.playing ? "pause" : "play"
                primary: true
                enabled: root.canPlayPause
                implicitWidth: 46
                implicitHeight: 46
                onClicked: appController.togglePlayPause()
            }

            SoftButton {
                theme: root.theme
                iconName: "next"
                enabled: root.canNext
                implicitWidth: 38
                implicitHeight: 38
                onClicked: appController.nextTrack()
            }

            Item { Layout.fillWidth: true }
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0 && appController.mediaDuration <= 0)
            return "—"
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
