import QtQuick

// Per-app volume. Full: the apps making sound with their levels. Half: their icons.
// The flyout lists every app with a slider and a mute button.
DockCard {
    id: card
    cardId: "mixer"
    summaryHeight: 84

    readonly property var apps: audioExtras.sessions || []
    readonly property var playing: apps.filter(a => a.active)
    readonly property var shown: (playing.length ? playing : apps).slice(0, 3)
    detailHeight: 52 + Math.max(1, Math.min(6, apps.length)) * 44 + Theme.pad - 6

    function icon(app) { return "image://exeicon/" + encodeURIComponent(app.path) }

    railIcon: "sliders"
    railLabel: "앱별 볼륨"
    railStatus: playing.length ? playing.map(a => a.name).join(", ") : apps.length ? "재생 중인 앱 없음" : "앱 없음"
    railDot: playing.length ? Theme.good : "transparent"

    summary: Component {
        Item {
            readonly property bool wide: card.size === "full"
            DockIcon { x: Theme.pad; y: 14; size: 16; name: "sliders"; color: Theme.inkSecondary }
            Text {
                x: Theme.pad + 24; y: 13; height: 20
                visible: parent.wide
                text: "앱별 볼륨"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
            }
            Text {
                visible: card.shown.length === 0
                x: Theme.pad; y: 40
                text: "소리 나는 앱 없음"
                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 12
            }
            // Wide: one line per app with a level bar.
            Column {
                visible: parent.wide
                x: Theme.pad; y: 38; width: parent.width - Theme.pad * 2; spacing: 4
                Repeater {
                    model: parent.visible ? card.shown.slice(0, 2) : []
                    Row {
                        required property var modelData
                        spacing: 8
                        Image {
                            width: 16; height: 16; sourceSize: Qt.size(32, 32)
                            source: card.icon(modelData)
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: 70; elide: Text.ElideRight
                            text: modelData.name
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Meter {
                            width: card.width - Theme.pad * 2 - 70 - 16 - 16 - 36; height: 3
                            value: modelData.muted ? 0 : modelData.volume
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: 28; horizontalAlignment: Text.AlignRight
                            text: modelData.muted ? "—" : modelData.volume
                            color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 10
                            font.features: Theme.numberFeatures
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
            // Half: the apps' icons.
            Row {
                visible: !parent.wide
                x: Theme.pad; y: 40; spacing: 6
                Repeater {
                    model: parent.visible ? card.shown : []
                    Rectangle {
                        required property var modelData
                        width: 26; height: 26; radius: 8
                        color: Theme.well
                        opacity: modelData.muted ? 0.4 : 1
                        Image {
                            anchors.centerIn: parent
                            width: 18; height: 18; sourceSize: Qt.size(36, 36)
                            source: card.icon(modelData)
                        }
                    }
                }
            }
        }
    }

    detail: Component {
        Item {
            Text {
                x: Theme.pad; y: Theme.pad
                text: "앱별 볼륨"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Text {
                visible: card.apps.length === 0
                x: Theme.pad; y: 52; width: parent.width - Theme.pad * 2; wrapMode: Text.Wrap
                text: "소리를 내는 앱이 생기면 여기에서 따로 조절할 수 있습니다."
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
            }
            Column {
                x: Theme.pad; y: 46; width: parent.width - Theme.pad * 2; spacing: 2
                Repeater {
                    model: card.apps.slice(0, 6)
                    Item {
                        required property var modelData
                        required property int index
                        width: parent.width; height: 42
                        opacity: card.reveal(1 + index); transform: Translate { y: 8 * (1 - card.reveal(1 + index)) }
                        Image {
                            width: 20; height: 20; sourceSize: Qt.size(40, 40)
                            anchors.verticalCenter: parent.verticalCenter
                            source: card.icon(modelData)
                        }
                        Text {
                            x: 28; y: 2; width: 120; elide: Text.ElideRight
                            text: modelData.name
                            color: modelData.active ? Theme.ink : Theme.inkSecondary
                            font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                        }
                        GlassSlider {
                            x: 28; y: 18; width: parent.width - x - 44; height: 20
                            value: modelData.volume
                            opacity: modelData.muted ? 0.4 : 1
                            onMoved: function(value) { audioExtras.setAppVolume(modelData.key, value) }
                        }
                        GlassButton {
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            width: 30; height: 30
                            icon: "speaker"; pose: modelData.muted ? "muted" : ""; iconSize: 13
                            selected: modelData.muted
                            onClicked: audioExtras.toggleAppMute(modelData.key)
                        }
                    }
                }
            }
        }
    }
}
