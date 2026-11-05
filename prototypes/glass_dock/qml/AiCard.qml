import QtQuick
import QtQuick.Shapes

// AI assistants: usage left with the reset time (Codex), today's use (Claude), a red dot
// for a reply that arrived as a notification, and a click to bring the app up.
// Full: one row per assistant. Half: logos with a usage ring.
DockCard {
    id: card
    cardId: "ai"
    summaryHeight: 84

    readonly property var items: aiStatus.assistants || []
    // A first guess of the flyout's height (name row, 33 px per limit bar, the note lines); the
    // open flyout then takes the height its blocks really have.
    function blockHeight(item) {
        const limits = (item.limits || []).length
        return 36 + limits * 33 + (item.id === "claude" ? (limits ? 22 : 40) : limits ? 0 : 18) + (item.asOf > 0 ? 20 : 0)
    }
    detailHeight: 52 + Math.max(1, items.length) * 12 + items.reduce((sum, i) => sum + blockHeight(i), 0)

    property real now: Date.now()
    Timer { interval: 30000; repeat: true; running: true; onTriggered: card.now = Date.now() }
    // Shown as what is left, like the apps' own usage pages ("5시간 100% 남음").
    // The limit to watch: the one with least left (a week at 1 % matters more than 5 hours at 100 %).
    function main(item) {
        const limits = item.limits || []
        return limits.length ? limits.reduce((a, b) => (b.used > a.used ? b : a)) : null
    }
    function until(ms) {
        const s = Math.max(0, (ms - card.now) / 1000)
        if (!ms) return "초기화됨"
        const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60)
        return (d ? d + "일 " : "") + (d || h ? h + "시간 " : "") + (d ? "" : m + "분 ") + "후 초기화"
    }
    function ago(ms) {
        const s = Math.max(0, (card.now - ms) / 1000)
        return !ms ? "기록 없음" : s < 60 ? "방금" : s < 3600 ? Math.floor(s / 60) + "분 전" : s < 86400 ? Math.floor(s / 3600) + "시간 전"
            : Math.floor(s / 86400) + "일 전"
    }
    function tokens(n) { return n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "K" : n }
    function leftOf(limit) { return Math.max(0, 100 - limit.used) }
    function leftColor(left) { return left <= 10 ? Theme.bad : left <= 30 ? Theme.warn : Theme.good }
    function line(item) {
        const limit = card.main(item)
        return limit ? limit.label + " " + card.leftOf(limit) + "% 남음 · " + card.until(limit.resetsAt)
            : item.id === "claude" ? "오늘 " + card.tokens(item.tokens) + " 토큰 · " + card.ago(item.lastUsed)
            : "한도 기록 없음"
    }

    railIcon: "grid"
    railLabel: "AI"
    railStatus: items.map(i => i.name + (card.main(i) ? " " + card.leftOf(card.main(i)) + "% 남음" : "")).join(" · ")
    railDot: items.some(i => i.unread > 0) ? Theme.bad : "transparent"

    // A logo with an optional usage ring and the reply dot.
    component Logo: Item {
        id: logo
        property var item
        property real size: 26
        property bool ring: true
        readonly property var limit: card.main(item)
        width: size; height: size
        Image {
            anchors.centerIn: parent
            width: logo.size - (logo.ring ? 8 : 0); height: width
            sourceSize: Qt.size(64, 64)
            source: logo.item.logo
            smooth: true
        }
        Shape {
            anchors.fill: parent
            visible: logo.ring && logo.limit !== null
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Theme.well; strokeWidth: 2.5; fillColor: "transparent"
                PathAngleArc { centerX: logo.size / 2; centerY: logo.size / 2; radiusX: logo.size / 2 - 1.5; radiusY: radiusX; startAngle: 0; sweepAngle: 360 }
            }
            ShapePath {
                strokeColor: logo.limit ? card.leftColor(card.leftOf(logo.limit)) : "transparent"
                strokeWidth: 2.5; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: logo.size / 2; centerY: logo.size / 2; radiusX: logo.size / 2 - 1.5; radiusY: radiusX
                    startAngle: -90; sweepAngle: logo.limit ? 3.6 * card.leftOf(logo.limit) : 0
                }
            }
        }
        Rectangle {
            visible: logo.item.unread > 0
            width: 10; height: 10; radius: 5
            x: logo.size - 8; y: -2
            color: Theme.bad
            border.width: 2; border.color: "#1C1C22"
        }
    }

    summary: Component {
        Item {
            readonly property bool wide: card.size === "full"
            Text {
                visible: card.items.length === 0
                x: Theme.pad; y: 34
                text: "AI 앱이 없습니다"
                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 12
            }
            // Full: one row each.
            Column {
                visible: parent.wide
                x: Theme.pad; y: (parent.height - height) / 2; width: parent.width - Theme.pad * 2; spacing: 6
                Repeater {
                    model: parent.visible ? card.items : []
                    Item {
                        required property var modelData
                        width: parent.width; height: 28
                        Logo { item: modelData; size: 26; ring: false; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            x: 34; width: parent.width - x; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                            Text {
                                width: parent.width; elide: Text.ElideRight
                                text: modelData.name + "  ·  " + card.line(modelData)
                                color: Theme.ink; font.family: dockFont; font.pixelSize: 11
                                font.features: Theme.numberFeatures
                            }
                            Meter {
                                visible: card.main(modelData) !== null
                                width: parent.width; height: 3
                                value: card.main(modelData) ? card.leftOf(card.main(modelData)) : 0
                                fill: card.main(modelData) ? card.leftColor(card.leftOf(card.main(modelData))) : Theme.ink
                            }
                        }
                        TapHandler { enabled: !card.editing; onTapped: aiStatus.openApp(modelData.id) }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
            }
            // Half: logos with rings.
            Text {
                visible: !parent.wide
                x: Theme.pad; y: 13
                text: "AI"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
            }
            Row {
                visible: !parent.wide
                x: Theme.pad; y: 38; spacing: 10
                Repeater {
                    model: parent.visible ? card.items : []
                    Logo {
                        required property var modelData
                        item: modelData; size: 32
                        TapHandler { enabled: !card.editing; onTapped: aiStatus.openApp(modelData.id) }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
            }
        }
    }

    detail: Component {
        Item {
            Component.onCompleted: aiStatus.refresh()   // fresh numbers whenever it is opened
            Text {
                x: Theme.pad; y: Theme.pad
                text: "AI"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Column {
                id: blocks
                x: Theme.pad; y: 50; width: parent.width - Theme.pad * 2; spacing: 12
                onHeightChanged: if (height > 0) card.detailHeight = y + height + Theme.pad
                Repeater {
                    model: card.items
                    Item {
                        id: block
                        required property var modelData
                        required property int index
                        width: parent.width; height: 36 + info.height
                        opacity: card.reveal(1 + index); transform: Translate { y: 8 * (1 - card.reveal(1 + index)) }
                        Logo { item: block.modelData; size: 28; ring: false }
                        Text {
                            x: 38; y: 5
                            text: block.modelData.name + (block.modelData.unread ? "  · 새 답변 " + block.modelData.unread : "")
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 13; font.weight: Font.DemiBold
                        }
                        // Open the app, on the name row.
                        GlassButton {
                            anchors.right: parent.right; y: 0
                            height: 28
                            text: "열기"; accent: true
                            onClicked: aiStatus.openApp(block.modelData.id)
                        }
                        Column {
                            id: info
                            x: 0; y: 36; width: parent.width; spacing: 8
                            Repeater {
                                model: block.modelData.limits || []
                                Column {
                                    required property var modelData
                                    width: parent.width; spacing: 3
                                    Text {
                                        text: modelData.label + " " + card.leftOf(modelData) + "% 남음 · " + card.until(modelData.resetsAt)
                                        color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                                        font.features: Theme.numberFeatures
                                    }
                                    Meter {
                                        width: parent.width; height: 4
                                        value: card.leftOf(modelData); fill: card.leftColor(card.leftOf(modelData))
                                    }
                                }
                            }
                            Text {
                                visible: block.modelData.id === "claude"
                                width: parent.width; wrapMode: Text.Wrap
                                text: "오늘 " + card.tokens(block.modelData.tokens) + " 토큰 · 마지막 사용 " + card.ago(block.modelData.lastUsed)
                                    + ((block.modelData.limits || []).length ? ""
                                       : block.modelData.note === "expired" ? "\nClaude 앱을 한 번 열면 남은 한도가 다시 보여요"
                                       : "\n남은 한도를 불러오지 못했어요")
                                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                                lineHeight: 1.2
                            }
                            Text {
                                visible: block.modelData.id !== "claude" && !(block.modelData.limits || []).length
                                text: "아직 한도 기록이 없어요"
                                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                            }
                            Text {
                                visible: block.modelData.asOf > 0
                                text: "기록 기준 " + card.ago(block.modelData.asOf)
                                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 10
                            }
                        }
                    }
                }
            }
        }
    }
}
