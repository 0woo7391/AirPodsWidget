import QtQuick

DockCard {
    id: card
    cardId: "airpods"
    summaryHeight: 92
    detailHeight: 222

    readonly property var device: deviceBackend.state
    readonly property var batteries: deviceBackend.batteries
    readonly property string deviceName: device.name || "AirPods"
    readonly property var airpodsOutput: {
        const needle = (device.name || "AirPods").toLowerCase()
        const list = outputBackend.devices || []
        for (let i = 0; i < list.length; i++)
            if ((list[i].name || "").toLowerCase().indexOf(needle) >= 0) return list[i]
        return null
    }
    readonly property bool isOutput: airpodsOutput !== null && outputBackend.state.currentId === airpodsOutput.id

    function battery(index) { return batteries && batteries.length > index ? batteries[index] : ({ value: -1, charging: false }) }
    function levelColor(value) {
        return value < 0 ? Theme.inkTertiary : value <= 10 ? Theme.bad : value <= 20 ? Theme.warn : Theme.good
    }
    function percent(value) { return value < 0 ? "—" : value }
    readonly property string statusText: device.pending ? "연결 중" : device.connected ? "연결됨"
        : device.paired ? "연결 안 됨" : "설정에서 기기 선택"

    summary: Component {
        Item {
            DockIcon { x: Theme.pad; y: 15; size: 16; name: "headphones"; color: Theme.inkSecondary }
            Text {
                x: Theme.pad + 22; y: 13; width: parent.width - x - 26; height: 20
                text: card.deviceName; elide: Text.ElideRight
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
            }
            Rectangle {
                x: parent.width - Theme.pad - 7; y: 20; width: 7; height: 7; radius: 3.5
                color: card.device.connected ? Theme.good : card.device.pending ? Theme.warn : Theme.inkTertiary
            }
            Row {
                x: Theme.pad; y: 42; spacing: 12
                Repeater {
                    model: 3
                    Column {
                        required property int index
                        readonly property var part: card.battery(index)
                        spacing: 6
                        Row {
                            spacing: 3
                            Text {
                                id: tag
                                text: ["L", "R", "C"][index]
                                anchors.baseline: number.baseline
                                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 10; font.weight: Font.DemiBold
                            }
                            Text {
                                id: number
                                text: card.percent(part.value)
                                color: index === 2 ? Theme.inkSecondary : Theme.ink
                                font.family: dockFont; font.pixelSize: index === 2 ? 15 : 20; font.weight: Font.DemiBold
                                font.features: Theme.numberFeatures
                            }
                        }
                        Meter { width: index === 2 ? 30 : 38; height: 3; value: part.value; fill: part.charging ? Theme.charge : card.levelColor(part.value) }
                    }
                }
            }
        }
    }

    detail: Component {
        Item {
            DockIcon { x: Theme.pad + 2; y: 20; size: 20; name: "headphones" }
            Text {
                x: Theme.pad + 32; y: 15; width: parent.width - x - Theme.pad
                text: card.deviceName; elide: Text.ElideRight
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
            }
            Row {
                x: Theme.pad + 32; y: 35; spacing: 6
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter; width: 6; height: 6; radius: 3
                    color: card.device.connected ? Theme.good : card.device.pending ? Theme.warn : Theme.inkTertiary
                }
                Text {
                    text: card.statusText + (card.isOutput ? " · 현재 출력" : "")
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                }
            }
            Column {
                x: Theme.pad; y: 70; width: parent.width - Theme.pad * 2; spacing: 12
                Repeater {
                    model: 3
                    Item {
                        required property int index
                        readonly property var part: card.battery(index)
                        width: parent.width; height: 18
                        Text {
                            width: 46; anchors.verticalCenter: parent.verticalCenter
                            text: ["왼쪽", "오른쪽", "케이스"][index]
                            color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                        }
                        Meter {
                            x: 50; width: parent.width - 50 - 62; height: 5
                            anchors.verticalCenter: parent.verticalCenter
                            value: part.value; fill: part.charging ? Theme.charge : card.levelColor(part.value)
                        }
                        Image {
                            x: parent.width - 56; width: 8; height: 12
                            anchors.verticalCenter: parent.verticalCenter
                            sourceSize: Qt.size(16, 24)
                            source: "image://lucian/battery?bolt=1&color=%238FD0FF"
                            visible: part.charging
                        }
                        Text {
                            x: parent.width - 44; width: 44; anchors.verticalCenter: parent.verticalCenter
                            horizontalAlignment: Text.AlignRight
                            text: part.value < 0 ? "—" : part.value + "%"
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 13; font.weight: Font.DemiBold
                            font.features: Theme.numberFeatures
                        }
                    }
                }
            }
            Row {
                x: Theme.pad; y: parent.height - Theme.pad - 34; spacing: 8
                GlassButton {
                    width: 128
                    text: card.device.pending ? "연결 중" : card.device.connected ? "연결됨" : "연결"
                    selected: card.device.connected
                    enabled: card.device.paired && !card.device.pending && !card.device.connected
                    onClicked: deviceBackend.connectDevice()
                }
                GlassButton {
                    width: 128
                    text: card.isOutput ? "출력 사용 중" : "출력 전환"
                    accent: !card.isOutput && card.airpodsOutput !== null
                    enabled: card.airpodsOutput !== null && !card.isOutput
                    onClicked: outputBackend.selectOutput(card.airpodsOutput.id)
                }
            }
        }
    }
}
