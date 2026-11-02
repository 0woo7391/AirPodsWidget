import QtQuick

// A dock cell. As a bento card it shows `summary`; as a rail row (minimized
// dock) it shows an icon that widens into a label. The cell never grows or
// moves: its `detail` opens in the dock's shared flyout beside the column, so
// the other cells stay visible and reachable. The dock decides which card is
// open (dock.openCard) from the hover reports below.
Item {
    id: card
    property string cardId: ""
    property Item dock
    // Position of this cell inside the dock, for placing the flyout beside it.
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
    // Docked on the left edge: rail icons sit on the left.
    readonly property bool mirrored: dock ? dock.mirrored : false
    readonly property real cellHeight: summaryHeight + (railHeight - summaryHeight) * railness
    readonly property alias hovered: hover.hovered

    readonly property bool expanded: expandable && !!dock
        && (dock.forcedCard.length ? dock.forcedCard === cardId : dock.openCard === cardId)

    // Spring-driven open/close of this card's share of the flyout; the detail
    // rows read it through reveal().
    property real springTime: 1
    property real springFrom: 0
    property real springTo: 0
    function springAt(time) { return springTo > 0 ? Theme.spring(17, 0.72, time) : Theme.spring(22, 0.9, time) }
    readonly property real progress: Math.max(0, springFrom + (springTo - springFrom) * springAt(springTime))
    onExpandedChanged: {
        springFrom = progress
        springTo = expanded ? 1 : 0
        springTime = 0
    }
    FrameAnimation {
        running: card.springTime < 0.9
        onTriggered: card.springTime = Math.min(0.9, card.springTime + frameTime)
    }
    // Detail rows come in one after another; detail components call this per row.
    function reveal(row) { return Theme.seg(progress, 0.22 + 0.07 * row, 0.62 + 0.07 * row) }

    implicitHeight: cellHeight

    // Cursor magnification: the cell nearest the pointer swells the most.
    readonly property real magnifyTarget: {
        if (!magnifies || !dock || dock.pointerY < 0 || dock.activeCard.length) return 0
        // A widened rail is a list, not a dock: its rows stay level once the labels are out.
        const peak = (Theme.magnifyCard + (Theme.magnifyRail - Theme.magnifyCard) * railness) * (1 - railOpen * railness)
        return peak * Theme.magnify(dock.pointerY - (dockTop + cellHeight / 2), Theme.magnifyReach)
    }
    property real magnifyAmount: magnifyTarget
    Behavior on magnifyAmount { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    // While dragged the cards stay locked to the grip; only after the drop do they
    // spring the last stretch (onto a snap point, or back from past an end).
    property real followY: dock ? dock.columnY : 0
    Behavior on followY {
        enabled: !!card.dock && card.dock.settling
        SpringAnimation { spring: 18; damping: 0.5; epsilon: 0.1 }
    }
    transform: [
        Scale {
            origin.x: card.mirrored ? 0 : card.width; origin.y: card.cellHeight / 2
            xScale: 1 + card.magnifyAmount; yScale: 1 + card.magnifyAmount
        },
        Translate { y: card.dock ? card.followY - card.dock.columnY : 0 }
    ]

    GlassSurface {
        anchors.fill: parent
        radius: Theme.radius - (Theme.radius - 16) * card.railness
        lit: hover.hovered || card.expanded
        lift: card.dock ? 0.7 * card.dock.dragLift : 0
    }
    // The open card's rim glows toward the flyout, tying the two together.
    Rectangle {
        visible: opacity > 0
        opacity: Math.min(1, card.progress)
        width: 3; height: Math.min(card.cellHeight - 24, 40); radius: 1.5
        anchors.verticalCenter: parent.verticalCenter
        x: card.mirrored ? card.width - width - 1 : 1
        color: Theme.charge
    }
    Item {
        anchors.fill: parent
        clip: card.railness > 0 && card.railness < 1
        Loader {
            // Pinned to the cell's own footprint so the summary never reflows mid-motion.
            width: card.width
            height: card.summaryHeight
            x: card.mirrored ? 0 : parent.width - width
            sourceComponent: card.summary
            opacity: 1 - card.railness
            visible: opacity > 0
            enabled: !card.rail
        }
        Loader {
            width: card.width
            height: card.railHeight
            x: card.mirrored ? 0 : parent.width - width
            active: card.railness > 0
            sourceComponent: card.railContent ? card.railContent : railRow
            opacity: card.railness
            visible: opacity > 0
            enabled: card.rail
        }
    }
    HoverHandler {
        id: hover
        onHoveredChanged: if (card.dock) card.dock.cardHover(card, hovered)
    }
    // On the rail, hovering only widens the labels; a click opens the detail.
    TapHandler {
        enabled: card.rail && card.expandable && !card.expanded && !!card.dock
        onTapped: card.dock.openNow(card.cardId)
    }

    Component {
        id: railRow
        Item {
            readonly property real iconCenter: card.mirrored ? Theme.railWidth / 2 : width - Theme.railWidth / 2
            DockIcon {
                x: parent.iconCenter - size / 2
                anchors.verticalCenter: parent.verticalCenter
                size: 18
                name: card.railIcon
                pose: card.railPose
            }
            Rectangle {
                x: parent.iconCenter + 6; y: parent.height / 2 - 11
                width: 7; height: 7; radius: 3.5
                color: card.railDot
                border.width: 1; border.color: "#661B1B21"
                visible: card.railDot.a > 0
            }
            // Labels slide in one row after another as the rail widens (#040).
            Column {
                readonly property real shown: Theme.seg(card.railOpen, 0.1 * card.railIndex, 0.55 + 0.1 * card.railIndex)
                x: (card.mirrored ? Theme.railWidth : Theme.pad) + 6 * (1 - shown)
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
