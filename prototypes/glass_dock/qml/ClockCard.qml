import QtQuick

// Time and date. Half: time over date. Full: a larger time with the weekday beside it.
// The flyout is a month calendar: today marked, weekends tinted, arrows to page months.
DockCard {
    id: card
    cardId: "clock"
    summaryHeight: 84
    detailHeight: 286

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

    detail: Component {
        Item {
            id: calendar
            // Months away from this one; the grid slides the way you page.
            property int offset: 0
            property int direction: 0
            readonly property date month: new Date(card.now.getFullYear(), card.now.getMonth() + offset, 1)
            readonly property int firstDay: month.getDay()
            readonly property int days: new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
            function page(step) { direction = step; offset += step; slide.restart() }
            Connections { target: card; function onExpandedChanged() { if (!card.expanded) calendar.offset = 0 } }

            Text {
                x: Theme.pad; y: Theme.pad
                text: calendar.month.getFullYear() + "년 " + (calendar.month.getMonth() + 1) + "월"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: Theme.pad - 4; y: Theme.pad - 6
                spacing: 4
                opacity: card.reveal(0)
                GlassButton { width: 28; height: 28; text: "‹"; onClicked: calendar.page(-1) }
                GlassButton {
                    width: 44; height: 28; text: "오늘"
                    enabled: calendar.offset !== 0
                    onClicked: calendar.page(-calendar.offset)
                }
                GlassButton { width: 28; height: 28; text: "›"; onClicked: calendar.page(1) }
            }
            Row {
                id: weekdays
                x: Theme.pad; y: 52
                opacity: card.reveal(1)
                Repeater {
                    model: ["일", "월", "화", "수", "목", "금", "토"]
                    Text {
                        required property string modelData
                        required property int index
                        width: (calendar.width - Theme.pad * 2) / 7
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData
                        color: index === 0 ? "#FF8A80" : index === 6 ? "#8FB8FF" : Theme.inkTertiary
                        font.family: dockFont; font.pixelSize: 10; font.weight: Font.DemiBold
                    }
                }
            }
            Grid {
                id: grid
                x: Theme.pad; y: 74
                columns: 7
                opacity: card.reveal(2)
                transform: Translate { id: shift }
                SequentialAnimation {
                    id: slide
                    ParallelAnimation {
                        NumberAnimation { target: shift; property: "x"; to: -18 * calendar.direction; duration: 0 }
                        NumberAnimation { target: grid; property: "opacity"; to: 0.2; duration: 0 }
                    }
                    ParallelAnimation {
                        NumberAnimation { target: shift; property: "x"; to: 0; duration: 260; easing.type: Easing.OutCubic }
                        NumberAnimation { target: grid; property: "opacity"; to: 1; duration: 220 }
                    }
                }
                Repeater {
                    model: 42
                    Item {
                        required property int index
                        readonly property int day: index - calendar.firstDay + 1
                        readonly property bool inMonth: day >= 1 && day <= calendar.days
                        readonly property date date: new Date(calendar.month.getFullYear(), calendar.month.getMonth(), day)
                        readonly property bool today: inMonth && date.toDateString() === card.now.toDateString()
                        width: (calendar.width - Theme.pad * 2) / 7
                        height: 30
                        Rectangle {
                            anchors.centerIn: parent
                            width: 26; height: 26; radius: 13
                            color: parent.today ? Theme.charge : "transparent"
                        }
                        Text {
                            anchors.centerIn: parent
                            text: parent.date.getDate()
                            color: parent.today ? "#16161A" : !parent.inMonth ? "#33F5F5F7"
                                : index % 7 === 0 ? "#FF8A80" : index % 7 === 6 ? "#8FB8FF" : Theme.ink
                            font.family: dockFont; font.pixelSize: 12
                            font.weight: parent.today ? Font.DemiBold : Font.Normal
                            font.features: Theme.numberFeatures
                        }
                    }
                }
            }
        }
    }
}
