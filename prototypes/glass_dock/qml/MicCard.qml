import QtQuick

// The default microphone: on or off at a glance, one click to switch.
DockCard {
    id: card
    cardId: "mic"
    expandable: false
    summaryHeight: 84

    readonly property var mic: audioExtras.mic
    readonly property bool muted: !!mic.muted
    readonly property color tone: !mic.available ? Theme.inkTertiary : muted ? Theme.bad : Theme.good

    railIcon: "microphone"
    railPose: muted ? "muted" : ""
    railLabel: "마이크"
    railStatus: !mic.available ? "없음" : muted ? "꺼짐" : "켜짐"
    railDot: mic.available && muted ? Theme.bad : "transparent"

    summary: Component {
        Item {
            DockIcon {
                x: Theme.pad; y: 14; size: 16
                name: "microphone"; pose: card.muted ? "muted" : ""
                color: card.muted ? Theme.bad : Theme.inkSecondary
            }
            Rectangle {
                x: parent.width - Theme.pad - 8; y: 18; width: 8; height: 8; radius: 4
                color: card.tone
            }
            Text {
                x: Theme.pad; y: 36
                text: !card.mic.available ? "없음" : card.muted ? "꺼짐" : "켜짐"
                color: !card.mic.available ? Theme.inkSecondary : card.muted ? Theme.bad : Theme.ink
                font.family: dockFont; font.pixelSize: 20; font.weight: Font.DemiBold
            }
            Text {
                x: Theme.pad; y: parent.height - Theme.pad - height + 2; width: parent.width - Theme.pad * 2
                text: card.mic.name || "기본 마이크"
                elide: Text.ElideRight
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 10
            }
            TapHandler {
                enabled: card.mic.available && !(card.dock && card.dock.editing)
                onTapped: audioExtras.toggleMic()
            }
            HoverHandler { cursorShape: card.mic.available ? Qt.PointingHandCursor : Qt.ArrowCursor }
        }
    }
}
