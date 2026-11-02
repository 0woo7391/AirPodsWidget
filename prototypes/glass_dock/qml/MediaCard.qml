import QtQuick

DockCard {
    id: card
    cardId: "media"
    summaryHeight: 68
    detailHeight: 176

    readonly property var media: mediaBackend.state
    readonly property bool available: !!media.available
    function command(action) { mediaBackend.command(action, media.token || "", media.identity || "") }

    railIcon: "music"
    railLabel: available ? media.title || "—" : "재생 중 없음"
    railStatus: available ? media.artist || media.sourceName || "" : ""
    railDot: available && media.playing ? Theme.good : "transparent"

    summary: Component {
        Item {
            Artwork { x: Theme.pad; y: 14; width: 40; height: 40; source: card.media.artwork || "" }
            Column {
                x: Theme.pad + 50; y: 15; width: parent.width - x - 48; spacing: 2
                Text {
                    width: parent.width
                    text: card.available ? card.media.title || "—" : "재생 중 없음"
                    elide: Text.ElideRight
                    color: card.available ? Theme.ink : Theme.inkSecondary
                    font.family: dockFont; font.pixelSize: 13; font.weight: Font.DemiBold
                }
                Text {
                    width: parent.width
                    text: card.available ? card.media.artist || card.media.sourceName || "" : ""
                    elide: Text.ElideRight
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                }
            }
            GlassButton {
                x: parent.width - Theme.pad - 32; y: 18; width: 32; height: 32
                icon: "play"; pose: card.media.playing ? "playing" : ""; iconSize: 14
                enabled: card.available && card.media.canPlay
                onClicked: card.command("toggle")
            }
        }
    }

    detail: Component {
        Item {
            Artwork { x: Theme.pad; y: Theme.pad; width: 76; height: 76; radius: 14; source: card.media.artwork || ""; opacity: card.reveal(0); transform: Translate { y: 8 * (1 - card.reveal(0)) } }
            Column {
                x: Theme.pad + 90; y: Theme.pad + 6; width: parent.width - x - Theme.pad; spacing: 4
                opacity: card.reveal(1); transform: Translate { y: 8 * (1 - card.reveal(1)) }
                Text {
                    width: parent.width
                    text: card.available ? card.media.title || "—" : "재생 중인 미디어 없음"
                    wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                }
                Text {
                    width: parent.width
                    text: card.available ? [card.media.artist, card.media.sourceName].filter(Boolean).join(" · ") : ""
                    elide: Text.ElideRight
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                }
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height - Theme.pad - 46; spacing: 18
                opacity: card.reveal(2); transform: Translate { y: 8 * (1 - card.reveal(2)) }
                GlassButton {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "next"; mirrorIcon: true; iconSize: 14
                    enabled: card.available && card.media.canPrevious
                    onClicked: card.command("previous")
                }
                GlassButton {
                    width: 46; height: 46; accent: true
                    icon: "play"; pose: card.media.playing ? "playing" : ""; iconSize: 18
                    enabled: card.available && card.media.canPlay
                    onClicked: card.command("toggle")
                }
                GlassButton {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "next"; iconSize: 14
                    enabled: card.available && card.media.canNext
                    onClicked: card.command("next")
                }
            }
        }
    }
}
