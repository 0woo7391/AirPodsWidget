import QtQuick

// Instagram DMs seen in Windows notifications: unread count and the latest
// sender at rest; the recent ones and a link to the inbox in the flyout.
// Opening the card marks them read. Message text shows only when allowed.
DockCard {
    id: card
    cardId: "instagram"
    summaryHeight: 68

    readonly property var messages: notificationWatcher.messages
    readonly property int unread: notificationWatcher.unread
    readonly property var latest: messages.length ? messages[0] : null
    readonly property var shown: messages.slice(0, 4)
    detailHeight: 48 + Math.max(1, shown.length) * 46 + 60

    property bool showContent: dockPrefs.get("island/instagramContent")
    Connections {
        target: dockPrefs
        function onChanged(key) { if (key === "island/instagramContent") card.showContent = dockPrefs.get(key) }
    }
    function line(message) { return card.showContent && message.content ? message.content : "메시지" }

    // "방금 / n분 전 / n시간 전 / n일 전", refreshed every half minute.
    property real now: Date.now()
    Timer { interval: 30000; repeat: true; running: card.messages.length > 0; onTriggered: card.now = Date.now() }
    function ago(ms) {
        const s = Math.max(0, (card.now - ms) / 1000)
        return s < 60 ? "방금" : s < 3600 ? Math.floor(s / 60) + "분 전" : s < 86400 ? Math.floor(s / 3600) + "시간 전"
            : Math.floor(s / 86400) + "일 전"
    }
    onExpandedChanged: if (expanded) notificationWatcher.markRead()

    railIconComponent: Component { InstaGlyph { size: 18 } }
    railLabel: "Instagram"
    railStatus: unread ? unread + "개 새 메시지" : latest ? latest.sender + " · " + ago(latest.time) : "새 메시지 없음"
    railDot: unread ? Theme.charge : "transparent"

    summary: Component {
        Item {
            InstaGlyph { x: Theme.pad; y: 15; size: 16; color: Theme.inkSecondary }
            Text {
                x: Theme.pad + 22; y: 13; height: 20
                text: "Instagram"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
            }
            Rectangle {
                visible: card.unread > 0
                x: parent.width - Theme.pad - width; y: 14
                width: Math.max(18, count.implicitWidth + 10); height: 18; radius: 9
                color: Theme.charge
                Text {
                    id: count
                    anchors.centerIn: parent
                    text: card.unread > 99 ? "99+" : card.unread
                    color: "#16161A"; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                    font.features: Theme.numberFeatures
                }
            }
            Text {
                x: Theme.pad; y: 36; width: parent.width - Theme.pad * 2
                text: card.latest ? card.latest.sender : "새 메시지 없음"
                elide: Text.ElideRight
                color: card.latest ? Theme.ink : Theme.inkSecondary
                font.family: dockFont; font.pixelSize: 13; font.weight: Font.DemiBold
            }
            Text {
                x: Theme.pad; y: 53; width: parent.width - Theme.pad * 2
                visible: card.latest !== null
                text: card.latest ? card.line(card.latest) + " · " + card.ago(card.latest.time) : ""
                elide: Text.ElideRight
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
            }
        }
    }

    detail: Component {
        Item {
            Row {
                x: Theme.pad; y: Theme.pad; spacing: 8
                opacity: card.reveal(0); transform: Translate { y: 8 * (1 - card.reveal(0)) }
                InstaGlyph { size: 18; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "최근 DM"
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                }
            }
            Column {
                x: 6; y: 48; width: parent.width - 12; spacing: 2
                Repeater {
                    model: card.shown
                    Item {
                        required property var modelData
                        required property int index
                        width: parent.width; height: 44
                        opacity: card.reveal(1 + index); transform: Translate { y: 8 * (1 - card.reveal(1 + index)) }
                        Rectangle {
                            x: 8; width: 32; height: 32; radius: 16
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.wellHover
                            border.width: 1; border.color: Theme.stroke
                            Text {
                                anchors.centerIn: parent
                                text: (modelData.sender || "?").charAt(0).toUpperCase()
                                color: Theme.ink; font.family: dockFont; font.pixelSize: 14; font.weight: Font.DemiBold
                            }
                        }
                        Column {
                            x: 50; width: parent.width - x - 64
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1
                            Text {
                                width: parent.width; text: modelData.sender; elide: Text.ElideRight
                                color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                            }
                            Text {
                                width: parent.width; text: card.line(modelData); elide: Text.ElideRight
                                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                            }
                        }
                        Text {
                            anchors.right: parent.right; anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: card.ago(modelData.time)
                            color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 10
                        }
                    }
                }
            }
            Text {
                visible: card.shown.length === 0
                x: Theme.pad; y: 60; width: parent.width - Theme.pad * 2; wrapMode: Text.Wrap
                text: "아직 받은 DM이 없습니다. 브라우저에서 instagram.com 알림을 허용해 두면 여기에 쌓입니다."
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
            }
            GlassButton {
                x: Theme.pad; y: parent.height - Theme.pad - height
                width: parent.width - Theme.pad * 2
                text: "받은 메시지함 열기"; accent: true
                opacity: card.reveal(5)
                onClicked: notificationWatcher.openInbox()
            }
        }
    }
}
