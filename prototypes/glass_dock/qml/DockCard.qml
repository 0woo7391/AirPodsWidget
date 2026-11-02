import QtQuick

// A bento cell that shows `summary` at rest and grows into `detail` while the
// pointer rests on it. The cell keeps its place in the column; only its glass
// panel grows, toward the free space on the left, and floats above the others.
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
    property Component summary
    property Component detail

    property bool open: false
    readonly property bool expanded: expandable && (dock && dock.forcedCard.length ? dock.forcedCard === cardId : open)
    property real progress: expanded ? 1 : 0
    Behavior on progress { NumberAnimation { duration: Theme.expandDuration; easing.type: Easing.OutCubic } }
    readonly property alias panel: panel

    implicitHeight: summaryHeight
    z: progress > 0 ? 10 : 0
    // Step back while another card is grown over this one.
    readonly property bool dimmed: dock && dock.activeCard.length > 0 && dock.activeCard !== cardId
    opacity: dimmed ? Theme.dimmedOpacity : 1
    Behavior on opacity { NumberAnimation { duration: Theme.expandDuration; easing.type: Easing.OutCubic } }

    function maskRect() {
        const p = panel.mapToItem(dock, 0, 0)
        return [p.x, p.y, panel.width, panel.height, Theme.radius]
    }

    Item {
        id: panel
        readonly property real margin: 10
        readonly property real minX: -card.dockLeft + margin
        readonly property real maxRight: (card.dock ? card.dock.width : 0) - card.dockLeft - margin
        readonly property real minY: -card.dockTop + margin
        readonly property real maxBottom: (card.dock ? card.dock.height : 0) - card.dockTop - margin

        width: card.width + (card.detailWidth - card.width) * card.progress
        height: card.summaryHeight + (card.detailHeight - card.summaryHeight) * card.progress
        // Grow leftward from the cell's right edge, then keep inside the window.
        x: Math.max(minX, Math.min(card.width - width, maxRight - width))
        y: Math.max(minY, Math.min(0, maxBottom - height))

        onXChanged: if (card.dock) card.dock.scheduleMask()
        onYChanged: if (card.dock) card.dock.scheduleMask()
        onWidthChanged: if (card.dock) card.dock.scheduleMask()
        onHeightChanged: if (card.dock) card.dock.scheduleMask()

        GlassSurface {
            anchors.fill: parent
            lifted: card.progress > 0.02
        }
        Item {
            anchors.fill: parent
            clip: card.progress > 0 && card.progress < 1
            Loader {
                // Pinned to the cell's own footprint so the summary never reflows mid-motion.
                width: card.width
                height: card.summaryHeight
                anchors.right: parent.right
                anchors.top: parent.top
                sourceComponent: card.summary
                opacity: Math.max(0, 1 - card.progress * 2.2)
                visible: opacity > 0
                enabled: card.progress < 0.1
            }
            Loader {
                width: card.detailWidth
                height: card.detailHeight
                anchors.right: parent.right
                anchors.top: parent.top
                active: card.expandable
                sourceComponent: card.detail
                opacity: Math.max(0, (card.progress - 0.45) / 0.55)
                visible: opacity > 0
                enabled: card.progress > 0.9
            }
        }
        HoverHandler {
            id: hover
            enabled: card.expandable
            onHoveredChanged: {
                if (hovered) { closeTimer.stop(); openTimer.restart() }
                else { openTimer.stop(); closeTimer.restart() }
            }
        }
    }
    Timer { id: openTimer; interval: Theme.hoverOpenDelay; onTriggered: card.open = true }
    Timer { id: closeTimer; interval: Theme.hoverCloseDelay; onTriggered: card.open = false }
}
