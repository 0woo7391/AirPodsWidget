import QtQuick

DockCard {
    id: card
    cardId: "volume"
    summaryHeight: 84
    detailHeight: 124

    readonly property var audio: outputBackend.state
    readonly property int volume: audio.available ? audio.volume : 0

    railIcon: "speaker"
    railPose: audio.muted ? "muted" : ""
    railLabel: "볼륨"
    railStatus: !audio.available ? "—" : audio.muted ? "음소거" : volume + ""
    railDot: audio.muted ? Theme.warn : "transparent"

    summary: Component {
        Item {
            DockIcon {
                x: Theme.pad; y: 14; size: 16
                name: "speaker"; pose: card.audio.muted ? "muted" : ""
                color: card.audio.muted ? Theme.warn : Theme.inkSecondary
            }
            Text {
                x: Theme.pad; y: 36
                text: card.audio.available ? card.volume : "—"
                color: card.audio.muted ? Theme.inkSecondary : Theme.ink
                font.family: dockFont; font.pixelSize: 22; font.weight: Font.DemiBold
                font.features: Theme.numberFeatures
            }
            Meter { x: Theme.pad; y: parent.height - Theme.pad - 3; width: parent.width - Theme.pad * 2; height: 3; value: card.volume }
            WheelHandler {
                onWheel: function(event) {
                    outputBackend.setVolume(Math.max(0, Math.min(100, card.volume + (event.angleDelta.y > 0 ? 2 : -2))))
                }
            }
        }
    }

    detail: Component {
        Item {
            Text {
                x: Theme.pad; y: Theme.pad; text: "볼륨"
                opacity: card.reveal(0); transform: Translate { y: 8 * (1 - card.reveal(0)) }
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
            }
            Text {
                anchors.right: parent.right; anchors.rightMargin: Theme.pad; y: Theme.pad - 4
                opacity: card.reveal(0); transform: Translate { y: 8 * (1 - card.reveal(0)) }
                text: card.audio.available ? card.volume : "—"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 20; font.weight: Font.DemiBold
                font.features: Theme.numberFeatures
            }
            GlassButton {
                x: Theme.pad; y: 62
                opacity: (enabled ? 1 : 0.38) * card.reveal(1); transform: Translate { y: 8 * (1 - card.reveal(1)) }
                icon: "speaker"; pose: card.audio.muted ? "muted" : ""
                selected: card.audio.muted
                enabled: card.audio.available
                onClicked: outputBackend.toggleMute()
            }
            GlassSlider {
                x: Theme.pad + 48; y: 67; width: parent.width - x - Theme.pad - 4
                opacity: card.reveal(1); transform: Translate { y: 8 * (1 - card.reveal(1)) }
                value: card.volume
                enabled: card.audio.available
                onMoved: function(value) { outputBackend.setVolume(value) }
            }
        }
    }
}
