import QtQuick

DockCard {
    id: card
    cardId: "media"
    summaryHeight: 68
    detailHeight: 214

    readonly property var media: mediaBackend.state
    readonly property bool available: !!media.available
    function command(action) { mediaBackend.command(action, media.token || "", media.identity || "") }

    // Playback position: the backend reports ~3x a second; between reports it runs on locally.
    readonly property real duration: media.duration || 0
    readonly property real basePosition: media.position || 0
    property real baseAt: Date.now()
    property real now: Date.now()
    onBasePositionChanged: { baseAt = Date.now(); if (!seekCommit.running) dragValue = -1 }
    Timer { interval: 250; repeat: true; running: card.media.playing && card.expanded; onTriggered: card.now = Date.now() }
    readonly property real position: Math.min(duration, basePosition + (media.playing ? Math.max(0, (now - baseAt) / 1000) : 0))
    // While dragging, the bar shows the drag; the seek goes out once the pointer settles.
    property real dragValue: -1
    Timer {
        id: seekCommit; interval: 250
        onTriggered: mediaBackend.seek(card.media.token || "", card.media.identity || "", card.dragValue)
    }
    function clock(seconds) {
        const s = Math.max(0, Math.floor(seconds))
        return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0")
    }

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
            Item {
                x: Theme.pad; y: 98; width: parent.width - Theme.pad * 2; height: 40
                visible: card.duration > 0
                opacity: card.reveal(2) * (card.media.seekable ? 1 : 0.6); transform: Translate { y: 8 * (1 - card.reveal(2)) }
                GlassSlider {
                    width: parent.width
                    from: 0; to: Math.max(1, card.duration)
                    value: card.dragValue >= 0 ? card.dragValue : card.position
                    enabled: card.media.seekable
                    onMoved: function(value) { card.dragValue = value; seekCommit.restart() }
                }
                Text {
                    y: 24; text: card.clock(card.dragValue >= 0 ? card.dragValue : card.position)
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11; font.features: Theme.numberFeatures
                }
                Text {
                    anchors.right: parent.right; y: 24; text: card.clock(card.duration)
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11; font.features: Theme.numberFeatures
                }
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height - Theme.pad - 46; spacing: 18
                opacity: card.reveal(3); transform: Translate { y: 8 * (1 - card.reveal(3)) }
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
