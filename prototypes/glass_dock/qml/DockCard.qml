import QtQuick

// A dock cell. As a bento card it shows `summary` and grows into `detail` while
// the pointer rests on it; as a rail row (minimized dock) it shows an icon that
// widens into a label on hover and opens `detail` on click. The cell keeps its
// place; only its glass panel grows, toward the free space on the left, and
// floats above the others.
Item {
    id: card
    property string cardId: ""
    property Item dock
    // Position of this cell inside the dock, for keeping the grown panel on screen.
    property real dockLeft: 0
    property real dockTop: 0
    property real summaryHeight: 84
    property real detailWidth: Theme.detailWidth
    property real detailHeight: 180
    property bool expandable: true
    property bool magnifies: true
    property Component summary
    property Component detail

    // Rail row: icon, status dot and the label shown when the rail widens.
    property string railIcon: ""
    property string railPose: ""
    property string railLabel: ""
    property string railStatus: ""
    property color railDot: "transparent"
    property int railIndex: 0
    property real railHeight: Theme.railRow
    property Component railContent   // replaces the icon row (the launcher's app rail)

    readonly property real railness: dock ? dock.railness : 0
    readonly property real railOpen: dock ? dock.railOpen : 0
    readonly property bool rail: railness > 0.5
    readonly property real cellHeight: summaryHeight + (railHeight - summaryHeight) * railness

    property bool open: false
    readonly property bool expanded: expandable && (dock && dock.forcedCard.length ? dock.forcedCard === cardId : open)
    onRailChanged: open = false

    // Spring-driven open/close. Width leads and height follows 40 ms later, so
    // the panel unfolds instead of stretching as one box.
    property real springTime: 1
    property real fromW: 0
    property real fromH: 0
    property real springTo: 0
    readonly property bool opening: springTo > 0
    function springAt(time) { return opening ? Theme.spring(17, 0.72, time) : Theme.spring(22, 0.9, time) }
    readonly property real progressW: fromW + (springTo - fromW) * springAt(springTime)
    readonly property real progressH: fromH + (springTo - fromH) * springAt(springTime - 0.04)
    readonly property real progress: Math.max(0, progressW)
    onExpandedChanged: {
        fromW = progressW
        fromH = progressH
        springTo = expanded ? 1 : 0
        springTime = 0
        if (dock) dock.scheduleMask()
    }
    FrameAnimation {
        running: card.springTime < 0.9
        onTriggered: {
            card.springTime = Math.min(0.9, card.springTime + frameTime)
            if (card.springTime >= 0.9 && !card.expanded && card.dock) card.dock.scheduleMask()
        }
    }
    // Detail rows come in one after another; detail components call this per row.
    function reveal(row) { return Theme.seg(progress, 0.22 + 0.07 * row, 0.62 + 0.07 * row) }

    implicitHeight: cellHeight
    z: progress > 0.001 ? 10 : 0

    // Step back while another card is grown over this one.
    readonly property bool dimmed: dock && dock.activeCard.length > 0 && dock.activeCard !== cardId
    property real dimAmount: dimmed ? 1 : 0
    Behavior on dimAmount { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    opacity: 1 - (1 - Theme.dimmedOpacity) * dimAmount

    // Cursor magnification: the cell nearest the pointer swells the most.
    readonly property real magnifyTarget: {
        if (!magnifies || !dock || dock.pointerY < 0 || dock.activeCard.length) return 0
        // A widened rail is a list, not a dock: its rows stay level once the labels are out.
        const peak = (Theme.magnifyCard + (Theme.magnifyRail - Theme.magnifyCard) * railness) * (1 - railOpen * railness)
        return peak * Theme.magnify(dock.pointerY - (dockTop + cellHeight / 2), Theme.magnifyReach)
    }
    property real magnifyAmount: magnifyTarget
    Behavior on magnifyAmount { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    readonly property real cellScale: (1 + magnifyAmount) * (1 - (1 - Theme.dimmedScale) * dimAmount)
    transform: Scale { origin.x: card.width; origin.y: card.cellHeight / 2; xScale: card.cellScale; yScale: card.cellScale }

    // Input/visual envelope of the grown panel (with room for its shadow), or null at rest.
    function maskRect() {
        if (!expanded && progress <= 0.001) return null
        const w = detailWidth * 1.04
        const h = detailHeight * 1.04
        const x = Math.max(panel.minX, Math.min(card.width - w, panel.maxRight - w))
        const y = Math.max(panel.minY, Math.min(0, panel.maxBottom - h))
        const p = card.mapToItem(dock, x, y)
        return [p.x - 24, p.y - 16, w + 48, h + 48]
    }

    Item {
        id: panel
        readonly property real margin: 10
        readonly property real minX: -card.dockLeft + margin
        readonly property real maxRight: (card.dock ? card.dock.width : 0) - card.dockLeft - margin
        readonly property real minY: -card.dockTop + margin
        readonly property real maxBottom: (card.dock ? card.dock.height : 0) - card.dockTop - margin

        width: card.width + (card.detailWidth - card.width) * card.progressW
        height: card.cellHeight + (card.detailHeight - card.cellHeight) * Math.max(0, card.progressH)
        // Grow leftward from the cell's right edge, then keep inside the window.
        x: Math.max(minX, Math.min(card.width - width, maxRight - width))
        y: Math.max(minY, Math.min(0, maxBottom - height))

        GlassSurface {
            anchors.fill: parent
            radius: Theme.radius - (Theme.radius - 16) * card.railness * (1 - card.progress)
            lifted: card.progress > 0.02
            lift: Math.min(1, card.progress)
            lit: hover.hovered
        }
        Item {
            anchors.fill: parent
            clip: (card.progress > 0 && card.progress < 1) || (card.railness > 0 && card.railness < 1)
            readonly property real away: Theme.seg(card.progress, 0, 0.35)
            Loader {
                // Pinned to the cell's own footprint so the summary never reflows mid-motion.
                width: card.width
                height: card.summaryHeight
                anchors.right: parent.right
                anchors.top: parent.top
                sourceComponent: card.summary
                opacity: (1 - card.railness) * (1 - parent.away)
                scale: 1 - 0.03 * parent.away
                transformOrigin: Item.TopRight
                visible: opacity > 0
                enabled: !card.rail && card.progress < 0.1
            }
            Loader {
                width: card.width
                height: card.railHeight
                anchors.right: parent.right
                anchors.top: parent.top
                active: card.railness > 0
                sourceComponent: card.railContent ? card.railContent : railRow
                opacity: card.railness * (1 - parent.away)
                visible: opacity > 0
                enabled: card.rail && card.progress < 0.1
            }
            Loader {
                width: card.detailWidth
                height: card.detailHeight
                anchors.right: parent.right
                anchors.top: parent.top
                active: card.expandable
                sourceComponent: card.detail
                opacity: Theme.seg(card.progress, 0.15, 0.5)
                visible: opacity > 0
                enabled: card.progress > 0.9
            }
        }
        HoverHandler {
            id: hover
            onHoveredChanged: {
                if (!card.expandable) return
                if (hovered) { closeTimer.stop(); if (!card.rail) openTimer.restart() }
                else { openTimer.stop(); closeTimer.restart() }
            }
        }
        // On the rail, hovering only widens the labels; a click opens the detail.
        TapHandler {
            enabled: card.rail && card.expandable && !card.expanded
            onTapped: card.open = true
        }
    }
    Timer { id: openTimer; interval: Theme.hoverOpenDelay; onTriggered: card.open = true }
    Timer { id: closeTimer; interval: Theme.hoverCloseDelay; onTriggered: card.open = false }

    Component {
        id: railRow
        Item {
            DockIcon {
                x: parent.width - Theme.railWidth / 2 - size / 2
                anchors.verticalCenter: parent.verticalCenter
                size: 18
                name: card.railIcon
                pose: card.railPose
            }
            Rectangle {
                x: parent.width - Theme.railWidth / 2 + 6; y: parent.height / 2 - 11
                width: 7; height: 7; radius: 3.5
                color: card.railDot
                border.width: 1; border.color: "#661B1B21"
                visible: card.railDot.a > 0
            }
            // Labels slide in one row after another as the rail widens (#040).
            Column {
                readonly property real shown: Theme.seg(card.railOpen, 0.1 * card.railIndex, 0.55 + 0.1 * card.railIndex)
                x: Theme.pad + 6 * (1 - shown)
                width: parent.width - Theme.railWidth - Theme.pad
                anchors.verticalCenter: parent.verticalCenter
                opacity: shown
                visible: shown > 0
                spacing: 1
                Text {
                    width: parent.width
                    text: card.railLabel; elide: Text.ElideRight
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                }
                Text {
                    width: parent.width
                    text: card.railStatus; elide: Text.ElideRight
                    visible: text.length > 0
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                    font.features: Theme.numberFeatures
                }
            }
        }
    }
}
