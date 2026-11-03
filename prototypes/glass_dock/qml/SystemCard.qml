import QtQuick

// CPU and memory load and the network's ping; the flyout shows them with bars.
DockCard {
    id: card
    cardId: "system"
    summaryHeight: 84
    detailHeight: 176

    readonly property var s: systemStatus.state
    function loadColor(value) { return value >= 90 ? Theme.bad : value >= 70 ? Theme.warn : Theme.ink }
    readonly property string pingText: s.ping >= 0 ? s.ping + " ms" : "—"

    railIcon: "grid"
    railLabel: "CPU " + s.cpu + "%"
    railStatus: "메모리 " + s.memory + "% · 핑 " + pingText
    railDot: s.cpu >= 90 || s.memory >= 90 ? Theme.warn : "transparent"

    summary: Component {
        Item {
            Text {
                x: Theme.pad; y: 13
                text: "CPU"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
            }
            Text {
                x: Theme.pad; y: 30
                text: card.s.cpu + "%"
                color: card.loadColor(card.s.cpu)
                font.family: dockFont; font.pixelSize: 22; font.weight: Font.DemiBold
                font.features: Theme.numberFeatures
            }
            Text {
                x: Theme.pad; y: parent.height - Theme.pad - height + 2; width: parent.width - Theme.pad * 2
                text: "메모리 " + card.s.memory + "% · " + card.pingText
                elide: Text.ElideRight
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 10
                font.features: Theme.numberFeatures
            }
        }
    }

    detail: Component {
        Item {
            Text {
                x: Theme.pad; y: Theme.pad
                text: "시스템"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Column {
                x: Theme.pad; y: 50; width: parent.width - Theme.pad * 2; spacing: 14
                Repeater {
                    model: [
                        { label: "CPU", value: card.s.cpu, text: card.s.cpu + "%" },
                        { label: "메모리", value: card.s.memory,
                          text: card.s.memoryUsed + " / " + card.s.memoryTotal + " GB" },
                        { label: "핑", value: -1, text: card.pingText }
                    ]
                    Item {
                        required property var modelData
                        required property int index
                        width: parent.width; height: 18
                        opacity: card.reveal(1 + index); transform: Translate { y: 8 * (1 - card.reveal(1 + index)) }
                        Text {
                            width: 50; anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label
                            color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                        }
                        Meter {
                            visible: modelData.value >= 0
                            x: 56; width: parent.width - 56 - 96; height: 5
                            anchors.verticalCenter: parent.verticalCenter
                            value: modelData.value
                            fill: card.loadColor(modelData.value)
                        }
                        Text {
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            text: modelData.text
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                            font.features: Theme.numberFeatures
                        }
                    }
                }
            }
            Text {
                x: Theme.pad; y: parent.height - Theme.pad - height; width: parent.width - Theme.pad * 2
                text: "핑은 1.1.1.1까지 왕복 시간입니다."
                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 10
                opacity: card.reveal(4)
            }
        }
    }
}
