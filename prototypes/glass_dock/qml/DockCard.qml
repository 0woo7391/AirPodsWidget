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
    property Component railIconComponent   // in place of the Lucian icon (a glyph not in the set)
    property Component backdrop            // drawn over the glass, under the content (media artwork)

    readonly property real railness: dock ? dock.railness : 0
    readonly property real railOpen: dock ? dock.railOpen : 0
    readonly property bool rail: railness > 0.5
    // Docked on the left edge: rail icons sit on the left.
    readonly property bool mirrored: dock ? dock.mirrored : false
    // On the desktop icon grid a card spans whole icon rows (less the 10 px gap).
    readonly property real bentoHeight: dock && dock.gridOn
        ? Math.max(1, Math.ceil((summaryHeight + 10) / dock.cellH)) * dock.cellH - 10 : summaryHeight
    readonly property real cellHeight: bentoHeight + (railHeight - bentoHeight) * railness
    readonly property alias hovered: hover.hovered
    // "half" pairs with a neighbouring half card, "full" spans the dock (dockPrefs.modules).
    readonly property string size: dock ? dock.sizeOf(cardId) : "full"
    readonly property var sizes: dock ? dock.sizesOf(cardId) : ["full"]
    // A card can hold its flyout open (the memo while typing).
    property bool pinned: false

    // ---- edit mode (dock.editing): wobble, remove, resize, drag to reorder ----
    readonly property bool editing: !!dock && dock.editing
    readonly property bool dragging: editDrag.active
    // Pointer position in dock coordinates while dragged, and where on the card it grabbed.
    property point dragPoint: Qt.point(0, 0)
    property point grabOffset: Qt.point(0, 0)
    z: dragging ? 50 : 0
    Behavior on x { enabled: card.editing && !card.dragging; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on y { enabled: card.editing && !card.dragging; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    rotation: editing && !dragging ? 0.8 * Math.sin(2 * Math.PI * (dock.wobbleClock * 2.2 + railIndex * 0.37)) : 0

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
        if (!magnifies || !dock || dock.pointerY < 0 || dock.activeCard.length || editing) return 0
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
        Translate { y: card.dock ? card.followY - card.dock.columnY : 0 },
        // Held under the pointer while dragged in edit mode, wherever the layout has moved its slot.
        Translate {
            x: card.dragging ? card.dragPoint.x - card.grabOffset.x - card.dockLeft : 0
            y: card.dragging ? card.dragPoint.y - card.grabOffset.y - card.dockTop : 0
        },
        Scale {
            origin.x: card.width / 2; origin.y: card.cellHeight / 2
            xScale: card.dragging ? 1.04 : 1; yScale: xScale
        }
    ]

    GlassSurface {
        anchors.fill: parent
        radius: Theme.radius - (Theme.radius - 16) * card.railness
        lit: hover.hovered || card.expanded
        lift: card.dock ? Math.max(0.7 * card.dock.dragLift, card.dragging ? 1 : 0) : 0
    }
    Loader {
        anchors.fill: parent
        active: !!card.backdrop
        sourceComponent: card.backdrop
        opacity: 1 - card.railness
        visible: opacity > 0
    }
    // The rim again over a backdrop, so the card keeps its edge.
    Rectangle {
        anchors.fill: parent
        visible: !!card.backdrop && card.railness < 1
        radius: Theme.radius
        color: "transparent"
        border.width: 1
        border.color: hover.hovered || card.expanded ? Theme.strokeLit : Theme.stroke
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
            y: (card.bentoHeight - card.summaryHeight) / 2   // centred in a taller grid cell
            sourceComponent: card.summary
            opacity: 1 - card.railness
            visible: opacity > 0
            enabled: !card.rail && !card.editing
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
        enabled: card.rail && card.expandable && !card.expanded && !!card.dock && !card.editing
        onTapped: card.dock.openNow(card.cardId)
    }
    // Hold a card, or right-click it, to edit the dock (like a phone's home screen).
    TapHandler {
        enabled: !!card.dock && !card.editing
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        longPressThreshold: 0.6
        onLongPressed: card.dock.startEditing()
        onTapped: function(point, button) { if (button === Qt.RightButton) card.dock.startEditing() }
    }
    DragHandler {
        id: editDrag
        enabled: card.editing
        target: null
        onActiveChanged: {
            if (active) {
                card.grabOffset = Qt.point(centroid.pressPosition.x, centroid.pressPosition.y)
                card.dragPoint = Qt.point(centroid.scenePosition.x, centroid.scenePosition.y)   // the dock is the scene root
            } else {
                card.dock.endDrag(card)
            }
        }
        onCentroidChanged: if (active) {
            card.dragPoint = Qt.point(centroid.scenePosition.x, centroid.scenePosition.y)
            card.dock.dragTo(card, card.dragPoint)
        }
    }

    // Edit-mode controls: remove (top corner) and, for two-size modules, resize.
    Rectangle {
        z: 5
        width: 22; height: 22; radius: 11
        x: card.mirrored ? card.width - width + 6 : -6; y: -6
        color: "#E6303038"
        border.width: 1; border.color: Theme.strokeLit
        opacity: card.editing && !card.dragging ? 1 : 0
        scale: card.editing ? 1 : 0.6
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
        Rectangle { anchors.centerIn: parent; width: 10; height: 2; radius: 1; color: Theme.ink }
        TapHandler { onTapped: card.dock.removeCard(card.cardId) }
    }
    Rectangle {
        z: 5
        readonly property string other: card.sizes.length > 1 ? card.sizes[(card.sizes.indexOf(card.size) + 1) % card.sizes.length] : ""
        width: sizeText.implicitWidth + 16; height: 22; radius: 11
        x: card.mirrored ? 6 : card.width - width - 6; y: card.cellHeight - height - 6
        color: "#E6303038"
        border.width: 1; border.color: Theme.strokeLit
        opacity: card.editing && !card.dragging && other.length ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        Text {
            id: sizeText
            anchors.centerIn: parent
            text: parent.other === "half" ? "작게" : "크게"
            color: Theme.ink; font.family: dockFont; font.pixelSize: 10; font.weight: Font.DemiBold
        }
        TapHandler { onTapped: dockPrefs.setModuleSize(card.cardId, parent.other) }
    }

    Component {
        id: railRow
        Item {
            readonly property real iconCenter: card.mirrored ? Theme.railWidth / 2 : width - Theme.railWidth / 2
            DockIcon {
                visible: !card.railIconComponent
                x: parent.iconCenter - size / 2
                anchors.verticalCenter: parent.verticalCenter
                size: 18
                name: card.railIcon
                pose: card.railPose
            }
            Loader {
                sourceComponent: card.railIconComponent
                x: parent.iconCenter - width / 2
                anchors.verticalCenter: parent.verticalCenter
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
