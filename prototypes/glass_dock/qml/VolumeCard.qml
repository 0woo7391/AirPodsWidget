import QtQuick

// Output volume and every app's own level, in one module.
// Card: a speaker whose waves follow the volume, a rolling number and the volume slider
// with a ruler on top (the tens near the knob labelled when there is room). Flyout: a
// bigger ruler slider for the master volume and the apps making sound, each with a
// slider, mute and reset (Windows remembers app levels).
DockCard {
    id: card
    cardId: "volume"
    summaryHeight: 84

    readonly property var audio: outputBackend.state
    readonly property int volume: audio.available ? audio.volume : 0
    readonly property var apps: audioExtras.sessions || []
    readonly property var shownApps: apps.slice(0, 5)
    detailHeight: 176 + (apps.length ? 30 + shownApps.length * 44 : 40)
    function icon(app) { return "image://exeicon/" + encodeURIComponent(app.path) }
    function setVolume(value) { outputBackend.setVolume(Math.max(0, Math.min(100, value))) }

    railIcon: "speaker"
    railPose: audio.muted ? "muted" : ""
    railLabel: "볼륨"
    railStatus: !audio.available ? "—" : audio.muted ? "음소거" : volume + ""
    railDot: audio.muted ? Theme.warn : "transparent"

    summary: Component {
        Item {
            readonly property bool wide: card.size === "full"
            SpeakerGlyph {
                x: Theme.pad; y: 13; size: 18
                volume: card.volume; muted: card.audio.muted; level: audioMeter.level
                color: card.audio.muted ? Theme.warn : Theme.inkSecondary
            }
            RollingNumber {
                x: Theme.pad; y: 34
                visible: card.audio.available
                value: card.volume
                pixelSize: parent.wide ? 24 : 22
                color: card.audio.muted ? Theme.inkSecondary : Theme.ink
            }
            Text {
                x: Theme.pad; y: 34
                visible: !card.audio.available
                text: "—"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 22; font.weight: Font.DemiBold
            }
            RulerSlider {
                // Wide: beside the number with room for labels; half: along the bottom.
                x: parent.wide ? 86 : Theme.pad
                y: parent.height - Theme.pad - height + 4
                width: parent.width - x - Theme.pad
                height: parent.wide ? 40 : 26
                trackHeight: parent.wide ? 6 : 4
                knobSize: parent.wide ? 14 : 12
                value: card.volume
                enabled: card.audio.available
                onMoved: function(value) { card.setVolume(value) }
            }
        }
    }

    detail: Component {
        Item {
            Row {
                x: Theme.pad; y: Theme.pad; spacing: 8
                opacity: card.reveal(0)
                SpeakerGlyph {
                    size: 18; anchors.verticalCenter: parent.verticalCenter
                    volume: card.volume; muted: card.audio.muted; level: audioMeter.level
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "볼륨"
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                }
            }
            GlassButton {
                anchors.right: parent.right; anchors.rightMargin: Theme.pad; y: Theme.pad - 6
                opacity: (enabled ? 1 : 0.38) * card.reveal(0)
                text: card.audio.muted ? "음소거 해제" : "음소거"
                selected: card.audio.muted
                enabled: card.audio.available
                onClicked: outputBackend.toggleMute()
            }
            // Master volume: a big rolling number over the dial.
            RollingNumber {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 50
                opacity: card.reveal(1)
                value: card.volume
                pixelSize: 34
                color: card.audio.muted ? Theme.inkSecondary : Theme.ink
            }
            RulerSlider {
                x: Theme.pad + 4; y: 106; width: parent.width - Theme.pad * 2 - 8; height: 44
                trackHeight: 8; knobSize: 20
                opacity: card.reveal(1)
                value: card.volume
                enabled: card.audio.available
                onMoved: function(value) { card.setVolume(value) }
            }
            // Apps.
            Item {
                x: Theme.pad; y: 166; width: parent.width - Theme.pad * 2; height: 24
                opacity: card.reveal(2)
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: card.apps.length ? "앱별 볼륨" : "소리를 내는 앱이 생기면 여기에서 따로 조절할 수 있습니다."
                    width: parent.width; wrapMode: Text.Wrap
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                }
                Text {
                    visible: card.apps.length > 0
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    text: "모두 초기화"
                    color: resetAll.containsMouse ? Theme.ink : Theme.inkSecondary
                    font.family: dockFont; font.pixelSize: 11; font.underline: resetAll.containsMouse
                    MouseArea { id: resetAll; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true; onClicked: audioExtras.resetAllApps() }
                }
            }
            Column {
                x: Theme.pad; y: 196; width: parent.width - Theme.pad * 2; spacing: 2
                Repeater {
                    model: card.shownApps
                    Item {
                        id: appRow
                        required property var modelData
                        required property int index
                        readonly property bool changed: modelData.volume !== 100 || modelData.muted
                        width: parent.width; height: 42
                        opacity: card.reveal(3 + index); transform: Translate { y: 8 * (1 - card.reveal(3 + index)) }
                        Image {
                            width: 20; height: 20; sourceSize: Qt.size(40, 40)
                            anchors.verticalCenter: parent.verticalCenter
                            source: card.icon(appRow.modelData)
                            opacity: appRow.modelData.muted ? 0.45 : 1
                        }
                        // Playing apps get a small live dot.
                        Rectangle {
                            visible: appRow.modelData.active && !appRow.modelData.muted
                            x: 16; y: 8; width: 7; height: 7; radius: 3.5
                            color: Theme.good
                            border.width: 1.5; border.color: "#1C1C22"
                            scale: 0.85 + 0.3 * Math.min(1, audioMeter.level * 1.5)
                        }
                        Text {
                            x: 30; y: 2; width: parent.width - x - 120; elide: Text.ElideRight
                            text: appRow.modelData.name
                            color: appRow.modelData.active ? Theme.ink : Theme.inkSecondary
                            font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                        }
                        Text {
                            anchors.right: muteButton.left; anchors.rightMargin: 6; y: 2
                            text: appRow.modelData.muted ? "음소거" : appRow.modelData.volume
                            color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 10
                            font.features: Theme.numberFeatures
                        }
                        GlassSlider {
                            x: 30; y: 18; width: parent.width - x - 76; height: 20
                            value: appRow.modelData.volume
                            opacity: appRow.modelData.muted ? 0.4 : 1
                            onMoved: function(value) { audioExtras.setAppVolume(appRow.modelData.key, value) }
                        }
                        GlassButton {
                            id: muteButton
                            anchors.right: resetButton.left; anchors.rightMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            width: 28; height: 28
                            icon: "speaker"; pose: appRow.modelData.muted ? "muted" : ""; iconSize: 12
                            selected: appRow.modelData.muted
                            onClicked: audioExtras.toggleAppMute(appRow.modelData.key)
                        }
                        // Back to 100 % and unmuted; only offered when the app was changed.
                        GlassButton {
                            id: resetButton
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            width: 28; height: 28
                            text: "↺"
                            enabled: appRow.changed
                            onClicked: audioExtras.resetApp(appRow.modelData.key)
                        }
                    }
                }
            }
        }
    }
}
