import QtQuick

DockCard {
    id: card
    cardId: "output"
    summaryHeight: 84
    readonly property var audio: outputBackend.state
    readonly property var devices: outputBackend.devices || []
    detailHeight: 52 + Math.max(1, devices.length) * 40 + Theme.pad - 4

    railIcon: kindIcon(audio.kind)
    railLabel: "출력"
    railStatus: shortName(audio.name)

    function kindIcon(kind) { return kind === "headphones" ? "headphones" : "speaker" }
    function shortName(name) {
        const inner = /\(([^)]+)\)/.exec(name || "")
        return inner ? inner[1] : (name || "출력 없음")
    }

    summary: Component {
        Item {
            DockIcon { x: Theme.pad; y: 14; size: 16; name: card.kindIcon(card.audio.kind); color: Theme.inkSecondary }
            Text {
                x: Theme.pad; y: 36; width: parent.width - Theme.pad * 2
                text: card.shortName(card.audio.name)
                wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                lineHeight: 1.1
            }
        }
    }

    detail: Component {
        Item {
            Text {
                x: Theme.pad; y: Theme.pad; text: "출력 장치"
                opacity: card.reveal(0); transform: Translate { y: 8 * (1 - card.reveal(0)) }
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
            }
            Column {
                x: 6; y: 42; width: parent.width - 12; spacing: 4
                Repeater {
                    model: card.devices
                    Rectangle {
                        required property var modelData
                        required property int index
                        readonly property bool current: modelData.id === card.audio.currentId
                        width: parent.width; height: 36; radius: Theme.radiusInner
                        transform: Translate { y: 8 * (1 - card.reveal(1 + index)) }
                        color: current ? Theme.wellHover : row.containsMouse ? Theme.well : "transparent"
                        opacity: (modelData.available ? 1 : 0.4) * card.reveal(1 + index)
                        DockIcon {
                            x: 10; anchors.verticalCenter: parent.verticalCenter; size: 16
                            name: card.kindIcon(modelData.kind); color: current ? Theme.ink : Theme.inkSecondary
                        }
                        Text {
                            x: 36; width: parent.width - 36 - 30; anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name; elide: Text.ElideRight
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 12
                            font.weight: current ? Font.DemiBold : Font.Normal
                        }
                        Rectangle {
                            visible: current
                            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                            width: 7; height: 7; radius: 3.5; color: Theme.good
                        }
                        MouseArea {
                            id: row
                            anchors.fill: parent; hoverEnabled: true
                            enabled: modelData.available && !current && !card.audio.pendingId
                            onClicked: outputBackend.selectOutput(modelData.id)
                        }
                    }
                }
            }
        }
    }
}
