import QtQuick

// Time and date. Half: time over date. Full: a larger time with the weekday beside it.
DockCard {
    id: card
    cardId: "clock"
    expandable: false
    summaryHeight: 84

    property date now: new Date()
    Timer { interval: 1000; repeat: true; running: true; triggeredOnStart: true; onTriggered: card.now = new Date() }
    readonly property string time: Qt.formatTime(now, "hh:mm")
    readonly property string date: Qt.formatDate(now, "M월 d일")
    readonly property string weekday: ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"][now.getDay()]

    // On the rail the time itself is the icon.
    railIconComponent: Component {
        Text {
            text: card.time
            color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
            font.features: Theme.numberFeatures
        }
    }
    railLabel: time
    railStatus: date + " " + weekday

    summary: Component {
        Item {
            readonly property bool wide: card.size === "full"
            Text {
                x: Theme.pad; y: wide ? 16 : 14
                text: card.time
                color: Theme.ink; font.family: dockFont; font.weight: Font.DemiBold
                font.pixelSize: wide ? 40 : 28
                font.features: Theme.numberFeatures
            }
            Text {
                visible: !parent.wide
                x: Theme.pad; y: parent.height - Theme.pad - height + 2
                text: card.date + " " + card.weekday.charAt(0)
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
            }
            Column {
                visible: parent.wide
                anchors.right: parent.right; anchors.rightMargin: Theme.pad
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    anchors.right: parent.right
                    text: card.weekday
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 14; font.weight: Font.DemiBold
                }
                Text {
                    anchors.right: parent.right
                    text: card.date
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                }
            }
        }
    }
}
